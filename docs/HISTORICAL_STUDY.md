# Legacy 365-day diagnostic study

**Status: needs revision.** These are preserved results of an original implementation, not returns of a corrected model or the package's event evaluator. [Independent findings](AUDIT_365.md) remain open. This study is not out-of-sample.

## Frozen inputs and population

Window: 2025-11-07 to 2026-11-06, 251 SPY sessions. Warm-up begins 2025-08-09. Austin dataset snapshot: aac6948946f1b46b992192d10154558290b68cd3. Prices: Yahoo adjusted daily open/close, applying adjusted-close / close to both.

| Unit | Count |
|---|---:|
| Rows in the two loaded annual shards | 27,339 |
| Unique event IDs in those shards | 27,326 |
| Eligible buys before member/ticker/filing-day collapse | 3,676 |
| Events after collapse across both shards | 3,002 |
| Evaluation-window eligible events | 1,339 |
| Filing-day cohorts per ranking variant | 160 |
| Selected symbols across variants, excluding SPY | 157 |

The selected symbols are not all verified equities. Complete price endpoints do not establish universe completeness, classification accuracy or execution quality. availableAt is a retrospective filing-day proxy, constructed at the end of the New York filing day, not certified first-publication capture.

## Original rules

Lag eligibility 0–45 days; freshness exp(-lag/60). Prior 90-day TF = 1 + ln(1+r), with r counting dates retained after member/ticker/filing-day collapse. IDF = 1 + ln((1+N)/(1+n)), with N prior distinct buying members and n buyers of this ticker. Consensus multiplies by 1 + ln(1+other distinct buyers over prior 30 days). Same-day observations are excluded from history. Rank top one per filing day; break ties by ticker, member, event ID. No committee overlay.

Start with $100,000. Each cohort receives up to 20% of initial capital, bounded by available cash. Weekend/holiday cohorts remain separate and enter in filing-day order at the next SPY session open. Buy before same-day close exits; no borrowing. Sell at entry index + 9 close. Fees are 10 bps per side: shares = budget / (open × 1.001), sale proceeds = shares × close × 0.999. Five final open positions are marked without exit fees. SPY is fully invested from first open to last close and pays both fees.

| Original variant | Net return | SPY difference | Max daily-close drawdown |
|---|---:|---:|---:|
| Freshness | +5.63% | -5.42 pp | 17.90% |
| TF-IDF | +28.49% | +17.44 pp | 9.94% |
| TF-IDF + consensus | +32.26% | +21.21 pp | 9.85% |
| SPY | +11.05% | — | 8.88% |

Consensus funded 140 positions: 135 closed, five open, 20 zero-cash skips. Closed wins: 74/135 (54.81%). At a 2% initial-capital cohort cap, return was +3.25%, with different cash usage and funded trades. This is not an allocation-independent factor effect.

## Concentration and fixed-rule sensitivities

| Check on original rankings | Net return |
|---|---:|
| 25 bps per side | +25.29% |
| Entry delayed one session, then hold ten sessions | +25.06% |
| Remove only the largest winning GNPX signal; resimulate cash | +15.91% |
| Remove the three largest winning signals; resimulate cash | +6.12% |
| Charge exit fees on the five final open positions | +32.17% |

Removal does not replace a signal with the day's second-ranked candidate. These are sensitivity experiments, not statistical confidence intervals or corrected-model runs. The three largest positions supplied 68.4% of net profit. Simply subtracting their original PnL leaves +10.21%, an arithmetic residual; cash resimulation gives +6.12% because later allocations change. January 2026 contributed +19.82%; the strategy beat SPY in six of thirteen calendar-month buckets, including two partial months.

## Reproducibility boundary

The repository includes four daily NAV series and summaries in [year-data.json](../assets/research/year-data.json), plus a renderer. A reader can reconcile totals/drawdowns/monthly compounding and redraw figures. The raw filings, prices, full trade ledger and annual engine are not distributed. The earlier research-environment accounting checks cannot be rerun from this repository alone.

An earlier 69-session study used different data and a policy overlay. Its results are not combined with this study. Neither study validates future alpha.
