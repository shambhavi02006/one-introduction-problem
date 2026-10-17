### A. Official `evaluate.py`, public seeds 101-103, all six variants (18 episodes per policy)

| policy | eligible | invalid | primary score | coverage | mutual acc/100 | ask cost | inference s/episode |
|---|---|---|---|---|---|---|---|
| ours | True | 0/18 | 0.306 | 0.375 | 5.92 | 218 | 8.2 |
| greedy | True | 0/18 | 0.389 | 0.372 | 5.50 | 207 | 11.2 |
| random | True | 0/18 | 0.389 | 0.376 | 6.08 | 207 | 10.5 |
| no_asks | True | 0/18 | 0.139 | 0.143 | 1.75 | 0 | 11.5 |

Per-family primary score (public seeds):

| policy | development | sparse | cold_start | delayed | shift | drift |
|---|---|---|---|---|---|---|
| ours | 0.33 | 0.17 | 0.17 | 0.50 | 0.33 | 0.33 |
| greedy | 0.50 | 0.17 | 0.17 | 0.50 | 0.50 | 0.50 |
| random | 0.67 | 0.17 | 0.00 | 0.33 | 0.50 | 0.67 |
| no_asks | 0.17 | 0.00 | 0.00 | 0.33 | 0.17 | 0.17 |

### B. Held-out batch, seeds 3020-3119 (100 per family, 600 episodes per policy; never used for tuning)

Primary score = mean over seeds within each family, then mean of the six families (organiser rule). `expected MSMI` is an analysis-only diagnostic from the simulator latent values (not available to a policy).

| policy | invalid | **MSMI/100** | expected MSMI/100 (diag.) | coverage | mutual acc/100 | assignments | edge utilisation | ask cost |
|---|---|---|---|---|---|---|---|---|
| ours | 0 | **0.376** | 0.377 | 0.335 | 5.32 | 74.9 | 0.833 | 221 |
| greedy | 0 | **0.366** | 0.363 | 0.334 | 5.08 | 74.3 | 0.828 | 199 |
| random | 0 | **0.370** | 0.361 | 0.335 | 5.02 | 74.5 | 0.831 | 199 |
| no_asks | 0 | **0.100** | 0.103 | 0.121 | 1.50 | 21.3 | 0.231 | 0 |
| abl_list_order_asks | 0 | **0.383** | 0.370 | 0.336 | 5.09 | 74.4 | 0.829 | 199 |
| abl_greedy_allocation | 0 | **0.383** | 0.382 | 0.335 | 5.29 | 74.8 | 0.832 | 222 |
| ours_kit_prior | 0 | **0.384** | 0.382 | 0.336 | 5.32 | 75.1 | 0.834 | 222 |
| ours_neutral_prior | 0 | **0.370** | 0.373 | 0.333 | 5.17 | 74.5 | 0.823 | 211 |

Per-family MSMI/100 (diagnostic expected MSMI in parentheses):

| policy | development | sparse | cold_start | delayed | shift | drift |
|---|---|---|---|---|---|---|
| ours | 0.51 (0.46) | 0.09 (0.11) | 0.34 (0.39) | 0.41 (0.44) | 0.42 (0.41) | 0.48 (0.44) |
| greedy | 0.47 (0.45) | 0.10 (0.11) | 0.39 (0.37) | 0.38 (0.43) | 0.38 (0.39) | 0.47 (0.42) |
| random | 0.46 (0.44) | 0.10 (0.11) | 0.36 (0.37) | 0.42 (0.42) | 0.43 (0.39) | 0.45 (0.42) |
| no_asks | 0.15 (0.14) | 0.01 (0.03) | 0.07 (0.05) | 0.10 (0.14) | 0.14 (0.13) | 0.14 (0.14) |
| abl_list_order_asks | 0.53 (0.45) | 0.10 (0.11) | 0.36 (0.38) | 0.38 (0.44) | 0.41 (0.40) | 0.51 (0.43) |
| abl_greedy_allocation | 0.52 (0.47) | 0.10 (0.11) | 0.38 (0.39) | 0.36 (0.44) | 0.45 (0.42) | 0.49 (0.45) |
| ours_kit_prior | 0.49 (0.47) | 0.10 (0.12) | 0.34 (0.39) | 0.44 (0.45) | 0.45 (0.41) | 0.48 (0.45) |
| ours_neutral_prior | 0.51 (0.46) | 0.09 (0.11) | 0.33 (0.39) | 0.33 (0.44) | 0.47 (0.41) | 0.49 (0.44) |

Paired differences, ours minus comparator (same 600 world seeds; 95% bootstrap CI resampling seeds within family):

| comparator | MSMI/100 diff [95% CI] | expected-MSMI diff [95% CI] | assignments diff | mutual acc/100 diff | coverage diff |
|---|---|---|---|---|---|
| greedy | +0.010 [-0.031, +0.052] | +0.014 [+0.009, +0.018] | +0.592 | +0.236 | +0.002 |
| random | +0.006 [-0.037, +0.048] | +0.016 [+0.012, +0.020] | +0.442 | +0.296 | +0.001 |
| no_asks | +0.276 [+0.241, +0.310] | +0.273 [+0.267, +0.280] | +53.628 | +3.823 | +0.215 |
| abl_list_order_asks | -0.007 [-0.048, +0.036] | +0.007 [+0.003, +0.011] | +0.537 | +0.229 | -0.001 |
| abl_greedy_allocation | -0.007 [-0.039, +0.027] | -0.005 [-0.008, -0.002] | +0.113 | +0.033 | +0.001 |
| ours_kit_prior | -0.008 [-0.036, +0.019] | -0.005 [-0.008, -0.002] | -0.225 | -0.006 | -0.000 |
| ours_neutral_prior | +0.006 [-0.030, +0.040] | +0.004 [+0.000, +0.007] | +0.470 | +0.152 | +0.003 |

Who is not served (ours, mean members per 200-member episode):

| family | served | unserved | declined a hard field | no feasible partner exists | policy/capacity |
|---|---|---|---|---|---|
| development | 76.2 | 123.8 | 65.6 | 56.8 | 1.5 |
| sparse | 33.4 | 166.6 | 66.3 | 99.9 | 0.3 |
| cold_start | 64.7 | 135.3 | 81.1 | 52.9 | 1.3 |
| delayed | 76.0 | 124.0 | 65.6 | 56.8 | 1.6 |
| shift | 76.2 | 123.8 | 65.6 | 56.8 | 1.5 |
| drift | 76.2 | 123.8 | 65.6 | 56.8 | 1.4 |

First-introduction wait, days from arrival (pooled over served members):

| family | ours median / p90 | greedy median / p90 |
|---|---|---|
| development | 2 / 15 | 4 / 17 |
| sparse | 2 / 14 | 4 / 16 |
| cold_start | 5 / 16 | 7 / 19 |
| delayed | 2 / 15 | 4 / 17 |
| shift | 2 / 14 | 4 / 16 |
| drift | 2 / 15 | 4 / 17 |

Slowest single policy call in the 600 final-config episodes (in-process, excludes interpreter start): **0.12 s** (limit 10 s).

### C. Invalid-episode audit

Across every result file in `results/` (all policies, ablations, seeds, official and in-process): **7842 episodes, 0 invalid**.

