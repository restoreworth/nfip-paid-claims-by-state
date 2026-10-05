"""Generate README.md from data/nfip_paid_claims_by_state.json (stdlib only).

  python tools/gen_readme.py
"""
import json, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

FEMA_NOTICE = ("This product uses the Federal Emergency Management Agency's OpenFEMA API, but is not endorsed by FEMA. "
               "The Federal Government or FEMA cannot vouch for the data or analyses derived from these data after the "
               "data have been retrieved from the Agency's website(s).")
FEMA_NOT_OFFICIAL = ("This dataset is not intended to be an official federal report, and should not be considered an "
                     "official federal report.")
NOT_OFFICIAL = 'This repository is not an official federal report.'
NOT_REPAIR_COST = 'These are amounts paid by NFIP, not repair cost.'
SITE = 'https://restoreworth.com/'


def money(x):
    return '' if x is None else f'{x:,.0f}'


def render(doc):
    s, m, recs = doc['source'], doc['method'], doc['records']
    ok = [r for r in recs if r['status'] == 'ok']
    low = [r for r in recs if r['status'] == 'insufficient']
    dep = [r['state'] for r in ok if r['event_dependent']]
    cpi = m['cpi']
    L = [
        f"# {doc['title']}",
        '',
        f"Per-state statistics of the building amount paid by the National Flood Insurance Program (NFIP) on claims "
        f"with a year of loss in {m['window']}, computed from FEMA's OpenFEMA dataset "
        f"[{s['dataset']}]({s['dataset_page']}).",
        '',
        f"**{NOT_REPAIR_COST}** {NOT_OFFICIAL}",
        '',
        '## Source and citation',
        '',
        f"- API endpoint (version {s['version']}): {s['endpoint']}",
        f"- Retrieved (UTC): {s['retrieved_utc']}",
        f"- Dataset `asOfDate`: {s['as_of_date']}",
        f"- OpenFEMA terms and conditions: {s['terms']}",
        '',
        f"> {FEMA_NOTICE}",
        '',
        f"FEMA states about the source dataset: \"{FEMA_NOT_OFFICIAL}\"",
        '',
        '## Files',
        '',
        '- `data/nfip_paid_claims_by_state.json`: source of truth (metadata + one record per state).',
        '- `data/nfip_paid_claims_by_state.csv`: same records, same columns.',
        '- `data/cpi_u_annual.csv`: CPI-U annual averages and the factors used for the 2024-dollar column.',
        '- `tools/`: `download.py` (raw re-download), `aggregate.py` (builds `data/`), `crosscheck.mjs` '
        '(independent recomputation in Node), `verify_counts.py` (server-side counts), `refresh.py` (monthly check against the newest `asOfDate`; writes `data/` only with `--apply`), `gen_readme.py` (this file).',
        '',
        '## Method',
        '',
        f"- Window: `{m['year_field']}` {m['window']}; geography: {m['geography']}.",
        f"- Paid claims: `{m['paid_filter']}`; amount: `{m['amount_field']}`. `n_claims` counts all claim records of the "
        f"state in the window, `n_paid` the paid ones.",
        f"- Quartiles: {m['quantiles']} on `n_paid` amounts; values rounded to the cent.",
        f"- States with `n_paid` < {m['min_n_paid']}: statistics left empty, `status` = `insufficient`.",
        f"- `top_event`: {m['top_event']}. `median_excl_top_event`: {m['median_excl_top_event']}.",
        f"- `event_dependent`: {m['event_dependent']} (empty when `median_excl_top_event` is empty).",
        f"- `median_2024usd`: each amount multiplied by CPI-U({cpi['base_year']}) / CPI-U(year of loss), BLS series "
        f"`{cpi['series_id']}` (all items, U.S. city average, not seasonally adjusted, annual average), see "
        f"`{cpi['file']}` for values and retrieval time. The dataset gives no payment date: the factor is applied to "
        f"`{cpi['applied_to']}`, an approximation. The CPI is not a construction cost index: this column is a monetary "
        f"adjustment, not today's cost of repair.",
        '',
        f"## Results ({len(ok)} states with statistics, {len(low)} with insufficient data)",
        '',
        'Nominal US dollars unless stated. Event-dependent states: ' + ', '.join(dep) + '.',
        '',
        '| State | n paid | Q1 | Median | Q3 | Median (2024 $) | Top event (share) | Median excl. top event | Event-dependent |',
        '|---|---:|---:|---:|---:|---:|---|---:|---|',
    ]
    for r in sorted(recs, key=lambda r: r['state']):
        if r['status'] != 'ok':
            L.append(f"| {r['state']} | {r['n_paid']} | | | | | insufficient data (n < {m['min_n_paid']}) | | |")
            continue
        top = f"{r['top_event']} ({r['top_event_share']:.0%})" if r['top_event'] else '(no named event)'
        ev = '' if r['event_dependent'] is None else ('yes' if r['event_dependent'] else 'no')
        L.append(f"| {r['state']} | {r['n_paid']} | {money(r['q1'])} | {money(r['median'])} | {money(r['q3'])} | "
                 f"{money(r['median_2024usd'])} | {top} | {money(r['median_excl_top_event'])} | {ev} |")
    L += [
        '',
        '## Limitations',
        '',
        f"- {NOT_REPAIR_COST} They are what NFIP paid the policyholder on the building, after deductible and capped by "
        "the coverage purchased; uninsured, undeclared or non-covered damage is not included.",
        '- Not representative of all homes or all floods: only NFIP-insured properties with a claim that was paid.',
        '- Amounts are nominal dollars of different years and of different disasters; one event can dominate a '
        'state (see `event_dependent`).',
        '- No single-family series, no city, ZIP code or water-depth breakdown.',
        '- No promise of cost, eligibility or claim amount for any individual.',
        '- No endorsement by FEMA or DHS is stated or implied; no FEMA or DHS logo or seal is used.',
        '',
        '## License',
        '',
        'Aggregated data (`data/`): CC BY 4.0, attribution "RestoreWorth Team". Code (`tools/`, `tests/`): MIT. '
        'See `LICENSE` and `DATA_NOTICE.md`. Raw OpenFEMA records are not redistributed here.',
        '',
        f"Maintained by the RestoreWorth Team: {SITE}",
        '',
        '<!-- generated by tools/gen_readme.py from data/nfip_paid_claims_by_state.json; do not edit by hand -->',
        '',
    ]
    return '\n'.join(L)


def main():
    doc = json.load(open(os.path.join(ROOT, 'data', 'nfip_paid_claims_by_state.json'), encoding='utf-8'))
    with open(os.path.join(ROOT, 'README.md'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(render(doc))


if __name__ == '__main__':
    main()
