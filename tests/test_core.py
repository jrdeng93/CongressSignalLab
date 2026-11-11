import unittest
from dataclasses import replace
from congress_signal_lab.core import Disclosure, score_components, select, evaluate


def event(**kw):
    data=dict(event_id='e',member='A',ticker='XYZ',transaction_date='2026-01-01',
              available_at='2026-01-02T14:00:00Z',first_seen_at='2026-01-02T20:00:00Z')
    data.update(kw)
    return Disclosure(**data)


class CoreTests(unittest.TestCase):
    def test_requires_timezone(self):
        with self.assertRaises(ValueError): event(first_seen_at='2026-01-02T20:00:00')

    def test_impossible_availability(self):
        with self.assertRaises(ValueError): event(first_seen_at='2026-01-01T20:00:00Z')

    def test_future_policy_not_used(self):
        e=event(policy_match=True,policy_known_at='2026-02-01T00:00:00Z')
        self.assertEqual(score_components(e,[])['policy'],1)

    def test_same_day_and_future_do_not_change_score(self):
        e=event()
        future=event(event_id='later',first_seen_at='2026-02-01T00:00:00Z')
        self.assertEqual(score_components(e,[]),score_components(e,[e,future]))

    def test_rare_ticker_gets_more_idf(self):
        now=event(first_seen_at='2026-01-10T20:00:00Z')
        prior=event(ticker='COMMON')
        self.assertGreater(score_components(now,[prior])['idf'],score_components(replace(now,ticker='COMMON'),[prior])['idf'])

    def test_funds_and_opposite_sides_excluded(self):
        picks,excluded=select([event(),event(event_id='sell',side='sell'),event(event_id='etf',ticker='SPY',asset_type='etf')])
        self.assertEqual(picks,[])
        self.assertEqual(len(excluded),3)

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError): select([event(),event()])

    def test_repeats_same_date_do_not_inflate_tf(self):
        later=event(first_seen_at='2026-01-10T20:00:00Z')
        self.assertEqual(score_components(later,[event()])['tf'],score_components(later,[event(),event(event_id='copy')])['tf'])

    def test_next_session_cost_and_immature(self):
        picks,_=select([event()])
        cal=['2026-01-02','2026-01-05','2026-01-06']
        prices={s:{d:dict(open=100,close=110 if s=='XYZ' else 100) for d in cal} for s in ['XYZ','SPY']}
        row=evaluate(picks,prices,cal,horizon=2)[0]
        self.assertEqual(row['entry'],'2026-01-05')
        self.assertAlmostEqual(row['net_return'],.098)
        self.assertEqual(evaluate(picks,prices,cal,horizon=3)[0]['status'],'immature')
        del prices['XYZ']['2026-01-05']
        self.assertEqual(evaluate(picks,prices,cal,horizon=2)[0]['status'],'missing_prices')

    def test_utc_midnight_maps_to_previous_local_day(self):
        self.assertEqual(event(first_seen_at='2026-01-03T00:10:00Z').day.isoformat(),'2026-01-02')

    def test_invalid_prices_rejected(self):
        with self.assertRaises(ValueError): evaluate([],{'XYZ':{'2026-01-02':dict(open=float('nan'),close=1)}},['2026-01-02'])


if __name__ == '__main__': unittest.main()
