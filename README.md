<p align="center"><img src="assets/brand/readme-hero.jpeg" alt="Congress Signal Lab" width="100%" /></p>

# Congress Signal Lab

**Find the signal in congressional disclosures.** An offline Python research toolkit for asking whether repeated buying, cross-member rarity, and disclosure timing help distinguish investment signals.

**Research and education only — not investment advice.** [Read the disclaimer](#disclaimer).

[Results](#historical-results) · [Return drivers](#monthly-schedule--return-drivers) · [Quickstart](#quickstart) · [Methodology](docs/METHODOLOGY.md) · [Input contract](docs/INPUT_SCHEMA.md) · [Historical study](docs/HISTORICAL_STUDY.md) · [Audit](docs/AUDIT.md)

## Historical results

**+32.26% vs. +11.05% for SPY** in the original 365-day backtest — a **21.21 percentage-point difference**, after modeled trading costs.

> **Legacy diagnostic, needs revision.** The original annual implementation produced +32.26%. Its TF history lost distinct transaction dates, and the comparison universe contained an ETF and a zero-volume simulated trade. Corrected historical portfolio results are pending. The window overlaps historical parameter selection and is not out-of-sample. See the [full findings](docs/AUDIT_365.md).

Window: 2025-11-07 through 2026-11-06, 251 SPY sessions. Next-session open entry, 10-session holding period, 10 bps per side, up to 20% of initial capital per filing-day cohort, available-cash constrained. Committee relevance was omitted.

| Original ranking | Net return | Difference vs. SPY | Maximum daily-close drawdown |
|---|---:|---:|---:|
| Freshness | +5.63% | -5.42 pp | 17.90% |
| TF-IDF | +28.49% | +17.44 pp | 9.94% |
| **TF-IDF + consensus** | **+32.26%** | **+21.21 pp** | **9.85%** |
| SPY buy and hold | +11.05% | — | 8.88% |

![Legacy diagnostic NAV and drawdown; corrected rerun pending](assets/research/year/equity.png)

## Monthly Schedule & Return Drivers

These figures describe the same original historical experiment above; corrected portfolio results remain pending.

### A standout month: +19.82% in January 2026

![Monthly Return Heatmap — legacy results; first and last months are partial](assets/research/year/monthly.png)

[View the full-size heatmap (SVG)](assets/research/year/monthly.svg)

Returns arrive in episodic bursts rather than steady monthly outperformance: January 2026 returned **+19.82%**, and `consensus_20cap` beat SPY in **6 of 13 monthly buckets**. November 2025 and November 2026 are partial calendar months.

### What drove the return?

![Return Attribution and Capital Cap Sensitivity — legacy results](assets/research/year/drivers.png)

[View the full-size attribution chart (SVG)](assets/research/year/drivers.svg)

- **Top-position concentration:** The three largest winning positions — `GNPX` **+12.49 pp**, `BE` **+6.29 pp**, and `ANET` **+3.28 pp** — account for **68.4% of total net profit**. Subtracting their original PnL leaves **+10.21%** by arithmetic attribution. Removing those signals and **resimulating cash** instead gives **+6.12%**, without replacing them with second-ranked candidates. These are different calculations: removing trades changes the cash available to later cohorts.
- **Capital allocation matters:** At a **2% initial-capital cap** per cohort, consensus returned **+3.25%** with **1.47% maximum daily-close drawdown**, versus **+32.26%** and **9.85% drawdown** at the **20% cap**. Different cash utilization and funded trades drive this sensitivity; the simulation uses **no margin borrowing**.

Full-precision daily NAVs and monthly returns: [`year-data.json`](assets/research/year-data.json). Methodology and sensitivity checks: [365-day study](docs/HISTORICAL_STUDY.md). Known defects and validation limits: [historical audit](docs/AUDIT_365.md). A return difference is not risk-adjusted alpha.

## The idea: read portfolios like documents

A member's disclosed buying history is a document; a ticker is a token. TF measures repeated buying on distinct transaction dates. IDF discounts tickers bought by many members. The resulting score is an interpretable research hypothesis, not an estimate of expected returns.

## Quickstart

Python 3.11 or later. The scoring core and tests use only the standard library. An IANA timezone database with America/New_York must be available; on systems without one, install the optional tzdata package.

```bash
git clone https://github.com/jrdeng93/CongressSignalLab.git
cd CongressSignalLab
python3 -m unittest discover -s tests -v
python3 -m congress_signal_lab --input examples/synthetic.json --output output/demo.json --horizon 2
python3 scripts/audit_public_tree.py
```

The repository is currently private during release preparation; cloning requires access. The demo uses invented data. Output includes selections, exclusions, coverage, input SHA-256, and forward event returns. Output files are created exclusively: use a new filename for each run.

Optional installation in a virtual environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install .
congress-signal-lab --input examples/synthetic.json --output output/installed-demo.json --horizon 2
```

## What you can run

| Component | Included behavior |
|---|---|
| Ranking | Prior-observation-day TF-IDF, filing-lag decay, basket-size adjustment, optional dated policy evidence |
| Event evaluation | Next supplied session entry, fixed holding horizon, modeled costs, matched-date SPY comparison |
| Local adapters | Austin JSON/read-only SQLite; auxiliary Kadoa provenance; dated committee snapshots |
| Audit tools | Synthetic regressions, publication hygiene checks, source and methodology notes |
| Historical figures | Redraw frozen derived NAV summaries without downloading vendor data |

The core produces **event returns**, not a cash-funded portfolio NAV. Its variants are `all`, `tfidf`, and `tfidf_policy`. The annual consensus portfolio experiment used a separate research engine. That engine and its raw datasets are not bundled; running this package does not reproduce the annual headline.

```text
Local disclosure files -> validation / quarantine -> observed-day ranking
                                                   |
Local session calendar + price bars ----------------+-> forward-event ledger
Frozen historical NAV summary ------------------------> diagnostic figures
```

## Continue the research

- [Audit entry point](docs/AUDIT.md): stable findings, reproduction commands, and evidence required to close each issue.
- [Methodology](docs/METHODOLOGY.md) and [input schema](docs/INPUT_SCHEMA.md): exact shipped-core behavior.
- [Reproducibility](docs/REPRODUCIBILITY.md): what can be rerun and what cannot.
- [Data sources and rights](docs/DATA_SOURCES.md): source versions, timing limitations, and redistribution boundaries.
- [Related work](docs/RELATED_WORK.md), [contributing](CONTRIBUTING.md), and [security](SECURITY.md).

MIT covers the code. Third-party data rights are separate. No raw vendor datasets, credentials, account integrations, or order execution are included. This is a research library; no live profitability or execution capacity has been established.

## Disclaimer

Congress Signal Lab is an independent, experimental project for **research and educational purposes only**. Nothing in this repository is investment, financial, legal, or tax advice, a personalized recommendation, or an offer or solicitation to buy or sell any security. No advisory relationship is created by using this project.

- **Hypothetical performance:** Results are historical simulations, not actual investment returns. Rules were explored using overlapping historical data, creating selection and overfitting risk. Reported results include known implementation and data limitations documented in the [audit](docs/AUDIT.md); corrected annual results remain pending. Past or simulated performance does not guarantee future results.
- **Data and execution limitations:** Public disclosures may be delayed, incomplete, amended, or incorrectly classified. Market data and software may contain errors. Modeled prices and fees do not establish executable fills, liquidity, capacity, or real-world returns; actual costs, taxes, and losses may differ materially.
- **Investment risk:** Investing can result in loss of capital. Independently verify inputs and conclusions, assess suitability for your circumstances, and seek qualified professional advice where appropriate before making investment decisions.
- **No affiliation or allegations:** This project is not affiliated with or endorsed by the U.S. Congress, any government agency, any member of Congress, or any data provider. A score or trading pattern does not establish intent, access to nonpublic information, insider trading, or wrongdoing.
- **Software and data rights:** The software is provided “as is” under the [MIT License](LICENSE), without warranty as specified there. Third-party data remains subject to its own terms and restrictions; public availability does not imply unrestricted reuse or redistribution. See [data sources and rights](docs/DATA_SOURCES.md).
