# Data sources, provenance and rights

The distribution contains project code, synthetic fixtures, an author-provided generated banner, and aggregate historical research outputs. It contains no raw disclosure shards, member trade logs, vendor OHLC caches, credentials, or account configuration. Adapter outputs can contain raw input fields and must remain outside the published tree.

| Source | Role and boundary |
|---|---|
| [Austin congressional-disclosures](https://github.com/austin-starks/congressional-disclosures) | Source extraction/schema reference and local JSON/SQLite adapter. Code reference 998312fac28815ff096404f08c0d975cd0072591. |
| [Austin congressional-stock-trades](https://huggingface.co/datasets/austin-starks/congressional-stock-trades) | Annual study snapshot aac6948946f1b46b992192d10154558290b68cd3; 2025 and 2026 shards, not distributed. |
| Yahoo Finance daily bars | Historical adjusted price inputs, not distributed. Current adjustment factors and historical quote availability remain limitations. |
| [Kadoa congress-trading-monitor](https://github.com/kadoa-org/congress-trading-monitor) | Auxiliary provenance adapter; no scoring events or upstream performance metrics imported. |
| [unitedstates/congress-legislators](https://github.com/unitedstates/congress-legislators) | Stable member IDs and dated committee snapshots; current membership is not a historical interval database. |

Frozen annual shard SHA-256:

- 2025: 32e00744a3b0df6b9b4d9adc94caafd0837e2d04bc9f03be759d9e2666d0c4ea
- 2026: 3b1d9a7d5df65fc489bf56a9c69d5afa0ca6efc79db847d089af1a82a82637c8

The earlier 69-session pilot used CapitolTrades tracker observations, Alpaca/IEX bars, and an April 2026 committee snapshot. It is a different study; its private inputs and performance artifacts are not part of this candidate.

## License boundary

[MIT](../LICENSE) applies to project code. It does not relicense third-party data, remove provider terms, or grant rights to underlying disclosure reports. The [Austin data-use notice](https://huggingface.co/datasets/austin-starks/congressional-stock-trades/blob/main/LICENSE_DATA.md), reviewed 2026-11-11, explicitly does not offer unrestricted open-data licensing. Review that notice and applicable source terms for your intended use. No legal or data-redistribution clearance is represented here.

The charts and derived NAV summary describe one historical experiment with known defects; no raw data download is bundled or automated. The banner was supplied by the project owner after image generation. Referenced projects are inspirations and data/schema references, not endorsements or verified performance comparators.
