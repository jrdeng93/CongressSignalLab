import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from .core import Disclosure, select, evaluate


def _reject_nonfinite_constant(token: str):
    raise ValueError(f'Non-finite JSON constant not allowed: {token}')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Offline disclosure score and forward-return evaluation')
    parser.add_argument('--input', type=Path, required=True, help='JSON fixture or locally normalized dataset')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--variant', choices=['all', 'tfidf', 'tfidf_policy'], default='tfidf')
    parser.add_argument('--horizon', type=int, default=20)
    parser.add_argument('--cost-bps', type=float, default=10)
    parser.add_argument('--start', default='0001-01-01')
    args = parser.parse_args(argv)
    if not args.input.exists() or not args.input.is_file():
        parser.error('Input must be an existing file')
    if args.input.resolve() == args.output.resolve() or args.output.exists():
        parser.error('Output must be a new file, distinct from input')
    raw = args.input.read_bytes()
    data = json.loads(raw, parse_constant=_reject_nonfinite_constant)
    if not isinstance(data, dict):
        raise ValueError('Input dataset must be a JSON object')
    for key in ('events', 'prices', 'calendar'):
        if key not in data:
            raise ValueError(f'Missing required top-level key: {key}')
    if not isinstance(data['events'], list):
        raise ValueError('events must be a list of disclosure objects')
    for ev in data['events']:
        if not isinstance(ev, dict):
            raise ValueError('Each event entry must be a JSON object')
    if 'synthetic' in data and not isinstance(data['synthetic'], bool):
        raise ValueError('synthetic flag must be a boolean when provided')
    picks, excluded = select([Disclosure(**x) for x in data['events']], args.variant, start=args.start)
    ledger = evaluate(picks, data['prices'], data['calendar'], args.horizon, args.cost_bps)
    mature = [x for x in ledger if x['status'] == 'mature']
    report = dict(input_sha256=hashlib.sha256(raw).hexdigest(),
                  synthetic=bool(data.get('synthetic', False)), variant=args.variant,
                  horizon=args.horizon, cost_bps_per_side=args.cost_bps,
                  coverage=dict(Counter(x['status'] for x in ledger)),
                  mean_event_net_return=sum(x['net_return'] for x in mature)/len(mature) if mature else None,
                  warning='Event returns are not portfolio returns or proof of alpha.',
                  selections=picks, exclusions=excluded, ledger=ledger)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as f:
        json.dump(report, f, indent=2, allow_nan=False)
    print(json.dumps({'synthetic': report['synthetic'], 'coverage': report['coverage']}))


if __name__ == '__main__':
    main()
