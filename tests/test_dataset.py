import csv, json, os, re, subprocess, sys, unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import gen_readme  # noqa: E402


def read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()


DOC = json.loads(read('data/nfip_paid_claims_by_state.json'))
RECS = {r['state']: r for r in DOC['records']}
STATS = ['q1', 'median', 'q3', 'total_paid', 'median_2024usd', 'top_event', 'top_event_share',
         'median_excl_top_event', 'event_dependent']

FEMA_NOTICE = ("This product uses the Federal Emergency Management Agency’s OpenFEMA API, but is not endorsed by FEMA. "
               "The Federal Government or FEMA cannot vouch for the data or analyses derived from these data after the "
               "data have been retrieved from the Agency's website(s).")
ENDPOINT = 'https://www.fema.gov/api/open/v3/NfipClaims'


class Invariants(unittest.TestCase):
    def test_states(self):
        fifty_dc = set('AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ '
                       'NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split())
        self.assertEqual(set(RECS), fifty_dc)
        self.assertEqual(len(DOC['records']), 51)

    def test_acceptance_values(self):
        fl = RECS['FL']
        self.assertEqual(fl['n_paid'], 120351)
        self.assertEqual(round(fl['median']), 71205)
        self.assertEqual(sum(r['status'] == 'ok' for r in RECS.values()), 41)
        self.assertEqual({s for s, r in RECS.items() if r['status'] == 'insufficient'},
                         set('KS AK SD NE DC UT ND NV ID WY'.split()))
        self.assertEqual({s for s, r in RECS.items() if r['event_dependent']}, set('FL NJ NC MS VT IA'.split()))

    def test_record_rules(self):
        common = {(r['window'], r['as_of_date'], r['retrieved_utc']) for r in RECS.values()}
        self.assertEqual(len(common), 1)
        self.assertEqual(DOC['columns'], list(DOC['records'][0]))
        for s, r in RECS.items():
            self.assertLessEqual(r['n_paid'], r['n_claims'], s)
            if r['n_paid'] < 100:
                self.assertEqual(r['status'], 'insufficient', s)
                self.assertTrue(all(r[k] is None for k in STATS), s)
                continue
            self.assertEqual(r['status'], 'ok', s)
            self.assertTrue(0 < r['q1'] <= r['median'] <= r['q3'], s)
            self.assertGreaterEqual(r['median_2024usd'], r['median'], s)  # all CPI factors >= 1
            self.assertTrue(0 <= r['top_event_share'] <= 1, s)
            if r['top_event'] is None:
                self.assertEqual(r['top_event_share'], 0, s)
            if r['median_excl_top_event'] is None:
                self.assertIsNone(r['event_dependent'], s)
            else:
                dep = abs(r['median_excl_top_event'] - r['median']) / r['median'] > 0.25
                self.assertEqual(r['event_dependent'], dep, s)

    def test_csv_matches_json(self):
        rows = list(csv.DictReader(open(os.path.join(ROOT, 'data/nfip_paid_claims_by_state.csv'), encoding='utf-8')))
        self.assertEqual(len(rows), 51)
        for row in rows:
            rec = RECS[row['state']]
            for k, v in row.items():
                want = '' if rec[k] is None else str(rec[k]).lower() if isinstance(rec[k], bool) else str(rec[k])
                self.assertEqual(v, want, (row['state'], k))

    def test_cpi_file(self):
        rows = list(csv.DictReader(open(os.path.join(ROOT, 'data/cpi_u_annual.csv'), encoding='utf-8')))
        self.assertEqual([int(r['year']) for r in rows], [2020, 2021, 2022, 2023, 2024])
        self.assertTrue(all(r['series_id'] == 'CUUR0000SA0' and r['retrieved_utc'] for r in rows))
        self.assertEqual(rows[-1]['factor_to_2024usd'], '1.000000')


class Texts(unittest.TestCase):
    def test_readme_is_generated(self):
        self.assertEqual(read('README.md'), gen_readme.render(DOC))

    def test_d4_phrases(self):
        for f in ('README.md', 'DATA_NOTICE.md'):
            t = read(f)
            self.assertIn(FEMA_NOTICE, t, f)
            self.assertIn('not an official federal report', t, f)
            self.assertIn(ENDPOINT, t, f)
            self.assertIn('amounts paid by NFIP, not repair cost', t, f)
        readme = read('README.md')
        self.assertIn('version v3', readme)
        self.assertIn(DOC['source']['retrieved_utc'], readme)
        self.assertNotRegex(readme, r'!\[|<img')  # no logo or image

    def test_license(self):
        t = read('LICENSE')
        self.assertIn('CC BY 4.0', t)
        self.assertIn('RestoreWorth Team', t)
        self.assertIn('MIT License', t)


class Repository(unittest.TestCase):
    def tracked(self):
        out = subprocess.run(['git', 'ls-files'], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        return [p for p in out.splitlines() if p]

    def test_raw_not_tracked(self):
        self.assertFalse([p for p in self.tracked() if p.startswith('raw/')])
        ok = subprocess.run(['git', 'check-ignore', '-q', 'raw/claims_v3_2024.jsonl'], cwd=ROOT).returncode == 0
        self.assertTrue(ok, 'raw/ must be ignored')

    def test_no_private_publisher_and_single_site_link(self):
        banned = re.compile(r'homeguide|\bangi\b|homeadvisor|homewyse|thumbtack|\bfixr\b|costhelper', re.I)
        site = re.compile(r'https?://(?:www\.)?restoreworth\.com[^\s)>"\'`]*', re.I)
        me = os.path.relpath(__file__, ROOT).replace(os.sep, '/')
        for p in self.tracked() or ['README.md', 'DATA_NOTICE.md', 'LICENSE']:
            if p == me:
                continue
            t = read(p)
            self.assertIsNone(banned.search(t), p)
            self.assertTrue(all(u == 'https://restoreworth.com/' for u in site.findall(t)), p)


if __name__ == '__main__':
    unittest.main()
