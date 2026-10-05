"""Compare server-side counts ($inlinecount) with the local n_paid for a few states.

  python tools/verify_counts.py [FL LA DE MT WY]

Filter sent to the API: state, yearOfLoss in the window, amountPaidOnBuildingClaim gt 0.
A difference is reported as is: the v3 dataset is refreshed about monthly, so a later
server count may legitimately differ from the snapshot in raw/ (see as_of_date).
Stdlib only. Exit code 1 if any count differs.
"""
import json, os, sys, urllib.parse, urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
doc = json.load(open(os.path.join(ROOT, 'data', 'nfip_paid_claims_by_state.json'), encoding='utf-8'))
endpoint = doc['source']['endpoint']
y0, y1 = doc['method']['window'].split('-')
local = {r['state']: r['n_paid'] for r in doc['records']}
states = sys.argv[1:] or ['FL', 'LA', 'DE', 'MT', 'WY']

diffs = 0
for st in states:
    flt = f"state eq '{st}' and yearOfLoss ge {y0} and yearOfLoss le {y1} and amountPaidOnBuildingClaim gt 0"
    params = {'$filter': flt, '$top': 1, '$select': 'id', '$inlinecount': 'allpages'}
    url = endpoint + '?' + urllib.parse.urlencode(params, quote_via=urllib.parse.quote, safe="$,()'")
    d = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'restoreworth-nfip-dataset/1.0'}), timeout=120).read())
    server = d['metadata']['count']
    ok = server == local[st]
    diffs += not ok
    print(f"{st}: server={server} local={local[st]} {'OK' if ok else 'DIFF'}")
print(f"verify_counts: {len(states)} states, {diffs} difference(s); local snapshot as_of_date={doc['source']['as_of_date']}")
sys.exit(1 if diffs else 0)
