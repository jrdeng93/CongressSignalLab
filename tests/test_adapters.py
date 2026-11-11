"""Unit tests for CongressSignalLab external data adapters."""

import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from congress_signal_lab.adapters import (
    adapt_austin_json,
    adapt_austin_records,
    adapt_austin_sqlite,
    adapt_committees,
    adapt_kadoa,
    classify_asset,
    compute_file_sha256,
    main,
    parse_iso_datetime,
)
from congress_signal_lab.core import Disclosure


class TestAdapters(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print(f"SELF_HASH:{compute_file_sha256(Path(__file__))}")

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.temp_dir.name)
        self.sample_observed_at = parse_iso_datetime("2026-04-01T00:00:00Z")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_austin_amendment_versioning_before_and_after(self):
        """Test that as_of correctly selects v1 before amendment and v2 after amendment."""
        smoke_file = self.tmp / "austin_amendment_smoke.json"
        records = [
            {
                "eventId": "event-pelosi-nvda-2026",
                "version": 1,
                "chamber": "house",
                "filerFirst": "Synthetic",
                "filerLast": "Pelosi",
                "displayName": "Pelosi, Synthetic",
                "owner": "spouse",
                "action": "purchase",
                "partialSale": False,
                "transactionDate": "2026-02-01",
                "ticker": "NVDA",
                "sourceTransactionId": "st-1",
                "assetDescription": "NVIDIA Corporation - Common Stock",
                "comment": None,
                "assetTypeCode": "ST",
                "assetTypeLabel": "Common Stock",
                "amountLow": 1000000.0,
                "amountHigh": 5000000.0,
                "firstAvailableAt": "2026-02-15T18:00:00Z",
                "availableAt": "2026-02-15T18:00:00Z",
                "supersededAt": "2026-03-01T00:00:00Z",
                "sourceDocId": "doc-1",
                "sourceRowIndex": 0,
                "sourceUrl": "https://example.com/doc1",
                "contributorRowIds": "c-1",
                "filerKey": "member:P000197",
                "memberId": "P000197",
                "identitySource": "legislators",
            },
            {
                "eventId": "event-pelosi-nvda-2026",
                "version": 2,
                "chamber": "house",
                "filerFirst": "Synthetic",
                "filerLast": "Pelosi",
                "displayName": "Pelosi, Synthetic",
                "owner": "spouse",
                "action": "purchase",
                "partialSale": False,
                "transactionDate": "2026-02-01",
                "ticker": "NVDA",
                "sourceTransactionId": "st-2",
                "assetDescription": "NVIDIA Corporation - Common Stock",
                "comment": None,
                "assetTypeCode": "ST",
                "assetTypeLabel": "Common Stock",
                "amountLow": 1000001.0,
                "amountHigh": 5000000.0,
                "firstAvailableAt": "2026-02-15T18:00:00Z",
                "availableAt": "2026-03-01T00:00:00Z",
                "supersededAt": None,
                "sourceDocId": "doc-2",
                "sourceRowIndex": 0,
                "sourceUrl": "https://example.com/doc2",
                "contributorRowIds": "c-2",
                "filerKey": "member:P000197",
                "memberId": "P000197",
                "identitySource": "legislators",
            },
            {
                "eventId": "event-quarantined",
                "version": 1,
                "chamber": "house",
                "transactionDate": "2026-02-01",
                "ticker": "AAPL",
                "availableAt": "2026-02-15T18:00:00Z",
            },
        ]
        smoke_file.write_text(json.dumps(records))

        # Before amendment (2026-02-20)
        as_of_v1 = parse_iso_datetime("2026-02-20T00:00:00Z")
        res_v1 = adapt_austin_json(smoke_file, self.sample_observed_at, as_of_v1, "austin-sha-1")
        pelosi_v1 = [e for e in res_v1["events"] if e["event_id"] == "event-pelosi-nvda-2026"]
        self.assertEqual(len(pelosi_v1), 1)
        self.assertEqual(res_v1["sidecar"]["event-pelosi-nvda-2026"]["amounts"]["amountLow"], 1000000.0)
        self.assertEqual(res_v1["sidecar"]["event-pelosi-nvda-2026"]["version"], 1)

        # After amendment (2026-03-05)
        as_of_v2 = parse_iso_datetime("2026-03-05T00:00:00Z")
        res_v2 = adapt_austin_json(smoke_file, self.sample_observed_at, as_of_v2, "austin-sha-1")
        pelosi_v2 = [e for e in res_v2["events"] if e["event_id"] == "event-pelosi-nvda-2026"]
        self.assertEqual(len(pelosi_v2), 1)
        self.assertEqual(res_v2["sidecar"]["event-pelosi-nvda-2026"]["amounts"]["amountLow"], 1000001.0)
        self.assertEqual(res_v2["sidecar"]["event-pelosi-nvda-2026"]["version"], 2)

        # Count reconciliation check
        manifest = res_v2["manifest"]
        self.assertEqual(
            manifest["total_raw_records"],
            manifest["valid_events_count"] + manifest["quarantined_count"] + manifest["inactive_count"],
        )

    def test_core_events_match_disclosure_exact_fields(self):
        """Test that every valid event matches Disclosure fields exactly: Disclosure(**event) works."""
        smoke_file = self.tmp / "austin_core_smoke.json"
        records = [
            {
                "eventId": "event-synth-core-1",
                "version": 1,
                "chamber": "house",
                "filerFirst": "Synthetic",
                "filerLast": "Representative",
                "displayName": "Representative, Synthetic",
                "owner": "self",
                "action": "purchase",
                "partialSale": False,
                "transactionDate": "2026-02-01",
                "ticker": "NVDA",
                "sourceTransactionId": "st-core-1",
                "assetDescription": "NVIDIA Corporation - Common Stock",
                "comment": None,
                "assetTypeCode": "ST",
                "assetTypeLabel": "Common Stock",
                "amountLow": 15000.0,
                "amountHigh": 50000.0,
                "firstAvailableAt": "2026-02-15T18:00:00Z",
                "availableAt": "2026-02-15T18:00:00Z",
                "supersededAt": None,
                "sourceDocId": "doc-core-1",
                "sourceRowIndex": 0,
                "sourceUrl": "https://example.com/doc-core",
                "contributorRowIds": "c-core-1",
                "filerKey": "member:P000197",
                "memberId": "P000197",
                "identitySource": "legislators",
            }
        ]
        smoke_file.write_text(json.dumps(records))

        res = adapt_austin_json(smoke_file, self.sample_observed_at, self.sample_observed_at, "sha-1")
        self.assertGreater(len(res["events"]), 0)
        for ev in res["events"]:
            disc = Disclosure(**ev)
            self.assertEqual(disc.event_id, ev["event_id"])
            self.assertNotIn("amount_low", ev)
            self.assertNotIn("member_id", ev)
            self.assertNotIn("chamber", ev)

    def test_reject_naive_datetime_and_future_as_of(self):
        """Test rejection of timezone-naive timestamps and as_of > observed_at."""
        with self.assertRaises(ValueError):
            parse_iso_datetime("2026-02-01T12:00:00")  # missing tz

        naive_dt = parse_iso_datetime("2026-02-01T12:00:00Z").replace(tzinfo=None)
        valid_dt = parse_iso_datetime("2026-02-01T12:00:00Z")

        # Function calls must reject naive datetimes
        with self.assertRaises(ValueError):
            adapt_austin_records([], observed_at=naive_dt, as_of=valid_dt, source_ref="ref", source_path=Path("/tmp"))
        with self.assertRaises(ValueError):
            adapt_austin_records([], observed_at=valid_dt, as_of=naive_dt, source_ref="ref", source_path=Path("/tmp"))

        # Function call must reject as_of > observed_at
        future_dt = parse_iso_datetime("2026-03-01T00:00:00Z")
        past_dt = parse_iso_datetime("2026-02-01T00:00:00Z")
        with self.assertRaises(ValueError):
            adapt_austin_records([], observed_at=past_dt, as_of=future_dt, source_ref="ref", source_path=Path("/tmp"))

        # CLI should reject as_of > observed_at
        dummy_in = self.tmp / "dummy.json"
        dummy_in.write_text("[]")
        dummy_out = self.tmp / "out.json"
        ret = main([
            "--source", "austin-json",
            "--input", str(dummy_in),
            "--output", str(dummy_out),
            "--observed-at", "2026-03-01T00:00:00Z",
            "--as-of", "2026-03-02T00:00:00Z",  # future
            "--source-ref", "ref1",
        ])
        self.assertNotEqual(ret, 0)
        self.assertFalse(dummy_out.exists())

    def test_duplicate_active_version_quarantine_no_silent_survivor(self):
        """Test duplicate active versions quarantine the entire group even if one version is invalid."""
        records = [
            {
                "eventId": "event-conflicted",
                "version": 1,
                "memberId": "P000197",
                "chamber": "house",
                "transactionDate": "2026-02-01",
                "action": "purchase",
                "amountLow": 1000.0,
                "amountHigh": 5000.0,
                "ticker": "AAPL",
                "sourceUrl": "https://example.com/1",
                "availableAt": "2026-02-15T00:00:00Z",
                "supersededAt": None,
                "assetTypeCode": "ST",
                "assetTypeLabel": "Common Stock",
                "identitySource": "legislators",
            },
            {
                "eventId": "event-conflicted",
                "version": 2,
                "memberId": "P000197",
                "chamber": "house",
                "transactionDate": "2026-02-01",
                "action": "purchase",
                "amountLow": 2000.0,
                "amountHigh": 6000.0,
                "ticker": "AAPL",
                "sourceUrl": "https://example.com/2",
                "availableAt": "2026-02-16T00:00:00Z",
                "supersededAt": None,  # Both active at as_of!
                # Version 2 fails asset type check (option)
                "assetTypeCode": "OPT",
                "assetTypeLabel": "Option",
                "identitySource": "legislators",
            },
        ]
        source_file = self.tmp / "test.json"
        source_file.write_text("[]")
        res = adapt_austin_records(
            records,
            observed_at=self.sample_observed_at,
            as_of=parse_iso_datetime("2026-03-01T00:00:00Z"),
            source_ref="test",
            source_path=source_file,
        )
        # No silent survivor! Both must be quarantined
        self.assertEqual(len(res["events"]), 0)
        self.assertEqual(len(res["quarantined"]), 2)
        for q in res["quarantined"]:
            self.assertIn("duplicate_active_version_conflict", q["reason"])

    def test_cli_json_serialization_with_duplicate_and_quarantine(self):
        """Test CLI serialization handles duplicate and quarantined records without datetime errors."""
        records = [
            {
                "eventId": "event-dup",
                "version": 1,
                "memberId": "P000197",
                "chamber": "house",
                "transactionDate": "2026-02-01",
                "action": "purchase",
                "amountLow": 1000.0,
                "ticker": "AAPL",
                "sourceUrl": "https://example.com/1",
                "availableAt": "2026-02-15T00:00:00Z",
                "supersededAt": None,
                "assetTypeCode": "ST",
                "identitySource": "legislators",
            },
            {
                "eventId": "event-dup",
                "version": 2,
                "memberId": "P000197",
                "chamber": "house",
                "transactionDate": "2026-02-01",
                "action": "purchase",
                "amountLow": 2000.0,
                "ticker": "AAPL",
                "sourceUrl": "https://example.com/2",
                "availableAt": "2026-02-16T00:00:00Z",
                "supersededAt": None,
                "assetTypeCode": "ST",
                "identitySource": "legislators",
            },
        ]
        in_file = self.tmp / "in_dup.json"
        in_file.write_text(json.dumps(records))
        out_file = self.tmp / "out_dup.json"

        ret = main([
            "--source", "austin-json",
            "--input", str(in_file),
            "--output", str(out_file),
            "--observed-at", "2026-04-01T00:00:00Z",
            "--source-ref", "test-ref",
        ])
        self.assertEqual(ret, 0)
        self.assertTrue(out_file.exists())
        loaded = json.loads(out_file.read_text())
        self.assertEqual(len(loaded["events"]), 0)
        self.assertEqual(len(loaded["quarantined"]), 2)

    def test_no_fake_sha256_digest(self):
        """Test compute_file_sha256 raises FileNotFoundError on missing files instead of emitting fake digest."""
        missing_file = self.tmp / "does_not_exist.json"
        with self.assertRaises(FileNotFoundError):
            compute_file_sha256(missing_file)

        real_file = self.tmp / "real.json"
        real_file.write_text("hello")
        digest = compute_file_sha256(real_file)
        self.assertEqual(digest, "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824")

    def test_missing_required_fields_quarantine(self):
        """Test quarantine on missing eventId, version, memberId, ticker, sourceUrl, or invalid identitySource."""
        source_file = self.tmp / "bad.json"
        source_file.write_text("[]")

        bad_records = [
            {"version": 1, "ticker": "AAPL", "sourceUrl": "https://example.com"},  # missing eventId
            {"eventId": "e-1", "ticker": "AAPL", "sourceUrl": "https://example.com"},  # missing version
            {"eventId": "e-2", "version": 1, "availableAt": "2026-02-01T00:00:00Z", "ticker": "AAPL"},  # missing memberId
            {"eventId": "e-3", "version": 1, "availableAt": "2026-02-01T00:00:00Z", "memberId": "P000197", "identitySource": "other"},  # bad identitySource
            {"eventId": "e-4", "version": 1, "availableAt": "2026-02-01T00:00:00Z", "memberId": "P000197", "identitySource": "legislators", "ticker": "--"},  # bad ticker
        ]
        res = adapt_austin_records(
            bad_records,
            observed_at=self.sample_observed_at,
            as_of=self.sample_observed_at,
            source_ref="test",
            source_path=source_file,
        )
        self.assertEqual(len(res["events"]), 0)
        self.assertEqual(len(res["quarantined"]), 5)

    def test_option_leakage_defense(self):
        """Test that options in comments, descriptions, or types are quarantined even if labeled ST."""
        source_file = self.tmp / "opt.json"
        source_file.write_text("[]")

        # 1. Helper function checks
        self.assertEqual(classify_asset("ST", "Common Stock", None, "Call option on Apple", None)[0], False)
        self.assertEqual(classify_asset("ST", "Common Stock", None, "Apple Inc", "Bought 10 put contracts")[0], False)
        self.assertEqual(classify_asset("ST", "Common Stock", None, "SPDR S&P 500 ETF Trust", None)[0], False)
        self.assertEqual(classify_asset("ST", "Common Stock", None, "Apple Inc - Common Stock", None)[0], True)

        # 2. Record quarantine
        records = [
            {
                "eventId": "opt-1",
                "version": 1,
                "memberId": "P000197",
                "chamber": "house",
                "transactionDate": "2026-02-01",
                "action": "purchase",
                "amountLow": 1000.0,
                "amountHigh": 5000.0,
                "ticker": "AAPL",
                "assetDescription": "Apple Inc",
                "comment": "March $150 strike Call Option",
                "assetTypeCode": "ST",
                "assetTypeLabel": "Common Stock",
                "sourceUrl": "https://example.com/opt",
                "availableAt": "2026-02-15T00:00:00Z",
                "identitySource": "legislators",
            }
        ]
        res = adapt_austin_records(
            records,
            observed_at=self.sample_observed_at,
            as_of=self.sample_observed_at,
            source_ref="test",
            source_path=source_file,
        )
        self.assertEqual(len(res["events"]), 0)
        self.assertEqual(len(res["quarantined"]), 1)
        self.assertIn("non_stock_asset:option", res["quarantined"][0]["reason"])

    def test_amount_interval_validation_and_null_preservation(self):
        """Test amount validation: finite, nonnegative, ordered, and preserve null bounds explicitly."""
        source_file = self.tmp / "amt.json"
        source_file.write_text("[]")

        records = [
            # Inverted bounds: low > high
            {
                "eventId": "amt-bad-1",
                "version": 1,
                "memberId": "P000197",
                "chamber": "house",
                "transactionDate": "2026-02-01",
                "action": "purchase",
                "amountLow": 5000.0,
                "amountHigh": 1000.0,
                "ticker": "AAPL",
                "assetTypeCode": "ST",
                "sourceUrl": "https://example.com/amt1",
                "availableAt": "2026-02-15T00:00:00Z",
                "identitySource": "legislators",
            },
            # Negative bound
            {
                "eventId": "amt-bad-2",
                "version": 1,
                "memberId": "P000197",
                "chamber": "house",
                "transactionDate": "2026-02-01",
                "action": "purchase",
                "amountLow": -100.0,
                "ticker": "AAPL",
                "assetTypeCode": "ST",
                "sourceUrl": "https://example.com/amt2",
                "availableAt": "2026-02-15T00:00:00Z",
                "identitySource": "legislators",
            },
            # Preserved null bounds
            {
                "eventId": "amt-good-null",
                "version": 1,
                "memberId": "P000197",
                "chamber": "house",
                "transactionDate": "2026-02-01",
                "action": "purchase",
                "amountLow": None,
                "amountHigh": 15000.0,
                "ticker": "MSFT",
                "assetTypeCode": "ST",
                "sourceUrl": "https://example.com/amt3",
                "availableAt": "2026-02-15T00:00:00Z",
                "identitySource": "legislators",
            },
        ]
        res = adapt_austin_records(
            records,
            observed_at=self.sample_observed_at,
            as_of=self.sample_observed_at,
            source_ref="test",
            source_path=source_file,
        )
        self.assertEqual(len(res["events"]), 1)
        self.assertEqual(len(res["quarantined"]), 2)
        sidecar_meta = res["sidecar"]["amt-good-null"]["amounts"]
        self.assertIsNone(sidecar_meta["amountLow"])
        self.assertEqual(sidecar_meta["amountHigh"], 15000.0)

    def test_inactive_count_and_raw_reconciliation(self):
        """Test inactive versions are counted separately and all rows reconcile to total_raw."""
        source_file = self.tmp / "inactive.json"
        source_file.write_text("[]")

        records = [
            # Active at 2026-03-01
            {
                "eventId": "ev-1",
                "version": 1,
                "memberId": "P000197",
                "chamber": "house",
                "transactionDate": "2026-02-01",
                "action": "purchase",
                "ticker": "AAPL",
                "assetTypeCode": "ST",
                "sourceUrl": "https://example.com/1",
                "availableAt": "2026-02-15T00:00:00Z",
                "supersededAt": "2026-03-10T00:00:00Z",
                "identitySource": "legislators",
            },
            # Future version relative to as_of (2026-03-01)
            {
                "eventId": "ev-2",
                "version": 1,
                "memberId": "P000197",
                "chamber": "house",
                "transactionDate": "2026-02-01",
                "action": "purchase",
                "ticker": "AAPL",
                "assetTypeCode": "ST",
                "sourceUrl": "https://example.com/2",
                "availableAt": "2026-03-05T00:00:00Z",
                "supersededAt": None,
                "identitySource": "legislators",
            },
            # Superseded before as_of
            {
                "eventId": "ev-3",
                "version": 1,
                "memberId": "P000197",
                "chamber": "house",
                "transactionDate": "2026-01-01",
                "action": "purchase",
                "ticker": "AAPL",
                "assetTypeCode": "ST",
                "sourceUrl": "https://example.com/3",
                "availableAt": "2026-01-15T00:00:00Z",
                "supersededAt": "2026-02-01T00:00:00Z",
                "identitySource": "legislators",
            },
            # Quarantined row (missing memberId)
            {
                "eventId": "ev-4",
                "version": 1,
                "chamber": "house",
                "availableAt": "2026-02-15T00:00:00Z",
                "ticker": "AAPL",
            },
        ]
        res = adapt_austin_records(
            records,
            observed_at=self.sample_observed_at,
            as_of=parse_iso_datetime("2026-03-01T00:00:00Z"),
            source_ref="test",
            source_path=source_file,
        )
        self.assertEqual(res["manifest"]["valid_events_count"], 1)
        self.assertEqual(res["manifest"]["quarantined_count"], 1)
        self.assertEqual(res["manifest"]["inactive_count"], 2)
        self.assertEqual(
            res["manifest"]["total_raw_records"],
            res["manifest"]["valid_events_count"] + res["manifest"]["quarantined_count"] + res["manifest"]["inactive_count"],
        )

    def test_supersession_interval_validation(self):
        """Test supersession interval validation: supersededAt < availableAt is quarantined."""
        source_file = self.tmp / "super.json"
        source_file.write_text("[]")
        record = {
            "eventId": "ev-super-bad",
            "version": 1,
            "memberId": "P000197",
            "chamber": "house",
            "transactionDate": "2026-02-01",
            "action": "purchase",
            "ticker": "AAPL",
            "assetTypeCode": "ST",
            "sourceUrl": "https://example.com/super",
            "availableAt": "2026-02-15T00:00:00Z",
            "supersededAt": "2026-02-10T00:00:00Z",  # before availableAt!
            "identitySource": "legislators",
        }
        res = adapt_austin_records(
            [record],
            observed_at=self.sample_observed_at,
            as_of=self.sample_observed_at,
            source_ref="test",
            source_path=source_file,
        )
        self.assertEqual(len(res["events"]), 0)
        self.assertEqual(len(res["quarantined"]), 1)
        self.assertIn("invalid_supersession_interval", res["quarantined"][0]["reason"])

    def test_austin_schema_faithful_no_filing_date(self):
        """Test that Austin events adhere to PoliticalTradeEventRow schema with NO filingDate field."""
        source_file = self.tmp / "no_filing_date.json"
        record = {
            "eventId": "ev-nofil",
            "version": 1,
            "chamber": "house",
            "filerFirst": "Nancy",
            "filerLast": "Pelosi",
            "displayName": "Pelosi, Nancy",
            "owner": "spouse",
            "action": "purchase",
            "partialSale": False,
            "transactionDate": "2026-02-01",
            "ticker": "NVDA",
            "sourceTransactionId": "st-1",
            "assetDescription": "NVIDIA Corporation - Common Stock",
            "comment": None,
            "assetTypeCode": "ST",
            "assetTypeLabel": "Common Stock",
            "amountLow": 1000000.0,
            "amountHigh": 5000000.0,
            "firstAvailableAt": "2026-02-15T18:00:00Z",
            "availableAt": "2026-02-15T18:00:00Z",
            "supersededAt": None,
            "sourceDocId": "doc-1",
            "sourceRowIndex": 0,
            "sourceUrl": "https://example.com/nofil",
            "contributorRowIds": "c-1",
            "filerKey": "member:P000197",
            "memberId": "P000197",
            "identitySource": "legislators",
        }
        source_file.write_text(json.dumps([record]))
        res = adapt_austin_json(source_file, self.sample_observed_at, self.sample_observed_at, "sha-nofil")
        self.assertEqual(len(res["events"]), 1)
        self.assertEqual(res["events"][0]["event_id"], "ev-nofil")
        # Ensure filing_date was never manufactured
        self.assertNotIn("filingDate", res["events"][0])
        self.assertNotIn("filing_date", res["events"][0])

    def test_sqlite_read_only_and_political_trade_events_table(self):
        """Test SQLite adapter reads political_trade_events table via read-only URI without modifying it."""
        db_path = self.tmp / "events.db"
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE political_trade_events (
                event_id TEXT,
                version INTEGER,
                chamber TEXT,
                filer_first TEXT,
                filer_last TEXT,
                owner TEXT,
                action TEXT,
                partial_sale INTEGER,
                transaction_date TEXT,
                ticker TEXT,
                source_transaction_id TEXT,
                asset_description TEXT,
                comment TEXT,
                asset_type_code TEXT,
                asset_type_label TEXT,
                amount_low REAL,
                amount_high REAL,
                first_available_at TEXT,
                available_at TEXT,
                superseded_at TEXT,
                source_doc_id TEXT,
                source_row_index INTEGER,
                source_url TEXT,
                contributor_row_ids TEXT,
                filer_key TEXT,
                member_id TEXT,
                display_name TEXT,
                identity_source TEXT
            )
            """
        )
        cur.execute(
            """
            INSERT INTO political_trade_events VALUES (
                'event-sqlite-1', 1, 'house', 'Nancy', 'Pelosi', 'spouse', 'purchase', 0,
                '2026-02-01', 'NVDA', 'st-1', 'NVIDIA Common Stock', NULL, 'ST', 'Common Stock',
                1000.0, 5000.0, '2026-02-15T00:00:00Z', '2026-02-15T00:00:00Z', NULL,
                'doc-1', 0, 'https://example.com/sql', 'c-1', 'member:P000197', 'P000197',
                'Pelosi, Nancy', 'legislators'
            )
            """
        )
        conn.commit()
        conn.close()

        res = adapt_austin_sqlite(db_path, self.sample_observed_at, self.sample_observed_at, "sqlite-ref")
        self.assertEqual(len(res["events"]), 1)
        self.assertEqual(res["events"][0]["ticker"], "NVDA")

        # Missing political_trade_events table should raise ValueError (no fallback to trades)
        db_bad = self.tmp / "bad_table.db"
        conn2 = sqlite3.connect(db_bad)
        conn2.execute("CREATE TABLE trades (id TEXT)")
        conn2.close()
        with self.assertRaises(ValueError):
            adapt_austin_sqlite(db_bad, self.sample_observed_at, self.sample_observed_at, "bad-ref")

    def test_kadoa_auxiliary_provenance_and_skip_when_missing(self):
        """Test Kadoa auxiliary provenance, returns exclusion, and skip smoke when sample missing."""
        sample_path = self.tmp / "kadoa_synthetic.json"
        kadoa_data = [
            {
                "filer": {
                    "full_name": "Synthetic Representative",
                    "chamber": "house",
                    "branch": "house",
                },
                "trades": [
                    {
                        "id": "t-1",
                        "filer_id": "f-1",
                        "source_id": "s-1",
                        "doc_url": "https://example.com/doc1",
                        "ticker": "CMPO",
                        "asset_name": "ChargePoint Holdings Inc",
                        "asset_type": "Stock",
                        "transaction_date": "2026-02-01",
                        "filing_date": "2026-02-15",
                        "amount_range_low": 1001,
                        "amount_range_high": 15000,
                        "amount_range_label": "$1,001 - $15,000",
                        "comment": None,
                        "ret_since": 0.05,
                        "excess_since": 0.02,
                    },
                    {
                        "id": "t-2",
                        "filer_id": "f-1",
                        "source_id": "s-2",
                        "doc_url": "https://example.com/doc2",
                        "ticker": "AAPL",
                        "asset_name": "Apple Inc",
                        "asset_type": "Stock",
                        "transaction_date": "2026-02-02",
                        "filing_date": "2026-02-16",
                        "amount_range_low": 15001,
                        "amount_range_high": 50000,
                        "amount_range_label": "$15,001 - $50,000",
                        "comment": None,
                    },
                    {
                        "id": "t-3",
                        "filer_id": "f-1",
                        "source_id": "s-3",
                        "doc_url": "https://example.com/doc3",
                        "ticker": "MSFT",
                        "asset_name": "Microsoft Corporation",
                        "asset_type": "Stock",
                        "transaction_date": "2026-02-03",
                        "filing_date": "2026-02-17",
                        "amount_range_low": 1001,
                        "amount_range_high": 15000,
                        "amount_range_label": "$1,001 - $15,000",
                        "comment": None,
                    },
                ],
            }
        ]
        sample_path.write_text(json.dumps(kadoa_data))

        res = adapt_kadoa(sample_path, self.sample_observed_at, self.sample_observed_at, "kadoa-sha")
        self.assertFalse(res["manifest"]["backtest_ready"])
        self.assertEqual(res["manifest"]["total_trades_rows"], 3)
        self.assertEqual(res["events"], [])
        self.assertEqual(len(res["auxiliary_trades"]), 3)

        first_trade = res["auxiliary_trades"][0]
        self.assertEqual(first_trade["ticker"], "CMPO")
        self.assertTrue(first_trade["date_complete"])
        self.assertEqual(first_trade["amount_low"], 1001)
        self.assertNotIn("ret_since", first_trade)
        self.assertNotIn("excess_since", first_trade)

    def test_committees_actual_json_shape(self):
        """Test committee shape {committeeCode: [{bioguide: 'A000001', ...}]} yields memberId -> committee codes."""
        comm_file = self.tmp / "comm.json"
        data = {
            "HAGR": [{"bioguide": "P000197"}, {"bioguide": "C001120"}],
            "HSJU": [{"bioguide": "P000197"}],
        }
        comm_file.write_text(json.dumps(data))

        # Rejects non 40-hex SHA
        with self.assertRaises(ValueError):
            adapt_committees(comm_file, self.sample_observed_at, self.sample_observed_at, "short-sha")

        sha40 = "a" * 40
        # Rejects snapshot known_at > as_of
        as_of_past = parse_iso_datetime("2026-01-01T00:00:00Z")
        with self.assertRaises(ValueError):
            adapt_committees(comm_file, self.sample_observed_at, as_of_past, sha40)

        # Successful adaptation
        res = adapt_committees(comm_file, self.sample_observed_at, self.sample_observed_at, sha40)
        self.assertEqual(res["member_committees"]["P000197"], ["HAGR", "HSJU"])
        self.assertEqual(res["member_committees"]["C001120"], ["HAGR"])

    def test_output_file_exists_refusal(self):
        """Test that CLI refuses to overwrite an existing output file."""
        dummy_in = self.tmp / "in.json"
        dummy_in.write_text("[]")
        existing_out = self.tmp / "exists.json"
        existing_out.write_text("existing content")

        ret = main([
            "--source", "austin-json",
            "--input", str(dummy_in),
            "--output", str(existing_out),
            "--observed-at", "2026-03-01T00:00:00Z",
            "--source-ref", "test-ref",
        ])
        self.assertEqual(ret, 1)
        self.assertEqual(existing_out.read_text(), "existing content")


if __name__ == "__main__":
    unittest.main()
