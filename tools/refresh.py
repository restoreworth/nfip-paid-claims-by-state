"""Check OpenFEMA for a newer NfipClaims v3 refresh and build a candidate dataset (stdlib only).

  python tools/refresh.py            # check; if newer, download + aggregate into a temporary folder, report changes
  python tools/refresh.py --force    # build the candidate even if asOfDate is unchanged
  python tools/refresh.py --apply    # same, then copy the candidate files over data/

The dataset record is read from the OpenFemaDataSets API (deprecation, lastDataSetRefresh); that record has no
asOfDate field, so asOfDate is read from the NfipClaims v3 endpoint itself (latest value). data/ is never written
without --apply. Nothing is committed, tagged or published: after --apply, regenerate the README
(tools/gen_readme.py), run the tests and review the diff by hand.
"""
import argparse, json, os, shutil, sys, tempfile, urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aggregate, download  # noqa: E402

DATASETS = 'https://www.fema.gov/api/open/v1/OpenFemaDataSets'
THRESHOLD = 0.05
WATCHED = ('n_paid', 'median')
FILES = ('nfip_paid_claims_by_state.json', 'nfip_paid_claims_by_state.csv', 'cpi_u_annual.csv')


def remote_as_of():
    """(asOfDate YYYY-MM-DD, OpenFemaDataSets record) for NfipClaims v3."""
    q = urllib.parse.quote("name eq 'NfipClaims' and version eq 3", safe=download.SAFE)
    rec = download.get_json(f'{DATASETS}?$filter={q}')['OpenFemaDataSets']
    if len(rec) != 1:
        raise SystemExit(f'OpenFemaDataSets: {len(rec)} records for NfipClaims v3')
    rec = rec[0]
    if rec.get('depDate'):
        raise SystemExit(f'NfipClaims v3 deprecated on {rec["depDate"]}: {rec.get("depApiMessage")}')
    q = urllib.parse.quote('asOfDate desc', safe=download.SAFE)
    row = download.get_json(f'{download.ENDPOINT}?$select=asOfDate&$top=1&$orderby={q}')[download.ENTITY][0]
    return row['asOfDate'][:10], rec


def rel_change(old, new):
    if old == new:
        return 0.0
    if old is None or new is None or old == 0:
        return float('inf')
    return abs(new - old) / abs(old)


def changes(old_doc, new_doc, threshold=THRESHOLD):
    """[(state, field, old, new, relative change)] for every watched field that moves by more than threshold,
    plus every status change and every state present on one side only."""
    old = {r['state']: r for r in old_doc['records']}
    new = {r['state']: r for r in new_doc['records']}
    out = []
    for st in sorted(set(old) | set(new)):
        o, n = old.get(st), new.get(st)
        if o is None or n is None:
            out.append((st, 'state', o and st, n and st, float('inf')))
            continue
        if o['status'] != n['status']:
            out.append((st, 'status', o['status'], n['status'], float('inf')))
        for f in WATCHED:
            c = rel_change(o[f], n[f])
            if c > threshold:
                out.append((st, f, o[f], n[f], c))
    return out


def build_candidate(work):
    raw, cand = os.path.join(work, 'raw'), os.path.join(work, 'candidate')
    os.makedirs(raw, exist_ok=True)
    for y in aggregate.YEARS:
        download.download_year(y, raw)
    download.download_bls(raw, aggregate.YEARS[0], aggregate.YEARS[-1])
    aggregate.RAW, aggregate.DATA = raw, cand
    aggregate.aggregate()
    return cand


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='copy the candidate over data/ (no commit, no publication)')
    ap.add_argument('--force', action='store_true', help='build the candidate even if asOfDate is unchanged')
    ap.add_argument('--work-dir', help='folder for raw files and candidate (default: new temporary folder)')
    a = ap.parse_args(argv)
    data = os.path.join(aggregate.ROOT, 'data')
    current = json.load(open(os.path.join(data, FILES[0]), encoding='utf-8'))
    local = current['source']['as_of_date']
    remote, rec = remote_as_of()
    print(f'asOfDate local {local} | remote {remote} | OpenFemaDataSets lastDataSetRefresh {rec.get("lastDataSetRefresh")}')
    if remote <= local and not a.force:
        print('up to date: nothing downloaded')
        return 0
    work = a.work_dir or tempfile.mkdtemp(prefix='nfip-refresh-')
    cand = build_candidate(work)
    new = json.load(open(os.path.join(cand, FILES[0]), encoding='utf-8'))
    moved = changes(current, new)
    print(f'candidate: {cand}')
    print(f'{len(moved)} change(s) above {THRESHOLD:.0%} on {", ".join(WATCHED)} or status:')
    for st, f, o, n, c in moved:
        print(f'  {st} {f}: {o} -> {n} ({"new/removed" if c == float("inf") else f"{c:.1%}"})')
    json.dump([dict(zip(('state', 'field', 'old', 'new', 'rel_change'), m[:4] + (None if m[4] == float('inf') else round(m[4], 4),)))
               for m in moved], open(os.path.join(work, 'changes.json'), 'w', encoding='utf-8'), indent=1)
    if not a.apply:
        print('data/ unchanged (rerun with --apply to copy the candidate)')
        return 0
    for name in FILES:
        shutil.copyfile(os.path.join(cand, name), os.path.join(data, name))
    print('data/ replaced by the candidate. Next: python tools/gen_readme.py, run the tests, review git diff. '
          'Nothing was committed or published.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
