# Historical experiment audit — 2026-11-09

**Needs revision.** Independent research-environment accounting reproduced the original +32.2630%, but data, algorithm and execution findings prevent treating it as a verified profitable strategy. This English record preserves the material findings; no corrected annual run is claimed.

| ID | Finding | Status / required evidence |
|---|---|---|
| HIST-001 | TF history was collapsed by member, ticker and filing day before counting distinct trade dates. 263 multi-date groups lost 391 date instances; 74 evaluation candidates changed TF. Full-date history changes 11/160 TF-IDF selections and 10/160 consensus selections. | OPEN. Preserve all dates, acquire missing replacement-symbol prices, and rerun every comparator with a frozen corrected spec. |
| HIST-002 | GIGB, a bond ETF mislabeled Stock, entered Freshness. AJINF was simulated on entry and exit dates with zero cached volume. | OPEN. Dated security classification and explicit fill-quality gates must be applied before a fresh complete simulation. |
| HIST-003 | availableAt is a filing-day proxy in a retrospective snapshot. Historical completeness and correction visibility are unverified. | OPEN. Capture timestamped versions and document missing/amended records. |
| HIST-004 | Daily bars and fixed fees do not establish execution capacity. The GNPX entry budget was about 2.17% of daily volume × open; another FMAO order reached 3.65%. | OPEN. Spread/auction/depth evidence and a capacity model are needed. |
| HIST-005 | Three positions supplied 68.4% of net profit; deleting their signals with cash resimulation leaves +6.12%. The window overlaps historical strategy selection. | OPEN. Freeze rules and evaluate untouched data with suitable risk and sector controls. |
| HIST-006 | The full annual engine, raw input contract and complete frozen ledgers are absent from the portable repository. | OPEN. A separately executable historical runner and permission-compatible input acquisition process are needed for end-to-end replication. |

The +32.26% number belongs to the original algorithm. A core regression that preserves distinct dates does not repair that historical result. HUBB and SHOP were missing from the corrected consensus replacement-price cache at the prior audit; corrected returns were not calculated.

GIGB contributed -$58.45 and AJINF +$863.12 in Freshness. No zero/missing entry volume was found among 140 funded consensus entries, but OTC exposure and impact remain unresolved. This limited check does not clear the complete universe.

Primary disclosure checks covered two of the three largest winners: [GNPX House report](https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/20033746.pdf) and [BE House report](https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/20035143.pdf). The ANET Senate page was unavailable during that review; secondary agreement was not primary verification. These are samples, not certification of all records.

GNPX's 1:22 reverse split occurred outside the January holding period; the [Nasdaq corporate-action notice](https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2026-495) and price conversion did not show a split-generated profit. This does not prove fills were achievable.

The 13 loaded events whose earliest available row was already version 2 had 496–876 day lag and were excluded. No selected-event impact was observed; full earliest-version recovery was not established. Data/output hashes matched the historical manifest, but the recorded verifier-script hash was stale. Preserve this provenance gap rather than relabeling it verified.

See [release audit](AUDIT.md) for the separate software-publication review and [historical study](HISTORICAL_STUDY.md) for the original specification.
