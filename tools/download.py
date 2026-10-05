"""Re-download the raw inputs into raw/ (never committed).

  python tools/download.py                 # NFIP claims v3, yearOfLoss 2020..2024, + BLS CPI-U
  python tools/download.py 2020 --raw-dir X  # one year into another directory (test)

NFIP: https://www.fema.gov/api/open/v3/NfipClaims, one file per yearOfLoss,
paged with $top/$skip ordered by id; retrieved_utc and the asOfDate values are
recorded in raw/claims_v3_<year>.meta.json.
BLS: CPI-U CUUR0000SA0 (v1 public API, POST), recorded in raw/bls_cpi_u.json + .meta.json.
Stdlib only.
"""
import argparse, datetime, json, os, sys, time, urllib.parse, urllib.request

ENDPOINT = 'https://www.fema.gov/api/open/v3/NfipClaims'
ENTITY = 'NfipClaims'
FIELDS = ['id', 'state', 'yearOfLoss', 'amountPaidOnBuildingClaim', 'asOfDate', 'floodEvent']
PAGE = 50000
SAFE = "$,()'"
UA = {'User-Agent': 'restoreworth-nfip-dataset/1.0'}
BLS_URL = 'https://api.bls.gov/publicAPI/v1/timeseries/data/'
BLS_SERIES = 'CUUR0000SA0'


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def get_json(url, data=None, headers=None):
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
            return json.loads(urllib.request.urlopen(req, timeout=180).read())
        except Exception as e:  # network retry
            print('retry', attempt, repr(e)[:120], flush=True)
            time.sleep(5 * (attempt + 1))
    sys.exit('ABORT: ' + url)


def download_year(year, raw_dir):
    retrieved = now_utc()
    out = os.path.join(raw_dir, f'claims_v3_{year}.jsonl')
    skip, total, as_of = 0, None, set()
    with open(out, 'w', encoding='utf-8') as f:
        while True:
            params = {'$top': PAGE, '$skip': skip, '$select': ','.join(FIELDS), '$orderby': 'id',
                      '$filter': f'yearOfLoss eq {year}', '$inlinecount': 'allpages' if skip == 0 else 'none'}
            url = ENDPOINT + '?' + '&'.join(k + '=' + urllib.parse.quote(str(v), safe=SAFE) for k, v in params.items())
            d = get_json(url)
            if skip == 0:
                total = d['metadata'].get('count')
            rows = d[ENTITY]
            for row in rows:
                as_of.add(row.get('asOfDate'))
                f.write(json.dumps(row, separators=(',', ':')) + '\n')
            skip += len(rows)
            print(year, skip, '/', total, flush=True)
            if len(rows) < PAGE:
                break
            time.sleep(0.5)
    if skip != total:
        sys.exit(f'ABORT {year}: downloaded {skip} rows, server reported {total}')
    meta = {'version': 'v3', 'entity': ENTITY, 'endpoint': ENDPOINT, 'retrieved_utc': retrieved,
            'total_reported': total, 'rows_downloaded': skip, 'as_of_dates': sorted(a for a in as_of if a)}
    json.dump(meta, open(os.path.join(raw_dir, f'claims_v3_{year}.meta.json'), 'w'), indent=1)


def download_bls(raw_dir, start=2020, end=2024):
    retrieved = now_utc()
    body = json.dumps({'seriesid': [BLS_SERIES], 'startyear': str(start), 'endyear': str(end), 'annualaverage': True}).encode()
    d = get_json(BLS_URL, data=body, headers={'Content-Type': 'application/json'})
    if d.get('status') != 'REQUEST_SUCCEEDED':
        sys.exit('BLS: ' + json.dumps(d.get('message')))
    json.dump(d, open(os.path.join(raw_dir, 'bls_cpi_u.json'), 'w'))
    json.dump({'series_id': BLS_SERIES, 'endpoint': BLS_URL, 'retrieved_utc': retrieved},
              open(os.path.join(raw_dir, 'bls_cpi_u.meta.json'), 'w'), indent=1)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('years', nargs='*', type=int, default=[2020, 2021, 2022, 2023, 2024])
    ap.add_argument('--raw-dir', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'raw'))
    ap.add_argument('--no-bls', action='store_true')
    a = ap.parse_args()
    os.makedirs(a.raw_dir, exist_ok=True)
    for y in a.years:
        download_year(y, a.raw_dir)
    if not a.no_bls:
        download_bls(a.raw_dir)
