# Input contract

The main CLI consumes a local JSON object with events, calendar, prices, and an optional boolean synthetic flag. See [the complete synthetic example](../examples/synthetic.json). JSON NaN and Infinity constants are rejected.

| Disclosure field | Type / meaning |
|---|---|
| event_id, member, ticker | Non-empty trimmed strings; stable identifiers; reconcile amendments before scoring |
| transaction_date | Canonical YYYY-MM-DD |
| available_at | Timezone-aware ISO-8601 public availability claim |
| first_seen_at | Timezone-aware ISO-8601 actual local observation; cannot precede availability |
| side | buy, sell, or exchange; default buy |
| asset_type | Explicit normalized category; only stock buys qualify; default stock |
| sector | Optional string; descriptive, not inferred |
| policy_match | Boolean, default false |
| policy_known_at | Timezone-aware evidence timestamp required for a true policy match |

The defaults are conveniences for explicitly normalized inputs, not a security master. Never omit asset_type for ambiguous real-world instruments. Canonicalize ticker aliases upstream and retain their dated mapping evidence.

calendar is an ascending, unique array of canonical exchange-session dates. It must include all actual sessions through the stated evaluation cutoff. The library checks shape and ordering, not exchange-calendar completeness.

prices maps symbol -> session date -> {open: number, close: number}. Values must be finite and positive, and use consistent currency, security identity, and corporate-action adjustments. Extra fields do not add execution validation. The benchmark defaults to SPY. Prices are used only after ranking.

## Adapter boundary

```bash
python3 -m congress_signal_lab.adapters --help
```

Supported sources are austin-json, austin-sqlite, kadoa, and committees. Each command requires a local input, new output path, observed-at timestamp, and source-ref. as-of defaults to observed-at. Raw data is not downloaded by these commands.

Austin JSON is an array of source records; SQLite requires political_trade_events and opens in read-only mode. Required source fields include eventId, positive integer version, availableAt, transactionDate, memberId, identitySource (legislators or override), House/Senate chamber, ticker, action, explicit stock classification, and a source URL. Camel/snake aliases are supported in code. Amount bounds may be null; otherwise finite, nonnegative, and ordered. Active revision intervals use availableAt <= as_of < supersededAt. Conflicting chains are quarantined conservatively. Naive timestamps are rejected rather than silently converted.

Austin import preserves observed-at as first_seen_at; selecting a historical as-of slice does not backdate local observation or create a historical replay. Its output has events, source metadata, sidecars, and quarantined rows. It must be combined with a separately sourced calendar and prices before event evaluation.

Kadoa is auxiliary only and emits zero scoring events. Committee mappings require a full 40-hex source commit and a known-at timestamp no later than the enrichment as-of time. Neither proves the historical validity of committee assignments.

Adapter output can contain original raw fields, source URLs and local file paths. Keep outputs local and review them before sharing. Dataset-level shape/time errors fail; malformed Austin rows are quarantined where supported. Runtime outputs are not safe-to-publish fixtures merely because an adapter created them.
