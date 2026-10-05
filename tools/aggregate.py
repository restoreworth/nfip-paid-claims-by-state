"""Build data/ from raw/ (stdlib only).

Inputs : raw/claims_v3_<year>.jsonl + .meta.json (yearOfLoss 2020..2024), raw/bls_cpi_u.json + .meta.json
Outputs: data/cpi_u_annual.csv, data/nfip_paid_claims_by_state.json (source of truth), data/nfip_paid_claims_by_state.csv
"""
import collections, csv, json, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
RAW, DATA = os.path.join(ROOT, 'raw'), os.path.join(ROOT, 'data')
YEARS = [2020, 2021, 2022, 2023, 2024]
BASE_YEAR = 2024
WINDOW = f'{YEARS[0]}-{YEARS[-1]}'
MIN_N = 100
EVENT_THRESHOLD = 0.25
ENDPOINT = 'https://www.fema.gov/api/open/v3/NfipClaims'
BLS_SERIES = 'CUUR0000SA0'
STATES = sorted('AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY '
                'NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split())
COLUMNS = ['state', 'window', 'as_of_date', 'retrieved_utc', 'n_claims', 'n_paid', 'q1', 'median', 'q3', 'total_paid',
           'median_2024usd', 'top_event', 'top_event_share', 'median_excl_top_event', 'event_dependent', 'status']


def quantile(values, p):
    """Hyndman-Fan type 7 (linear interpolation, numpy default)."""
    s = sorted(values)
    h = (len(s) - 1) * p
    lo = int(h)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (h - lo)


def r2(x):
    return None if x is None else round(x, 2)


def load_cpi():
    d = json.load(open(os.path.join(RAW, 'bls_cpi_u.json'), encoding='utf-8'))
    meta = json.load(open(os.path.join(RAW, 'bls_cpi_u.meta.json'), encoding='utf-8'))
    series = next(s for s in d['Results']['series'] if s['seriesID'] == BLS_SERIES)
    cpi = {int(x['year']): float(x['value']) for x in series['data'] if x['period'] == 'M13'}
    missing = [y for y in YEARS if y not in cpi]
    if missing:
        raise SystemExit(f'CPI annual average missing for {missing}')
    with open(os.path.join(DATA, 'cpi_u_annual.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['year', 'series_id', 'annual_average', 'factor_to_2024usd', 'source', 'retrieved_utc'])
        for y in YEARS:
            w.writerow([y, BLS_SERIES, f'{cpi[y]:.3f}', f'{cpi[BASE_YEAR] / cpi[y]:.6f}', meta['endpoint'], meta['retrieved_utc']])
    return cpi


def load_claims():
    rows, retrieved, as_of = [], [], set()
    for y in YEARS:
        meta = json.load(open(os.path.join(RAW, f'claims_v3_{y}.meta.json'), encoding='utf-8'))
        retrieved.append(meta['retrieved_utc'])
        n = 0
        for line in open(os.path.join(RAW, f'claims_v3_{y}.jsonl'), encoding='utf-8'):
            r = json.loads(line)
            if r['yearOfLoss'] != y:
                raise SystemExit(f'yearOfLoss {r["yearOfLoss"]} in file {y}')
            as_of.add(r.get('asOfDate'))
            rows.append(r)
            n += 1
        if n != meta['rows_downloaded'] or n != meta['total_reported']:
            raise SystemExit(f'{y}: {n} lines vs meta {meta["rows_downloaded"]}/{meta["total_reported"]}')
    if len(as_of) != 1:
        raise SystemExit(f'several asOfDate values: {sorted(map(str, as_of))}')
    # earliest retrieval start, to the second, UTC
    first = min(retrieved)
    return rows, first[:19] + 'Z', as_of.pop()[:10]


def aggregate():
    os.makedirs(DATA, exist_ok=True)
    cpi = load_cpi()
    rows, retrieved_utc, as_of_date = load_claims()
    by_state = collections.defaultdict(list)
    for r in rows:
        if r['state'] in STATES:
            by_state[r['state']].append(r)
    out = []
    for st in STATES:
        rs = by_state.get(st, [])
        paid = [r for r in rs if (r.get('amountPaidOnBuildingClaim') or 0) > 0]
        rec = dict.fromkeys(COLUMNS)
        rec.update(state=st, window=WINDOW, as_of_date=as_of_date, retrieved_utc=retrieved_utc,
                   n_claims=len(rs), n_paid=len(paid))
        if len(paid) < MIN_N:
            rec['status'] = 'insufficient'
            out.append(rec)
            continue
        v = [r['amountPaidOnBuildingClaim'] for r in paid]
        med = quantile(v, .5)
        real = [r['amountPaidOnBuildingClaim'] * cpi[BASE_YEAR] / cpi[r['yearOfLoss']] for r in paid]
        named = collections.Counter(r['floodEvent'] for r in paid if r.get('floodEvent'))
        top, top_n = (max(named.items(), key=lambda kv: (kv[1], kv[0])) if named else (None, 0))
        # no named event in the state: nothing to remove, the rest is every paid claim
        rest = [r['amountPaidOnBuildingClaim'] for r in paid if top is None or r.get('floodEvent') != top]
        med_x = quantile(rest, .5) if len(rest) >= MIN_N else None
        rec.update(q1=r2(quantile(v, .25)), median=r2(med), q3=r2(quantile(v, .75)), total_paid=r2(sum(v)),
                   median_2024usd=r2(quantile(real, .5)), top_event=top,
                   top_event_share=round(top_n / len(paid), 4),
                   median_excl_top_event=r2(med_x),
                   event_dependent=None if med_x is None else abs(med_x - med) / med > EVENT_THRESHOLD,
                   status='ok')
        out.append(rec)
    doc = {
        'title': 'NFIP paid building claims by state, 2020-2024',
        'source': {'publisher': 'Federal Emergency Management Agency (FEMA), OpenFEMA',
                   'dataset': 'NFIP Redacted Claims - v3',
                   'dataset_page': 'https://www.fema.gov/openfema-data-page/nfip-redacted-claims-v3',
                   'terms': 'https://www.fema.gov/about/openfema/terms-conditions',
                   'endpoint': ENDPOINT, 'version': 'v3',
                   'retrieved_utc': retrieved_utc, 'as_of_date': as_of_date},
        'method': {'window': WINDOW, 'year_field': 'yearOfLoss', 'amount_field': 'amountPaidOnBuildingClaim',
                   'paid_filter': 'amountPaidOnBuildingClaim > 0', 'geography': '50 states + DC',
                   'quantiles': 'Hyndman-Fan type 7 (linear interpolation)', 'min_n_paid': MIN_N,
                   'top_event': 'named floodEvent with the most paid claims in the state (null if none; share 0)',
                   'median_excl_top_event': 'median of paid claims not in top_event (claims without floodEvent kept); '
                                            'null if fewer than 100 remain',
                   'event_dependent': 'abs(median_excl_top_event - median) / median > 0.25',
                   'cpi': {'series_id': BLS_SERIES, 'base_year': BASE_YEAR, 'applied_to': 'yearOfLoss',
                           'file': 'data/cpi_u_annual.csv'}},
        'columns': COLUMNS,
        'records': out,
    }
    with open(os.path.join(DATA, 'nfip_paid_claims_by_state.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        f.write('\n')
    with open(os.path.join(DATA, 'nfip_paid_claims_by_state.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(COLUMNS)
        for rec in out:
            w.writerow(['' if rec[c] is None else str(rec[c]).lower() if isinstance(rec[c], bool) else rec[c] for c in COLUMNS])
    ok = [r for r in out if r['status'] == 'ok']
    print('states with stats:', len(ok), '| insufficient:', [r['state'] for r in out if r['status'] == 'insufficient'])
    print('event_dependent:', [r['state'] for r in ok if r['event_dependent']],
          '| median_excl null:', [r['state'] for r in ok if r['median_excl_top_event'] is None])
    fl = next(r for r in out if r['state'] == 'FL')
    print('FL', fl['n_paid'], fl['median'], fl['median_2024usd'], fl['median_excl_top_event'])


if __name__ == '__main__':
    aggregate()
