# NFIP paid building claims by state, 2020-2024

Per-state statistics of the building amount paid by the National Flood Insurance Program (NFIP) on claims with a year of loss in 2020-2024, computed from FEMA's OpenFEMA dataset [NFIP Redacted Claims - v3](https://www.fema.gov/openfema-data-page/nfip-redacted-claims-v3).

**These are amounts paid by NFIP, not repair cost.** This repository is not an official federal report.

## Source and citation

- API endpoint (version v3): https://www.fema.gov/api/open/v3/NfipClaims
- Retrieved (UTC): 2026-10-03T09:21:23Z
- Dataset `asOfDate`: 2026-09-08
- OpenFEMA terms and conditions: https://www.fema.gov/about/openfema/terms-conditions

> This product uses the Federal Emergency Management Agency's OpenFEMA API, but is not endorsed by FEMA. The Federal Government or FEMA cannot vouch for the data or analyses derived from these data after the data have been retrieved from the Agency's website(s).

FEMA states about the source dataset: "This dataset is not intended to be an official federal report, and should not be considered an official federal report."

## Files

- `data/nfip_paid_claims_by_state.json`: source of truth (metadata + one record per state).
- `data/nfip_paid_claims_by_state.csv`: same records, same columns.
- `data/cpi_u_annual.csv`: CPI-U annual averages and the factors used for the 2024-dollar column.
- `tools/`: `download.py` (raw re-download), `aggregate.py` (builds `data/`), `crosscheck.mjs` (independent recomputation in Node), `verify_counts.py` (server-side counts), `refresh.py` (monthly check against the newest `asOfDate`; writes `data/` only with `--apply`), `gen_readme.py` (this file).

## Method

- Window: `yearOfLoss` 2020-2024; geography: 50 states + DC.
- Paid claims: `amountPaidOnBuildingClaim > 0`; amount: `amountPaidOnBuildingClaim`. `n_claims` counts all claim records of the state in the window, `n_paid` the paid ones.
- Quartiles: Hyndman-Fan type 7 (linear interpolation) on `n_paid` amounts; values rounded to the cent.
- States with `n_paid` < 100: statistics left empty, `status` = `insufficient`.
- `top_event`: named floodEvent with the most paid claims in the state (null if none; share 0). `median_excl_top_event`: median of paid claims not in top_event (claims without floodEvent kept); null if fewer than 100 remain.
- `event_dependent`: abs(median_excl_top_event - median) / median > 0.25 (empty when `median_excl_top_event` is empty).
- `median_2024usd`: each amount multiplied by CPI-U(2024) / CPI-U(year of loss), BLS series `CUUR0000SA0` (all items, U.S. city average, not seasonally adjusted, annual average), see `data/cpi_u_annual.csv` for values and retrieval time. The dataset gives no payment date: the factor is applied to `yearOfLoss`, an approximation. The CPI is not a construction cost index: this column is a monetary adjustment, not today's cost of repair.

## Results (41 states with statistics, 10 with insufficient data)

Nominal US dollars unless stated. Event-dependent states: FL, IA, MS, NC, NJ, VT.

| State | n paid | Q1 | Median | Q3 | Median (2024 $) | Top event (share) | Median excl. top event | Event-dependent |
|---|---:|---:|---:|---:|---:|---|---:|---|
| AK | 92 | | | | | insufficient data (n < 100) | | |
| AL | 3530 | 4,445 | 14,260 | 50,696 | 16,961 | Hurricane Sally (71%) | 16,280 | no |
| AR | 408 | 10,826 | 27,435 | 56,106 | 29,655 | Hurricane Beryl (3%) | 26,534 | no |
| AZ | 216 | 5,595 | 17,079 | 44,920 | 18,711 | Arizona Burn Scar Flash Flooding (0%) | 16,949 | no |
| CA | 2077 | 8,884 | 25,630 | 70,956 | 27,172 | California Atmospheric River (64%) | 25,016 | no |
| CO | 118 | 3,355 | 6,560 | 15,512 | 6,849 | Colorado Burn Scar Flash Flooding (2%) | 6,389 | no |
| CT | 1077 | 6,371 | 14,655 | 32,357 | 16,576 | Hurricane Ida (55%) | 13,425 | no |
| DC | 65 | | | | | insufficient data (n < 100) | | |
| DE | 233 | 2,552 | 6,287 | 17,573 | 6,843 | Hurricane Ida (34%) | 5,637 | no |
| FL | 120351 | 17,647 | 71,205 | 129,121 | 73,569 | Hurricane Helene (40%) | 53,187 | yes |
| GA | 2063 | 6,392 | 16,885 | 41,289 | 18,494 | Hurricane Helene (25%) | 14,613 | no |
| HI | 267 | 8,436 | 25,188 | 71,819 | 28,064 | (no named event) | 25,188 | no |
| IA | 340 | 7,991 | 18,219 | 50,000 | 18,732 | June Midwest Flooding (43%) | 11,795 | yes |
| ID | 30 | | | | | insufficient data (n < 100) | | |
| IL | 1023 | 3,534 | 8,522 | 19,542 | 9,594 | Late July Flooding (6%) | 8,397 | no |
| IN | 184 | 4,283 | 11,617 | 26,901 | 13,224 | Late July Flooding (1%) | 11,676 | no |
| KS | 94 | | | | | insufficient data (n < 100) | | |
| KY | 1472 | 7,347 | 17,532 | 44,090 | 19,524 | Late July Flooding (28%) | 13,787 | no |
| LA | 20010 | 9,392 | 36,262 | 77,235 | 41,558 | Hurricane Ida (50%) | 31,982 | no |
| MA | 722 | 4,730 | 11,691 | 28,734 | 12,400 | December Nor'easter (8%) | 11,632 | no |
| MD | 1171 | 4,339 | 10,853 | 25,099 | 12,171 | Hurricane Isaias (7%) | 10,833 | no |
| ME | 854 | 8,643 | 24,520 | 54,325 | 24,931 | December Nor'easter (17%) | 23,223 | no |
| MI | 1196 | 5,434 | 14,122 | 44,022 | 15,871 | (no named event) | 14,122 | no |
| MN | 249 | 6,293 | 14,188 | 36,141 | 14,970 | June Midwest Flooding (41%) | 11,446 | no |
| MO | 1355 | 7,430 | 18,861 | 52,370 | 20,447 | Late July Flooding (42%) | 14,648 | no |
| MS | 1992 | 3,286 | 9,704 | 31,869 | 11,388 | Hurricane Zeta (32%) | 15,249 | yes |
| MT | 107 | 9,196 | 26,845 | 92,206 | 29,887 | Yellowstone Flooding (83%) |  |  |
| NC | 4971 | 5,637 | 17,282 | 59,887 | 18,623 | Hurricane Helene (34%) | 10,400 | yes |
| ND | 57 | | | | | insufficient data (n < 100) | | |
| NE | 67 | | | | | insufficient data (n < 100) | | |
| NH | 387 | 8,786 | 19,043 | 43,872 | 19,171 | December Nor'easter (13%) | 20,152 | no |
| NJ | 8230 | 8,270 | 18,797 | 43,884 | 21,271 | Hurricane Ida (75%) | 10,524 | yes |
| NM | 245 | 10,347 | 28,189 | 91,825 | 31,196 | (no named event) | 28,189 | no |
| NV | 54 | | | | | insufficient data (n < 100) | | |
| NY | 6912 | 7,339 | 16,686 | 37,962 | 18,240 | Hurricane Ida (41%) | 13,775 | no |
| OH | 871 | 4,660 | 10,988 | 27,046 | 12,456 | Tropical Storm Fred (0%) | 10,962 | no |
| OK | 240 | 12,944 | 28,423 | 62,038 | 32,240 | (no named event) | 28,423 | no |
| OR | 104 | 5,364 | 14,163 | 29,780 | 16,420 | (no named event) | 14,163 | no |
| PA | 3717 | 7,401 | 17,580 | 42,017 | 20,121 | Hurricane Ida (42%) | 15,007 | no |
| RI | 298 | 5,491 | 13,874 | 40,739 | 14,304 | December Nor'easter (19%) | 12,676 | no |
| SC | 2934 | 5,475 | 15,672 | 39,352 | 16,859 | Hurricane Ian (32%) | 14,323 | no |
| SD | 79 | | | | | insufficient data (n < 100) | | |
| TN | 1685 | 9,251 | 21,706 | 51,844 | 24,241 | Hurricane Helene (11%) | 20,063 | no |
| TX | 6483 | 6,432 | 20,271 | 49,361 | 21,939 | Hurricane Beryl (23%) | 21,016 | no |
| UT | 64 | | | | | insufficient data (n < 100) | | |
| VA | 914 | 3,982 | 9,331 | 21,583 | 10,456 | Hurricane Helene (12%) | 8,369 | no |
| VT | 773 | 10,919 | 26,372 | 65,000 | 27,150 | Vermont/New York Flooding (70%) | 15,675 | yes |
| WA | 1060 | 10,330 | 22,881 | 59,699 | 25,519 | (no named event) | 22,881 | no |
| WI | 225 | 3,623 | 9,887 | 26,473 | 10,872 | (no named event) | 9,887 | no |
| WV | 602 | 5,790 | 12,579 | 28,549 | 13,802 | West Virginia Flooding (6%) | 12,443 | no |
| WY | 10 | | | | | insufficient data (n < 100) | | |

## Limitations

- These are amounts paid by NFIP, not repair cost. They are what NFIP paid the policyholder on the building, after deductible and capped by the coverage purchased; uninsured, undeclared or non-covered damage is not included.
- Not representative of all homes or all floods: only NFIP-insured properties with a claim that was paid.
- Amounts are nominal dollars of different years and of different disasters; one event can dominate a state (see `event_dependent`).
- No single-family series, no city, ZIP code or water-depth breakdown.
- No promise of cost, eligibility or claim amount for any individual.
- No endorsement by FEMA or DHS is stated or implied; no FEMA or DHS logo or seal is used.

## License

Aggregated data (`data/`): CC BY 4.0, attribution "RestoreWorth Team". Code (`tools/`, `tests/`): MIT. See `LICENSE` and `DATA_NOTICE.md`. Raw OpenFEMA records are not redistributed here.

Maintained by the RestoreWorth Team: https://restoreworth.com/

<!-- generated by tools/gen_readme.py from data/nfip_paid_claims_by_state.json; do not edit by hand -->
