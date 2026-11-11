"""Small offline research core. No broker, network, or credential dependencies."""
from bisect import bisect_right
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime
from math import exp, isfinite, log, log1p, sqrt
from zoneinfo import ZoneInfo

NY = ZoneInfo('America/New_York')
PLACEHOLDER_IDS = {'--', 'N/A', 'NONE', 'UNKNOWN', 'NULL'}
VALID_SIDES = {'buy', 'sell', 'exchange'}


def timestamp(value):
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError('Availability timestamps must be non-empty ISO-8601 strings')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None or result.tzinfo.utcoffset(result) is None:
        raise ValueError('Availability timestamps must include a timezone')
    return result


def iso_date(value):
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError('Dates must be canonical YYYY-MM-DD strings')
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError('Dates must be canonical YYYY-MM-DD strings')
    return parsed


def _is_valid_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


@dataclass(frozen=True)
class Disclosure:
    event_id: str
    member: str
    ticker: str
    transaction_date: str
    available_at: str
    first_seen_at: str
    side: str = 'buy'
    asset_type: str = 'stock'
    sector: str = ''
    policy_match: bool = False
    policy_known_at: str | None = None

    def __post_init__(self):
        for field_name, val in (('event_id', self.event_id), ('member', self.member), ('ticker', self.ticker)):
            if not isinstance(val, str) or not val.strip() or val != val.strip():
                raise ValueError(f'Identifier {field_name} must be a non-empty trimmed string')
            if val.upper() in PLACEHOLDER_IDS:
                raise ValueError(f'Identifier {field_name} cannot be a placeholder value')
        if not isinstance(self.side, str) or self.side not in VALID_SIDES:
            raise ValueError(f'Invalid side: {self.side!r}')
        if not isinstance(self.asset_type, str) or not self.asset_type.strip() or self.asset_type != self.asset_type.strip():
            raise ValueError('asset_type must be a non-empty trimmed string')
        if not isinstance(self.sector, str):
            raise ValueError('sector must be a string')
        if not isinstance(self.policy_match, bool):
            raise ValueError('policy_match must be a boolean')
        tx_date = iso_date(self.transaction_date)
        avail_dt = timestamp(self.available_at)
        seen_dt = timestamp(self.first_seen_at)
        if seen_dt < avail_dt:
            raise ValueError('First observation precedes public availability')
        if tx_date > avail_dt.astimezone(NY).date():
            raise ValueError('Transaction date follows public availability')
        if self.policy_match and self.policy_known_at is None:
            raise ValueError('Policy match requires dated evidence')
        if self.policy_known_at is not None:
            timestamp(self.policy_known_at)

    @property
    def day(self):
        return timestamp(self.first_seen_at).astimezone(NY).date()

    @property
    def lag(self):
        return (timestamp(self.available_at).astimezone(NY).date() - iso_date(self.transaction_date)).days


def score_components(event, history, basket_size=1, lookback=90):
    """Use previous observation days only; same-day batches cannot self-inflate."""
    if not isinstance(event, Disclosure):
        raise ValueError('event must be a Disclosure instance')
    if (
        not isinstance(basket_size, int)
        or isinstance(basket_size, bool)
        or basket_size < 1
        or not isinstance(lookback, int)
        or isinstance(lookback, bool)
        or lookback < 1
    ):
        raise ValueError('Basket size and lookback must be positive integers')
    prior = []
    for x in history:
        if not isinstance(x, Disclosure):
            raise ValueError('history must contain Disclosure instances')
        if 0 < (event.day - x.day).days <= lookback and x.side == 'buy' and x.asset_type == 'stock' and 0 <= x.lag <= 45:
            prior.append(x)
    members = {x.member for x in prior}
    holders = {x.member for x in prior if x.ticker == event.ticker}
    repetitions = {x.transaction_date for x in prior
                   if x.member == event.member and x.ticker == event.ticker}
    tf = 1 + log1p(len(repetitions))
    idf = 1 + log((1+len(members))/(1+len(holders)))
    freshness = exp(-event.lag/30)
    basket = 1/sqrt(basket_size)
    policy = 2 if (event.policy_match and timestamp(event.policy_known_at)
                   <= timestamp(event.first_seen_at)) else 1
    return dict(tf=tf, idf=idf, freshness=freshness, basket=basket,
                policy=policy, tfidf=tf*idf*freshness*basket,
                tfidf_policy=tf*idf*freshness*basket*policy)


def select(events, variant='tfidf', top_k=3, start='0001-01-01'):
    """Rank before prices are examined. Returns selections and excluded reasons."""
    if (
        variant not in {'all', 'tfidf', 'tfidf_policy'}
        or not isinstance(top_k, int)
        or isinstance(top_k, bool)
        or top_k < 1
    ):
        raise ValueError('Invalid ranking configuration')
    start_date = iso_date(start)
    events = list(events)
    for e in events:
        if not isinstance(e, Disclosure):
            raise ValueError('All events must be Disclosure instances')
    if len({e.event_id for e in events}) != len(events):
        raise ValueError('Duplicate event_id; reconcile amendments upstream')
    batches = defaultdict(list)
    for e in events:
        batches[e.day].append(e)
    history, selected, exclusions = [], [], []
    for day, batch in sorted(batches.items()):
        baskets, sides = defaultdict(set), defaultdict(set)
        for e in batch:
            baskets[e.member].add(e.ticker)
            sides[e.member, e.ticker].add(e.side)
        candidates = []
        for e in batch:
            reason = ('not_stock_buy' if e.asset_type != 'stock' or e.side != 'buy'
                      else 'stale' if e.lag > 45
                      else 'opposite_batch' if 'sell' in sides[e.member, e.ticker]
                      else None)
            if reason:
                exclusions.append(dict(event_id=e.event_id, reason=reason))
                continue
            c = score_components(e, history, len(baskets[e.member]))
            candidates.append((e, c))
        if day >= start_date:
            ranked = sorted(candidates, key=lambda x: (
                -(x[1][variant] if variant != 'all' else 0), x[0].ticker, x[0].member, x[0].event_id))
            tickers = set()
            for e, components in ranked:
                if e.ticker in tickers:
                    continue
                if variant != 'all' and len(tickers) >= top_k:
                    break
                tickers.add(e.ticker)
                selected.append(dict(event=asdict(e), components=components))
        # Keep distinct underlying dates for TF; sets remove repeated same-date counts.
        history.extend(e for e, _ in candidates)
    return selected, exclusions


def evaluate(selected, prices, calendar, horizon=20, cost_bps=10, benchmark='SPY'):
    """Forward event returns only; these means are NOT account/portfolio returns.

    prices: {symbol: {session ISO date: {open: positive float, close: positive float}}}
    calendar must be a complete exchange-session list through the data cutoff.
    """
    if (
        not isinstance(horizon, int)
        or isinstance(horizon, bool)
        or horizon < 1
        or not _is_valid_number(cost_bps)
        or cost_bps < 0
    ):
        raise ValueError('Invalid horizon/cost')
    if not isinstance(benchmark, str) or not benchmark.strip() or benchmark != benchmark.strip():
        raise ValueError('Invalid benchmark symbol')
    if not isinstance(calendar, list) or not calendar:
        raise ValueError('Calendar must be sorted, unique and nonempty')
    for day in calendar:
        iso_date(day)
    if calendar != sorted(set(calendar)):
        raise ValueError('Calendar must be sorted, unique and nonempty')
    if not isinstance(prices, dict):
        raise ValueError('Prices must be a mapping of symbol to session bars')
    for sym, bars in prices.items():
        if not isinstance(sym, str) or not sym.strip() or not isinstance(bars, dict):
            raise ValueError('Prices must map non-empty symbol strings to session dicts')
        for day, bar in bars.items():
            iso_date(day)
            if not isinstance(bar, dict):
                raise ValueError('Each price bar must be a dict with open and close')
            for k in ('open', 'close'):
                if k not in bar or not _is_valid_number(bar[k]) or bar[k] <= 0:
                    raise ValueError('Prices must be finite and positive')
    out = []
    seen_ids = set()
    for row in selected:
        if not isinstance(row, dict) or not isinstance(row.get('event'), dict):
            raise ValueError('Selected items must contain an event mapping')
        e = Disclosure(**row['event'])
        if e.event_id in seen_ids:
            raise ValueError('Duplicate event_id in selected rows')
        seen_ids.add(e.event_id)
        i = bisect_right(calendar, e.day.isoformat())
        j = i+horizon-1
        rec = dict(event_id=e.event_id, ticker=e.ticker, observed_day=e.day.isoformat())
        if j >= len(calendar):
            out.append(dict(rec, status='immature'))
            continue
        entry, exit_day = calendar[i], calendar[j]
        if any(d not in prices.get(s, {}) for s in (e.ticker, benchmark) for d in (entry, exit_day)):
            out.append(dict(rec, status='missing_prices'))
            continue
        gross = prices[e.ticker][exit_day]['close']/prices[e.ticker][entry]['open']-1
        control = prices[benchmark][exit_day]['close']/prices[benchmark][entry]['open']-1
        out.append(dict(rec, status='mature', entry=entry, exit=exit_day,
                        net_return=gross-2*cost_bps/10000,
                        benchmark_net_return=control-2*cost_bps/10000,
                        excess_return=gross-control))
    return out
