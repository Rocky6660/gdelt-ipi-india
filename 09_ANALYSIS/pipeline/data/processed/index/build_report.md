# build_index report

Built 2026-11-24T00:01:58+00:00 (rung L3); partial: False
Panel: 714 of 936 domains; article share in panel 0.700
Days: 1654 sampled, 9 invalid (core rule 1, global rule 8; global counts available for 1219 days)

## Window series
{
 "rounds_with_window_days": 63,
 "valid_windows": 62,
 "core_size": 104,
 "core2018_size": 99,
 "core_language_counts": {
  "native": 50,
  "hin": 23,
  "tam": 9,
  "mal": 6,
  "tel": 4,
  "mar": 3,
  "pan": 3,
  "kan": 3,
  "guj": 2,
  "ben": 1
 },
 "core2018_language_counts": {
  "native": 47,
  "hin": 21,
  "tam": 9,
  "mal": 7,
  "tel": 4,
  "mar": 3,
  "pan": 3,
  "kan": 3,
  "guj": 2
 },
 "outlet_days_excluded_share": 0.028039202959693643,
 "days_excluded": 20,
 "corr_dedup_vs_nodedup": 0.9716288214828152,
 "mean_share_dedup": 0.011385779578893045,
 "mean_share_nodedup": 0.01076995403881668,
 "corr_window_vs_monthly_definition": 0.9514216201891899
}

## D3 split-half reliability
{
 "7": {
  "N": 62,
  "split_half_r": 0.8990652407125367,
  "spearman_brown": 0.946850293963786
 },
 "14": {
  "N": 62,
  "split_half_r": 0.8874157274032083,
  "spearman_brown": 0.9403500400244676
 }
}
Cross-day duplicate rate (A rows): 0.00275008390274838; inflation rows: 0.0025528499709709367; wire-copy share of inflation rows: 0.035577761384212994

## Monthly series
{
 "core_size": 81,
 "core2018_size": 78,
 "core2018_eng": 30,
 "core2018_ver": 48,
 "grid_days_sampled": 984,
 "grid_days_used": 979,
 "months": 130,
 "months_usable_d23": 129,
 "outlet_days_excluded_share": 0.028814612661784977
}

## N table (D3)
{
 "rounds_with_window": 63,
 "valid_windows": 62,
 "valid_by_mode": {
  "not_stated": 56,
  "telephone": 6
 },
 "valid_by_fs_rule": {
  "exact": 36,
  "month_rule": 26
 }
}

Flags not present every year (D9): []

## Notes
- Outlet weights omega: equal weights over the balanced core (D11 'fixed omega'); pooled ratio is row (ii).
- Window dedup is day-level (R5): numerator and denominator both from day-level distinct URLs; cross-day duplicate rates reported above.
- Row (i) 75th-percentile word cap: not computable (per-article word counts exist only for flagged/ECON articles, not for the denominator). Not reported.
- Row (iv) readership-weighted: no readership data (D2 optional). Not reported.
- Row (v) wire-copy filter: inflation articles whose (day, word count, first 6 V2Tone fields) appear in more than one host are removed from the numerator; denominator unchanged.
- Placebo flag 'sports': no sports theme code occurs among the extracted (ECON/price) article rows; only 'election' is available as a co-occurrence placebo.
- Monthly outlet key = SourceCommonName x source language, no dedup, grid days only (D11).