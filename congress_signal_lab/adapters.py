"""External data adapters for CongressSignalLab.

Supports ingesting candidate congress disclosure feeds from:
- austin-json / austin-sqlite: Primary transaction feeds with point-in-time versioning
- kadoa: Auxiliary secondary cross-check feed (not backtest ready)
- committees: Historical congressional committee assignments
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import asdict
from datetime import date, datetime
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import sys
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
from urllib.parse import urlsplit

from congress_signal_lab.core import Disclosure, PLACEHOLDER_IDS


VALID_CHAMBERS: Set[str] = {"house", "senate"}
VALID_ACTIONS: Dict[str, str] = {
    "purchase": "buy",
    "buy": "buy",
    "sale": "sell",
    "sale_full": "sell",
    "sale_partial": "sell",
    "sell": "sell",
    "exchange": "exchange",
}
ALLOWED_IDENTITY_SOURCES: Set[str] = {"legislators", "override"}
SHA_40_RE = re.compile(r"\A[0-9a-fA-F]{40}\Z")
TICKER_RE = re.compile(r"\A[A-Z0-9][A-Z0-9.\-]{0,14}\Z")
OPTION_WORD_RE = re.compile(r"\b(call|put|option|options|strike|expiry|expiring|warrant)\b", re.IGNORECASE)


def parse_iso_datetime(value: str) -> datetime:
    """Parse an ISO-8601 string and ensure it has timezone information."""
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"Expected trimmed ISO datetime string, got {value!r}")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError(f"Naive datetime not allowed (missing timezone): {value}")
    return dt


def parse_iso_date(value: str) -> date:
    """Parse a canonical ISO date string (YYYY-MM-DD)."""
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError(f"Expected canonical YYYY-MM-DD date string, got {value!r}")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError(f"Expected canonical YYYY-MM-DD date string, got {value!r}")
    return parsed


def _validate_aware_datetime(dt: Any, name: str) -> None:
    if not isinstance(dt, datetime) or dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError(f"{name} must be a timezone-aware datetime: {dt!r}")


def _validate_source_ref(source_ref: Any) -> str:
    if not isinstance(source_ref, str) or not source_ref.strip() or source_ref != source_ref.strip():
        raise ValueError("source_ref must be a non-empty trimmed string")
    return source_ref


def _is_valid_http_url(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        return False
    if any(ch.isspace() for ch in value):
        return False
    try:
        parts = urlsplit(value)
    except ValueError:
        return False
    return parts.scheme in {"http", "https"} and bool(parts.netloc)


def _is_valid_identifier(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    cleaned = value.strip()
    return bool(cleaned) and cleaned.upper() not in PLACEHOLDER_IDS


def _is_valid_ticker(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    cleaned = value.strip().upper()
    if not cleaned or cleaned in PLACEHOLDER_IDS or cleaned.isdigit():
        return False
    return bool(TICKER_RE.match(cleaned))


def _parse_finite_nonnegative_amount(raw_val: Any) -> Tuple[bool, Optional[float], str]:
    """Validate optional amount bound. Rejects booleans, NaNs, infinities, and negatives."""
    if raw_val is None:
        return True, None, ""
    if isinstance(raw_val, bool):
        return False, None, "boolean_not_allowed"
    try:
        val = float(raw_val)
    except (ValueError, TypeError):
        return False, None, "unparseable"
    if not math.isfinite(val) or val < 0:
        return False, None, "negative_or_nonfinite"
    return True, val, ""


def _sanitize_for_json(obj: Any) -> Any:
    """Ensure quarantined raw record snapshots do not contain raw NaN/Infinity floats."""
    if isinstance(obj, float):
        if not math.isfinite(obj):
            return str(obj)
        return obj
    if isinstance(obj, dict):
        return {str(k): _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(v) for v in obj]
    return obj


def _reject_nonfinite_constant(token: str) -> Any:
    raise ValueError(f"Non-finite JSON constant not allowed: {token}")


def compute_file_sha256(path: Path) -> str:
    """Compute the SHA-256 hex digest of a file. Fails if file does not exist."""
    if not path.exists():
        raise FileNotFoundError(f"Source file not found: {path}")
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def classify_asset(
    code: Optional[str],
    label: Optional[str],
    legacy_type: Optional[str],
    description: Optional[str],
    comment: Optional[str],
) -> Tuple[bool, str]:
    """Determine normalized asset type with defensive option/derivative exclusion.

    Returns (is_stock, normalized_type).
    """
    for val in (code, label, legacy_type, description, comment):
        if val is not None and not isinstance(val, str):
            return False, "invalid_field_type"

    code_str = (code or "").strip().lower()
    label_str = (label or "").strip().lower()
    legacy_str = (legacy_type or "").strip().lower()
    desc_str = (description or "").lower()
    comm_str = (comment or "").lower()

    # 1. Option / derivative detection takes precedence
    if (
        OPTION_WORD_RE.search(desc_str)
        or OPTION_WORD_RE.search(comm_str)
        or "option" in code_str
        or "option" in label_str
        or "option" in legacy_str
    ):
        return False, "option"

    # 2. ETF check
    if (
        code_str in {"etf", "exchange-traded fund"}
        or label_str in {"etf", "exchange-traded fund"}
        or legacy_str in {"etf", "exchange-traded fund"}
        or "etf" in desc_str.split()
        or "exchange-traded fund" in desc_str
    ):
        return False, "etf"

    # 3. Bond / treasury check
    if (
        "bond" in code_str
        or "bond" in label_str
        or "bond" in legacy_str
        or "bond" in desc_str.split()
        or "treasury" in desc_str
    ):
        return False, "bond"

    # 4. Fund / mutual fund check
    if (
        "fund" in code_str
        or "fund" in label_str
        or "fund" in legacy_str
        or "fund" in desc_str.split()
        or "mutual fund" in desc_str
    ):
        return False, "fund"

    # 5. Explicit stock check
    is_explicit_stock = (
        code_str in {"st", "stock"}
        or label_str in {"stock", "common stock", "equity"}
        or legacy_str in {"st", "stock", "common stock", "equity"}
        or "common stock" in desc_str
    )

    if is_explicit_stock:
        return True, "stock"

    # Unrecognized / unknown asset type
    raw_type = code_str or label_str or legacy_str or "unknown"
    return False, raw_type


def normalize_action(raw_action: Optional[str]) -> Optional[str]:
    """Map raw action strings to core actions."""
    if not raw_action or not isinstance(raw_action, str):
        return None
    cleaned = raw_action.strip().lower().replace("-", "_").replace(" ", "_")
    return VALID_ACTIONS.get(cleaned)


def _has_amendment_chain_conflict(group: List[Tuple[Dict[str, Any], Dict[str, Any]]]) -> bool:
    """Detect duplicate version numbers, non-monotonic version/availability order, or interval overlap."""
    if len(group) <= 1:
        return False
    versions = [meta["version"] for _, meta in group]
    if len(set(versions)) != len(versions):
        return True
    ordered = sorted(group, key=lambda item: (item[1]["available_at"], item[1]["version"]))
    for idx in range(len(ordered) - 1):
        curr_meta = ordered[idx][1]
        next_meta = ordered[idx + 1][1]
        if curr_meta["version"] >= next_meta["version"]:
            return True
        if curr_meta["superseded_at"] is None or curr_meta["superseded_at"] > next_meta["available_at"]:
            return True
    return False


def adapt_austin_records(
    records: List[Dict[str, Any]],
    observed_at: datetime,
    as_of: datetime,
    source_ref: str,
    source_path: Path,
) -> Dict[str, Any]:
    """Process Austin records into point-in-time Disclosure records.

    Uses PoliticalTradeEventRow schema as source of truth.
    Does not require or manufacture filing_date.
    Core events contain exactly Disclosure fields; metadata moved into sidecar.
    """
    _validate_aware_datetime(observed_at, "observed_at")
    _validate_aware_datetime(as_of, "as_of")
    source_ref = _validate_source_ref(source_ref)
    if as_of > observed_at:
        raise ValueError(
            f"as_of ({as_of.isoformat()}) cannot be in the future of observed_at ({observed_at.isoformat()})"
        )
    if not isinstance(records, list):
        raise ValueError(f"records must be a list of objects, got {type(records)}")

    quarantined: List[Dict[str, Any]] = []
    parsed_records_by_event: Dict[str, List[Tuple[Dict[str, Any], Dict[str, Any]]]] = defaultdict(list)
    tainted_event_ids: Set[str] = set()
    inactive_count = 0

    def _quarantine(record_id: str, reason: str, raw_rec: Any) -> None:
        quarantined.append({
            "record_id": record_id,
            "reason": reason,
            "record": _sanitize_for_json(raw_rec),
        })

    for idx, r in enumerate(records):
        if not isinstance(r, dict):
            _quarantine(f"row_{idx}", "malformed_record:not_an_object", r)
            continue

        # 1. eventId and version check (never manufacture row IDs)
        raw_event_id = r.get("eventId") if "eventId" in r and r.get("eventId") is not None else r.get("event_id")
        version = r.get("version")
        valid_version = isinstance(version, int) and not isinstance(version, bool) and version >= 1
        if not _is_valid_identifier(raw_event_id) or not valid_version:
            rec_id = (
                str(raw_event_id).strip()
                if isinstance(raw_event_id, str) and raw_event_id.strip()
                else (str(r.get("id")) if r.get("id") else "unknown")
            )
            if _is_valid_identifier(raw_event_id):
                tainted_event_ids.add(str(raw_event_id).strip())
            _quarantine(rec_id, "missing_event_id_or_version", r)
            continue

        event_id = str(raw_event_id).strip()

        # 2. availableAt check (never fall back to firstAvailableAt)
        raw_available = (
            r.get("availableAt")
            if "availableAt" in r and r.get("availableAt") is not None
            else r.get("available_at")
        )
        if not raw_available or not isinstance(raw_available, str):
            tainted_event_ids.add(event_id)
            _quarantine(event_id, "missing_available_at", r)
            continue

        try:
            available_at = parse_iso_datetime(raw_available)
        except Exception as e:
            tainted_event_ids.add(event_id)
            _quarantine(event_id, f"available_at_parse_error:{e}", r)
            continue

        if available_at > observed_at:
            tainted_event_ids.add(event_id)
            _quarantine(event_id, "available_at_after_observed_at", r)
            continue

        # 3. supersededAt check and interval validation
        raw_superseded = (
            r.get("supersededAt")
            if "supersededAt" in r and r.get("supersededAt") is not None
            else r.get("superseded_at")
        )
        superseded_at: Optional[datetime] = None
        if raw_superseded is not None and raw_superseded != "":
            if not isinstance(raw_superseded, str):
                tainted_event_ids.add(event_id)
                _quarantine(event_id, "superseded_at_parse_error:not_a_string", r)
                continue
            try:
                superseded_at = parse_iso_datetime(raw_superseded)
            except Exception as e:
                tainted_event_ids.add(event_id)
                _quarantine(event_id, f"superseded_at_parse_error:{e}", r)
                continue
            if superseded_at <= available_at:
                tainted_event_ids.add(event_id)
                _quarantine(event_id, "invalid_supersession_interval:superseded_before_available", r)
                continue
            if superseded_at > observed_at:
                tainted_event_ids.add(event_id)
                _quarantine(event_id, "invalid_supersession_interval:superseded_after_observed_at", r)
                continue

        # Optional firstAvailableAt validation
        raw_first_available = (
            r.get("firstAvailableAt")
            if "firstAvailableAt" in r and r.get("firstAvailableAt") is not None
            else r.get("first_available_at")
        )
        first_avail_str: Optional[str] = None
        if raw_first_available is not None and raw_first_available != "":
            if not isinstance(raw_first_available, str):
                tainted_event_ids.add(event_id)
                _quarantine(event_id, "invalid_first_available_at:not_a_string", r)
                continue
            try:
                first_avail_dt = parse_iso_datetime(raw_first_available)
            except Exception as e:
                tainted_event_ids.add(event_id)
                _quarantine(event_id, f"invalid_first_available_at:{e}", r)
                continue
            if first_avail_dt > available_at:
                tainted_event_ids.add(event_id)
                _quarantine(event_id, "invalid_first_available_at:after_available_at", r)
                continue
            first_avail_str = first_avail_dt.isoformat()

        parsed_records_by_event[event_id].append((
            r,
            {
                "event_id": event_id,
                "version": version,
                "available_at": available_at,
                "superseded_at": superseded_at,
                "first_available_at": first_avail_str,
            },
        ))

    active_records_by_event: Dict[str, List[Tuple[Dict[str, Any], Dict[str, Any]]]] = defaultdict(list)

    # Validate version chains per event_id before partitioning active vs inactive at as_of
    for event_id, event_group in parsed_records_by_event.items():
        if event_id in tainted_event_ids:
            for r, _ in event_group:
                _quarantine(event_id, f"corrupted_version_chain_for_event:{event_id}", r)
            continue

        active_in_group = [
            (r, meta)
            for r, meta in event_group
            if (meta["available_at"] <= as_of)
            and (meta["superseded_at"] is None or as_of < meta["superseded_at"])
        ]

        if len(active_in_group) > 1:
            for r, _ in active_in_group:
                _quarantine(event_id, f"duplicate_active_version_conflict_for_event:{event_id}", r)
            inactive_count += len(event_group) - len(active_in_group)
            continue

        if _has_amendment_chain_conflict(event_group):
            for r, _ in event_group:
                _quarantine(
                    event_id,
                    f"amendment_overlap_or_duplicate_active_version_conflict_for_event:{event_id}",
                    r,
                )
            continue

        for r, meta in event_group:
            is_active = (meta["available_at"] <= as_of) and (
                meta["superseded_at"] is None or as_of < meta["superseded_at"]
            )
            if not is_active:
                inactive_count += 1
            else:
                active_records_by_event[event_id].append((r, meta))

    valid_events: List[Dict[str, Any]] = []
    sidecar: Dict[str, Dict[str, Any]] = {}

    # Process active event groups
    for event_id, group in active_records_by_event.items():
        if len(group) > 1:
            for r, _ in group:
                _quarantine(event_id, f"duplicate_active_version_conflict_for_event:{event_id}", r)
            continue

        r, meta = group[0]

        # Identity check: memberId / bioguideId
        member_id = (
            r.get("memberId")
            if "memberId" in r and r.get("memberId") is not None
            else (r.get("member_id") or r.get("bioguideId") or r.get("bioguide_id"))
        )
        if not _is_valid_identifier(member_id):
            _quarantine(event_id, "missing_or_invalid_member_id", r)
            continue
        member_id = str(member_id).strip()

        # Identity source must be legislators or override (missing not allowed)
        identity_src = (
            r.get("identitySource")
            if "identitySource" in r and r.get("identitySource") is not None
            else r.get("identity_source")
        )
        if not isinstance(identity_src, str) or identity_src not in ALLOWED_IDENTITY_SOURCES:
            _quarantine(event_id, f"invalid_identity_source:{identity_src}", r)
            continue

        # Chamber check
        raw_chamber = r.get("chamber")
        chamber = raw_chamber.strip().lower() if isinstance(raw_chamber, str) else ""
        if chamber not in VALID_CHAMBERS:
            _quarantine(event_id, f"invalid_chamber:{raw_chamber}", r)
            continue

        # Ticker check
        raw_ticker = r.get("ticker")
        if not _is_valid_ticker(raw_ticker):
            _quarantine(event_id, "invalid_or_missing_ticker", r)
            continue
        ticker = str(raw_ticker).strip().upper()

        # Source URL check
        source_url = (
            r.get("sourceUrl")
            if "sourceUrl" in r and r.get("sourceUrl") is not None
            else (r.get("source_url") or r.get("filing_url"))
        )
        if not _is_valid_http_url(source_url):
            _quarantine(event_id, "invalid_or_missing_source_url", r)
            continue
        source_url = str(source_url).strip()

        # Transaction date check (filingDate is NOT required and never manufactured)
        raw_tx_date = (
            r.get("transactionDate")
            if "transactionDate" in r and r.get("transactionDate") is not None
            else r.get("transaction_date")
        )
        if not raw_tx_date or not isinstance(raw_tx_date, str):
            _quarantine(event_id, "missing_transaction_date", r)
            continue
        try:
            tx_date = parse_iso_date(raw_tx_date.strip())
        except Exception as e:
            _quarantine(event_id, f"date_parse_error:{e}", r)
            continue

        # Action mapping
        raw_act = (
            r.get("action")
            if "action" in r and r.get("action") is not None
            else (r.get("type") or r.get("transaction_type") or r.get("transactionType"))
        )
        action = normalize_action(raw_act)
        if not action:
            _quarantine(event_id, f"unrecognized_action:{raw_act}", r)
            continue

        # Asset classification & defensive option exclusion
        code = r.get("assetTypeCode") if "assetTypeCode" in r else r.get("asset_type_code")
        label = r.get("assetTypeLabel") if "assetTypeLabel" in r else r.get("asset_type_label")
        legacy_type = r.get("assetType") if "assetType" in r else r.get("asset_type")
        desc = (
            r.get("assetDescription")
            if "assetDescription" in r
            else (r.get("asset_description") or r.get("description"))
        )
        comment = r.get("comment")

        is_stock, asset_norm = classify_asset(code, label, legacy_type, desc, comment)
        if not is_stock:
            _quarantine(event_id, f"non_stock_asset:{asset_norm}", r)
            continue

        # Amount validation: finite, nonnegative, ordered low <= high, preserve nulls
        raw_low = r.get("amountLow") if "amountLow" in r else r.get("amount_low")
        raw_high = r.get("amountHigh") if "amountHigh" in r else r.get("amount_high")

        ok_low, low, err_low = _parse_finite_nonnegative_amount(raw_low)
        if not ok_low:
            reason_suffix = "unparseable_low" if err_low in {"unparseable", "boolean_not_allowed"} else "negative_or_nonfinite_low"
            _quarantine(event_id, f"invalid_amount_interval:{reason_suffix}", r)
            continue

        ok_high, high, err_high = _parse_finite_nonnegative_amount(raw_high)
        if not ok_high:
            reason_suffix = "unparseable_high" if err_high in {"unparseable", "boolean_not_allowed"} else "negative_or_nonfinite_high"
            _quarantine(event_id, f"invalid_amount_interval:{reason_suffix}", r)
            continue

        if low is not None and high is not None and low > high:
            _quarantine(event_id, "invalid_amount_interval:low_greater_than_high", r)
            continue

        # Construct core Disclosure dataclass
        try:
            disc = Disclosure(
                event_id=event_id,
                member=member_id,
                ticker=ticker,
                transaction_date=tx_date.isoformat(),
                available_at=meta["available_at"].isoformat(),
                first_seen_at=observed_at.isoformat(),
                side=action,
                asset_type="stock",
                sector="",
                policy_match=False,
                policy_known_at=None,
            )
        except Exception as e:
            _quarantine(event_id, f"core_disclosure_invariant_violation:{e}", r)
            continue

        # Core event contains exactly Disclosure fields
        event_dict = asdict(disc)
        valid_events.append(event_dict)

        sidecar[event_id] = {
            "version": meta["version"],
            "firstAvailableAt": meta["first_available_at"],
            "availableAt": meta["available_at"].isoformat(),
            "supersededAt": meta["superseded_at"].isoformat() if meta["superseded_at"] else None,
            "owner": r.get("owner"),
            "sourceDocId": r.get("sourceDocId") if "sourceDocId" in r else r.get("source_doc_id"),
            "sourceRowIndex": r.get("sourceRowIndex") if "sourceRowIndex" in r else r.get("source_row_index"),
            "amounts": {
                "amountLow": low,
                "amountHigh": high,
            },
            "originalSourceFields": {
                "chamber": chamber,
                "filerFirst": r.get("filerFirst") if "filerFirst" in r else r.get("filer_first"),
                "filerLast": r.get("filerLast") if "filerLast" in r else r.get("filer_last"),
                "displayName": r.get("displayName") if "displayName" in r else r.get("display_name"),
                "identitySource": identity_src,
                "sourceUrl": source_url,
                "sourceTransactionId": (
                    r.get("sourceTransactionId")
                    if "sourceTransactionId" in r
                    else r.get("source_transaction_id")
                ),
                "assetDescription": desc,
                "assetTypeCode": code,
                "assetTypeLabel": label,
                "comment": comment,
            },
        }

    # Deterministic ordering
    valid_events.sort(key=lambda e: (e["transaction_date"], e["available_at"], e["event_id"]))

    total_raw = len(records)
    # Strict reconciliation invariant
    assert total_raw == len(valid_events) + len(quarantined) + inactive_count, (
        f"Reconciliation mismatch: total={total_raw}, valid={len(valid_events)}, "
        f"quarantined={len(quarantined)}, inactive={inactive_count}"
    )

    return {
        "manifest": {
            "source_path": str(source_path.resolve()),
            "source_sha256": compute_file_sha256(source_path),
            "retrieved_at": observed_at.isoformat(),
            "provider": "austin",
            "pinned_ref": source_ref,
            "as_of": as_of.isoformat(),
            "total_raw_records": total_raw,
            "valid_events_count": len(valid_events),
            "quarantined_count": len(quarantined),
            "inactive_count": inactive_count,
        },
        "events": valid_events,
        "sidecar": sidecar,
        "quarantined": quarantined,
    }


def adapt_austin_json(
    input_path: Path, observed_at: datetime, as_of: datetime, source_ref: str
) -> Dict[str, Any]:
    """Adapt Austin JSON file."""
    _validate_aware_datetime(observed_at, "observed_at")
    _validate_aware_datetime(as_of, "as_of")
    source_ref = _validate_source_ref(source_ref)
    if as_of > observed_at:
        raise ValueError(
            f"as_of ({as_of.isoformat()}) cannot be in the future of observed_at ({observed_at.isoformat()})"
        )
    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f, parse_constant=_reject_nonfinite_constant)
    if not isinstance(data, list):
        raise ValueError(f"Austin JSON input must be an array of event objects, got {type(data)}")
    return adapt_austin_records(data, observed_at, as_of, source_ref, input_path)


def adapt_austin_sqlite(
    input_path: Path, observed_at: datetime, as_of: datetime, source_ref: str
) -> Dict[str, Any]:
    """Adapt Austin SQLite database file using read-only URI mode and political_trade_events table."""
    _validate_aware_datetime(observed_at, "observed_at")
    _validate_aware_datetime(as_of, "as_of")
    source_ref = _validate_source_ref(source_ref)
    if as_of > observed_at:
        raise ValueError(
            f"as_of ({as_of.isoformat()}) cannot be in the future of observed_at ({observed_at.isoformat()})"
        )
    uri = f"{input_path.resolve().as_uri()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='political_trade_events'")
        if not cur.fetchone():
            raise ValueError("Table 'political_trade_events' not found in SQLite database")
        cur.execute("SELECT * FROM political_trade_events")
        rows = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

    return adapt_austin_records(rows, observed_at, as_of, source_ref, input_path)


def adapt_kadoa(
    input_path: Path, observed_at: datetime, as_of: datetime, source_ref: str
) -> Dict[str, Any]:
    """Adapt auxiliary Kadoa feed.

    Kadoa is an auxiliary cross-check feed only.
    Lacks Bioguide IDs, revision availability timestamps, and includes executive branch.
    Produces zero backtest-ready events, ignores returns/oversight metrics,
    and captures auxiliary trade-level provenance.
    """
    _validate_aware_datetime(observed_at, "observed_at")
    _validate_aware_datetime(as_of, "as_of")
    source_ref = _validate_source_ref(source_ref)
    if as_of > observed_at:
        raise ValueError(
            f"as_of ({as_of.isoformat()}) cannot be in the future of observed_at ({observed_at.isoformat()})"
        )

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f, parse_constant=_reject_nonfinite_constant)

    if isinstance(data, dict):
        if "filer" in data:
            filer_records = [data]
        elif "filers" in data and isinstance(data["filers"], list):
            filer_records = data["filers"]
        else:
            filer_records = [data]
    elif isinstance(data, list):
        filer_records = data
    else:
        raise ValueError(f"Kadoa input must be an object or array of objects, got {type(data)}")

    reconciled_filers: List[Dict[str, Any]] = []
    excluded_filers: List[Dict[str, Any]] = []
    auxiliary_trades: List[Dict[str, Any]] = []
    total_trades_count = 0

    for item in filer_records:
        if not isinstance(item, dict):
            raise ValueError("Each Kadoa filer record must be a JSON object")
        filer_info = item.get("filer") if isinstance(item.get("filer"), dict) else item
        raw_branch = filer_info.get("branch") if filer_info.get("branch") is not None else item.get("branch")
        if raw_branch is not None and not isinstance(raw_branch, str):
            raise ValueError(f"Invalid branch value: {raw_branch!r}")
        branch = (raw_branch or "").strip().lower()
        filer_name = filer_info.get("full_name") or item.get("filer_name") or item.get("name")
        if not _is_valid_identifier(filer_name):
            raise ValueError("Kadoa filer record missing valid filer name")
        trades = item.get("trades") if item.get("trades") is not None else []
        if not isinstance(trades, list):
            raise ValueError("Kadoa trades field must be a list")
        total_trades_count += len(trades)

        # Exclude executive branch or non-congress filers
        if branch == "executive" or (branch and branch not in {"house", "senate", "congress"}):
            excluded_filers.append({
                "filer_name": str(filer_name).strip(),
                "branch": branch,
                "reason": "non_congress_branch",
                "trade_count": len(trades),
            })
            continue

        raw_chamber = filer_info.get("chamber")
        if raw_chamber is not None and not isinstance(raw_chamber, str):
            raise ValueError(f"Invalid chamber value: {raw_chamber!r}")
        chamber = (raw_chamber or "").strip().lower() or (branch if branch in {"house", "senate"} else "unknown")
        reconciled_filers.append({
            "filer_name": str(filer_name).strip(),
            "chamber": chamber,
            "chamber_source": "kadoa",
            "trade_count": len(trades),
        })

        # Auxiliary trade-level provenance (URLs, source IDs, amounts, asset types, date-completeness)
        # Never import returns metrics (ret_since, ret_30d, ret_1y, excess_since) or oversight scores
        for t in trades:
            if not isinstance(t, dict):
                raise ValueError("Each Kadoa trade entry must be a JSON object")
            tx_d = t.get("transaction_date")
            fil_d = t.get("filing_date")
            if tx_d is not None:
                parse_iso_date(tx_d)
            if fil_d is not None:
                parse_iso_date(fil_d)
            ok_low, low, _ = _parse_finite_nonnegative_amount(t.get("amount_range_low"))
            ok_high, high, _ = _parse_finite_nonnegative_amount(t.get("amount_range_high"))
            if not ok_low or not ok_high or (low is not None and high is not None and low > high):
                raise ValueError("Invalid amount interval in Kadoa trade record")
            auxiliary_trades.append({
                "trade_id": t.get("id"),
                "filer_id": t.get("filer_id"),
                "source_id": t.get("source_id"),
                "source_url": t.get("doc_url") or t.get("source_url"),
                "ticker": t.get("ticker"),
                "asset_name": t.get("asset_name"),
                "asset_type": t.get("asset_type"),
                "transaction_date": tx_d,
                "filing_date": fil_d,
                "date_complete": bool(tx_d and fil_d),
                "amount_low": low,
                "amount_high": high,
                "amount_label": t.get("amount_range_label"),
                "comment": t.get("comment"),
            })

    return {
        "manifest": {
            "source_path": str(input_path.resolve()),
            "source_sha256": compute_file_sha256(input_path),
            "retrieved_at": observed_at.isoformat(),
            "provider": "kadoa",
            "pinned_ref": source_ref,
            "as_of": as_of.isoformat(),
            "backtest_ready": False,
            "total_filer_rows": len(filer_records),
            "total_trades_rows": total_trades_count,
            "reconciled_filers_count": len(reconciled_filers),
            "excluded_filers_count": len(excluded_filers),
            "auxiliary_trades_count": len(auxiliary_trades),
            "notice": "Auxiliary cross-check only. Lacks revision availability timestamps and bioguide mapping; outputs 0 events.",
        },
        "events": [],
        "reconciled_filers": reconciled_filers,
        "excluded_filers": excluded_filers,
        "auxiliary_trades": auxiliary_trades,
    }


def adapt_committees(
    input_path: Path, observed_at: datetime, as_of: datetime, source_ref: str
) -> Dict[str, Any]:
    """Adapt congressional committee assignments feed.

    Expects committee-membership JSON shape: {committeeCode: [{bioguide: 'A000001', ...}]}.
    Yields memberId -> committee codes mapping.
    Requires full 40-hex git SHA and enforces known_at gate (observed_at <= as_of).
    """
    _validate_aware_datetime(observed_at, "observed_at")
    _validate_aware_datetime(as_of, "as_of")
    if not isinstance(source_ref, str) or not SHA_40_RE.match(source_ref):
        raise ValueError(f"Committees adapter requires full 40-hex git SHA for source-ref, got '{source_ref}'")

    if observed_at > as_of:
        raise ValueError(
            f"Committee snapshot known_at ({observed_at.isoformat()}) cannot be used to enrich prior as_of ({as_of.isoformat()})"
        )

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f, parse_constant=_reject_nonfinite_constant)

    member_committees: Dict[str, Set[str]] = defaultdict(set)

    if isinstance(data, dict):
        for committee_code, members in data.items():
            if not _is_valid_identifier(committee_code):
                raise ValueError(f"Invalid committee code: {committee_code!r}")
            clean_code = str(committee_code).strip()
            if isinstance(members, list):
                for m in members:
                    if isinstance(m, dict):
                        mid = (
                            m.get("bioguide")
                            or m.get("bioguideId")
                            or m.get("bioguide_id")
                            or m.get("member_id")
                            or m.get("id")
                        )
                    elif isinstance(m, str):
                        mid = m
                    else:
                        raise ValueError(f"Invalid committee member entry: {m!r}")
                    if not _is_valid_identifier(mid):
                        raise ValueError(f"Invalid member bioguide identifier in committee {clean_code}: {mid!r}")
                    member_committees[str(mid).strip()].add(clean_code)
            elif isinstance(members, dict):
                mid = members.get("bioguide") or members.get("bioguideId")
                if not _is_valid_identifier(mid):
                    raise ValueError(f"Invalid member bioguide identifier in committee {clean_code}: {mid!r}")
                member_committees[str(mid).strip()].add(clean_code)
            else:
                raise ValueError(f"Committee members for {clean_code} must be a list or object")
    elif isinstance(data, list):
        for entry in data:
            if not isinstance(entry, dict):
                raise ValueError("Committee list entries must be JSON objects")
            mid = entry.get("member_id") or entry.get("bioguide") or entry.get("bioguide_id")
            code = entry.get("committee_code") or entry.get("code")
            if not _is_valid_identifier(mid) or not _is_valid_identifier(code):
                raise ValueError(f"Invalid committee mapping entry: {entry!r}")
            member_committees[str(mid).strip()].add(str(code).strip())
    else:
        raise ValueError(f"Committees input must be a JSON object or array, got {type(data)}")

    sorted_map = {m: sorted(comm) for m, comm in sorted(member_committees.items())}

    return {
        "manifest": {
            "source_path": str(input_path.resolve()),
            "source_sha256": compute_file_sha256(input_path),
            "retrieved_at": observed_at.isoformat(),
            "provider": "congress-legislators",
            "pinned_ref": source_ref,
            "known_at": observed_at.isoformat(),
            "as_of": as_of.isoformat(),
            "members_count": len(sorted_map),
        },
        "member_committees": sorted_map,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="CongressSignalLab External Data Adapters")
    parser.add_argument(
        "--source",
        required=True,
        choices=["austin-json", "austin-sqlite", "kadoa", "committees"],
        help="Input source format",
    )
    parser.add_argument("--input", required=True, type=Path, help="Input data file path")
    parser.add_argument("--output", required=True, type=Path, help="Output destination file path (exclusive write)")
    parser.add_argument(
        "--observed-at",
        required=True,
        help="ISO-8601 timestamp with timezone when data was observed/retrieved",
    )
    parser.add_argument(
        "--as-of",
        required=False,
        default=None,
        help="ISO-8601 timestamp with timezone for historical point-in-time slice (defaults to observed-at)",
    )
    parser.add_argument(
        "--source-ref",
        required=True,
        help="Pinned commit SHA or version reference",
    )

    args = parser.parse_args(argv)

    try:
        observed_at = parse_iso_datetime(args.observed_at)
    except Exception as e:
        sys.stderr.write(f"Error parsing --observed-at: {e}\n")
        return 1

    if args.as_of:
        try:
            as_of = parse_iso_datetime(args.as_of)
        except Exception as e:
            sys.stderr.write(f"Error parsing --as-of: {e}\n")
            return 1
        if args.source != "committees" and as_of > observed_at:
            sys.stderr.write(
                f"Error: --as-of ({as_of.isoformat()}) cannot be in the future of --observed-at ({observed_at.isoformat()})\n"
            )
            return 1
        if args.source == "committees" and observed_at > as_of:
            sys.stderr.write(
                f"Error: committee snapshot --observed-at ({observed_at.isoformat()}) cannot be after --as-of ({as_of.isoformat()})\n"
            )
            return 1
    else:
        as_of = observed_at

    input_path = args.input
    if not input_path.exists() or not input_path.is_file():
        sys.stderr.write(f"Error: input file '{input_path}' does not exist\n")
        return 1

    output_path = args.output
    if output_path.exists() or input_path.resolve() == output_path.resolve():
        sys.stderr.write(f"Error: output file '{output_path}' already exists (exclusive write required)\n")
        return 1

    try:
        if args.source == "austin-json":
            result = adapt_austin_json(input_path, observed_at, as_of, args.source_ref)
        elif args.source == "austin-sqlite":
            result = adapt_austin_sqlite(input_path, observed_at, as_of, args.source_ref)
        elif args.source == "kadoa":
            result = adapt_kadoa(input_path, observed_at, as_of, args.source_ref)
        elif args.source == "committees":
            result = adapt_committees(input_path, observed_at, as_of, args.source_ref)
        else:
            sys.stderr.write(f"Unsupported source: {args.source}\n")
            return 1
    except Exception as e:
        sys.stderr.write(f"Adapter processing failed: {e}\n")
        return 1

    # Ensure parent directory exists and write exclusively
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output_path.open("x", encoding="utf-8") as f:
            json.dump(result, f, indent=2, allow_nan=False)
    except FileExistsError:
        sys.stderr.write(f"Error: output file '{output_path}' already exists\n")
        return 1

    print(f"Successfully adapted {args.source} -> {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
