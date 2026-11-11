# Shipped core methodology

This specification describes congress_signal_lab/core.py. It does not describe the legacy annual portfolio engine.

A disclosure has a trade date, claimed public availability timestamp, and actual local first-observation timestamp. Both timestamps must carry timezones. The observation day is first_seen_at converted to America/New_York. Entries occur strictly after that local calendar day. A date proxy is not proof of historical availability.

## Eligibility and history

Only explicit stock buys with filing lag from 0 through 45 calendar days qualify. Filing lag is the New York availability date minus transaction date; it is not observation lag. Same-member/ticker buy-and-sell pairs within an observed day are excluded. Asset labels are trusted inputs, not independently verified security classifications.

History uses strictly earlier observation days within the prior 90 calendar days. Same-day events cannot inflate each other's histories. Distinct eligible transaction dates are retained even when multiple dates were disclosed in one observed batch. Duplicate event IDs fail; amendments must be reconciled upstream.

## Score

- TF = 1 + ln(1 + distinct prior member/ticker buy dates).
- IDF = 1 + ln((1 + distinct prior buying members) / (1 + prior buyers of this ticker)).
- Freshness = exp(-filing_lag / 30).
- Basket multiplier = 1 / sqrt(distinct securities in the member's current observed batch).
- tfidf = TF × IDF × freshness × basket multiplier.
- tfidf_policy adds a factor of 2 only if policy_match is true and dated evidence was known by first_seen_at.

Basket size counts the supplied batch, including records later excluded from buying eligibility. This is an explicit v0.1 rule, not a calibrated conviction measure. Policy inputs require external evidence; the package does not infer expertise, private information, or legal misconduct.

select ranks before examining prices, keeps at most one event per ticker per day, and defaults to three tickers. Ties use ticker, member, then event ID. The all variant retains every eligible distinct ticker and ignores the top-k cap. The CLI currently uses the default top-k of three. The start date filters outputs while preserving earlier history.

## Forward-event evaluation

The caller must supply a complete, ordered, unique exchange-session calendar and consistent adjusted open/close prices. Entry is the first supplied session strictly after observation day. Exit is the close of holding session H, counting entry as session 1.

Net event return = exit_close / entry_open - 1 - 2 × cost_bps / 10,000. This is an entry-notional fee approximation, not exact cash/share accounting. SPY uses the same endpoints and fee approximation. Missing chosen endpoints are reported as missing_prices and never trigger silent replacement. Positions without a full future horizon are immature; they are not marked into a portfolio value.

No liquidity, volume, spread, settlement, taxes, borrowing, capital allocation, or daily NAV model is implemented here. A valid price is not a verified executable fill. Cross-event means are not portfolio returns.

## Difference from the annual experiment

The annual engine used a 60-day freshness constant, top one per filing day, an additional 30-day consensus multiplier, no basket adjustment or policy overlay, and a funded cash ledger. Its history was collapsed before TF construction. The shipped core keeps distinct dates and must not inherit the legacy +32.26% result. See [historical methodology](HISTORICAL_STUDY.md).
