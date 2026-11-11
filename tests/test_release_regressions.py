"""Independent regressions for publication-review input and timing findings."""
import contextlib
import io
import json
import math
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from congress_signal_lab.core import Disclosure, select, score_components, evaluate
from congress_signal_lab.__main__ import main as score_main
from congress_signal_lab.adapters import adapt_austin_records, adapt_kadoa, adapt_committees, parse_iso_datetime, main as adapter_main


def event(**changes):
    data = dict(event_id='e', member='A', ticker='XYZ', transaction_date='2026-01-01',
                available_at='2026-01-03T16:00:00Z', first_seen_at='2026-01-03T17:00:00Z')
    return Disclosure(**(data | changes))


def source_record(**changes):
    return dict(eventId='e', version=1, chamber='house', memberId='A000001',
                identitySource='legislators', ticker='XYZ', sourceUrl='https://example.org/filing',
                transactionDate='2026-01-01', availableAt='2026-01-03T16:00:00Z',
                action='purchase', assetTypeCode='ST', assetTypeLabel='Stock') | changes


class ReleaseRegressions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'input.json'
        self.path.write_text('[]')
        self.now = parse_iso_datetime('2026-04-01T00:00:00Z')

    def adapt(self, rows, as_of=None):
        return adapt_austin_records(rows, self.now, as_of or self.now, 'synthetic-v1', self.path)

    def test_identifiers_reject_empty_boolean_and_placeholder(self):
        for key in ('event_id', 'member', 'ticker'):
            for bad in (' ', True, 'UNKNOWN'):
                with self.subTest(key=key, bad=bad), self.assertRaises(ValueError):
                    event(**{key: bad})

    def test_string_false_cannot_enable_policy_multiplier(self):
        with self.assertRaises(ValueError):
            event(policy_match='false', policy_known_at='2026-01-01T00:00:00Z')

    def test_integer_configuration_is_not_boolean_or_float(self):
        for bad in (True, 1.5, 0):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError): select([event()], top_k=bad)
                with self.assertRaises(ValueError): evaluate([], {}, ['2026-01-05'], horizon=bad)
        with self.assertRaises(ValueError): evaluate([], {}, ['2026-01-05'], cost_bps=True)

    def test_all_distinct_dates_survive_same_observed_batch(self):
        first = event(event_id='one')
        second = event(event_id='two', transaction_date='2026-01-02')
        now = event(event_id='next', transaction_date='2026-01-05', available_at='2026-01-06T16:00:00Z', first_seen_at='2026-01-06T17:00:00Z')
        picks, _ = select([first, second, now], start='2026-01-06')
        self.assertEqual(len(picks), 1)
        self.assertAlmostEqual(picks[0]['components']['tf'], 1 + math.log(3))

    def test_direct_score_excludes_stale_history(self):
        old = event(transaction_date='2025-10-01')
        now = event(first_seen_at='2026-01-07T00:00:00Z')
        self.assertEqual(score_components(now, [old])['tf'], 1)

    def test_duplicate_selected_events_rejected(self):
        row = {'event': asdict(event())}
        with self.assertRaises(ValueError): evaluate([row, row], {}, ['2026-01-05'])

    def test_canonical_calendar_and_prices_are_required(self):
        with self.assertRaises(ValueError): evaluate([], {}, ['20260105'])
        with self.assertRaises(ValueError): evaluate([], {'XYZ': {'2026-01-05': {'open': True, 'close': 100}}}, ['2026-01-05'])

    def test_malformed_rows_and_invalid_versions_are_quarantined(self):
        result = self.adapt([None, source_record(version=True), source_record(eventId='good')])
        self.assertEqual(len(result['events']), 1)
        self.assertEqual(len(result['quarantined']), 2)
        self.assertEqual(result['manifest']['total_raw_records'], 3)

    def test_invalid_amounts_stay_valid_json(self):
        for value in (True, float('nan'), float('inf'), -1):
            with self.subTest(value=value):
                result = self.adapt([source_record(amountLow=value)])
                self.assertFalse(result['events'])
                self.assertEqual(len(result['quarantined']), 1)
                json.dumps(result, allow_nan=False)

    def test_valid_url_required_without_crashing_batch(self):
        for url in ('httpfake', 'https://', 'https://['):
            with self.subTest(url=url):
                result = self.adapt([source_record(sourceUrl=url)])
                self.assertFalse(result['events'])
                self.assertEqual(len(result['quarantined']), 1)

    def test_amendment_boundary_selects_new_version(self):
        boundary = '2026-02-01T00:00:00Z'
        old = source_record(supersededAt=boundary)
        new = source_record(version=2, availableAt=boundary)
        result = self.adapt([old, new], parse_iso_datetime(boundary))
        self.assertEqual(result['sidecar']['e']['version'], 2)
        self.assertEqual(result['manifest']['inactive_count'], 1)
        self.assertEqual(result['events'][0]['first_seen_at'], self.now.isoformat())

    def test_corrupt_revision_cannot_leave_valid_survivor(self):
        result = self.adapt([source_record(), source_record(version=False)])
        self.assertFalse(result['events'])
        self.assertEqual(len(result['quarantined']), 2)

    def test_adapter_direct_apis_reject_naive_time(self):
        naive = self.now.replace(tzinfo=None)
        for fn, ref in ((adapt_kadoa, 'test-ref'), (adapt_committees, 'a'*40)):
            with self.subTest(fn=fn.__name__), self.assertRaises(ValueError):
                fn(self.path, naive, naive, ref)

    def test_committee_cli_allows_known_snapshot_before_enrichment(self):
        self.path.write_text('{"HSIF": [{"bioguide": "A000001"}]}')
        out = Path(self.tmp.name) / 'committee.json'
        with contextlib.redirect_stdout(io.StringIO()):
            code = adapter_main(['--source', 'committees', '--input', str(self.path), '--output', str(out),
                                 '--observed-at', '2026-01-01T00:00:00Z', '--as-of', '2026-02-01T00:00:00Z', '--source-ref', 'a'*40])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.read_text())['member_committees']['A000001'], ['HSIF'])

    def test_score_cli_rejects_nonfinite_json_and_does_not_overwrite(self):
        self.path.write_text('{"events": [], "calendar": [], "prices": {}, "bad": NaN}')
        out = Path(self.tmp.name) / 'output.json'
        with self.assertRaises(ValueError): score_main(['--input', str(self.path), '--output', str(out)])
        self.assertFalse(out.exists())
        out.write_text('preserve')
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            score_main(['--input', str(self.path), '--output', str(out)])
        self.assertEqual(out.read_text(), 'preserve')


if __name__ == '__main__':
    unittest.main()
