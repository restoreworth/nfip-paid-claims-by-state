import copy, json, os, sys, unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import refresh  # noqa: E402

with open(os.path.join(ROOT, 'data', 'nfip_paid_claims_by_state.json'), encoding='utf-8') as f:
    DOC = json.load(f)


def mutated(state, field, factor=None, value=None):
    d = copy.deepcopy(DOC)
    r = next(r for r in d['records'] if r['state'] == state)
    r[field] = value if factor is None else r[field] * factor
    return d


class Changes(unittest.TestCase):
    def test_identical_is_silent(self):
        self.assertEqual(refresh.changes(DOC, copy.deepcopy(DOC)), [])

    def test_altered_median_is_reported(self):
        moved = refresh.changes(DOC, mutated('FL', 'median', 1.06))
        self.assertEqual([(m[0], m[1]) for m in moved], [('FL', 'median')])

    def test_altered_n_paid_is_reported(self):
        tx = next(r['n_paid'] for r in DOC['records'] if r['state'] == 'TX')
        moved = refresh.changes(DOC, mutated('TX', 'n_paid', value=int(tx * 0.9)))
        self.assertEqual([(m[0], m[1]) for m in moved], [('TX', 'n_paid')])

    def test_small_change_is_not_reported(self):
        self.assertEqual(refresh.changes(DOC, mutated('FL', 'median', 1.04)), [])

    def test_status_change_is_reported(self):
        d = copy.deepcopy(DOC)
        r = next(r for r in d['records'] if r['state'] == 'AK')
        r.update(status='ok', n_paid=150, median=10000.0)
        self.assertIn(('AK', 'status'), [(m[0], m[1]) for m in refresh.changes(DOC, d)])
        self.assertIn(('AK', 'median'), [(m[0], m[1]) for m in refresh.changes(DOC, d)])


if __name__ == '__main__':
    unittest.main()
