# Data notice

The files in `data/` are aggregates computed from FEMA's OpenFEMA API, endpoint
https://www.fema.gov/api/open/v3/NfipClaims (version v3). The retrieval date and time (UTC) are recorded in
`data/nfip_paid_claims_by_state.json` (`source.retrieved_utc`) and in every record.

> This product uses the Federal Emergency Management Agency’s OpenFEMA API, but is not endorsed by FEMA. The Federal Government or FEMA cannot vouch for the data or analyses derived from these data after the data have been retrieved from the Agency's website(s).

This repository is not an official federal report. No FEMA or DHS logo or seal is used.

## Use conditions carried over from the OpenFEMA terms

Terms: https://www.fema.gov/about/openfema/terms-conditions

- Only state-level aggregates are published; no individual claim record, ZIP code or city figure.
- The data are used for statistical research and reporting only, never to make determinations that might affect
  an individual's rights or eligibility for benefits. No attempt is made to reidentify anyone.
- Withdrawal on request: FEMA may rescind the use of the data if it believes that it does not serve the public
  interest. If FEMA requests it, the RestoreWorth Team will stop using the data, remove the aggregates from this
  repository and destroy any copy it holds.

## What the figures are not

These are amounts paid by NFIP, not repair cost. They are nominal dollars (except the CPI-adjusted
`median_2024usd` column), they cover only NFIP-insured properties with a paid claim, and they are not
representative of all homes or all floods.
