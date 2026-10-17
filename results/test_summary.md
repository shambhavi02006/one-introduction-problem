### Overall (organiser scoring rule: mean of six family means; 20 seeds/family)

| policy | eps | invalid | **MSMI/100** | expected-MSMI/100 (diag.) | coverage | mutual acc/100 | assignments | ask cost |
|---|---|---|---|---|---|---|---|---|
| ours | 120 | 0 | **0.371** | 0.363 | 0.340 | 5.37 | 73.9 | 226 |
| greedy | 120 | 0 | **0.442** | 0.357 | 0.338 | 5.10 | 74.0 | 206 |
| no_asks | 120 | 0 | **0.079** | 0.094 | 0.116 | 1.45 | 20.6 | 0 |
| random | 120 | 0 | **0.358** | 0.362 | 0.340 | 4.95 | 74.3 | 206 |
| abl_greedy_allocation | 120 | 0 | **0.312** | 0.371 | 0.340 | 5.38 | 74.2 | 226 |
| abl_list_order_asks | 120 | 0 | **0.458** | 0.358 | 0.340 | 5.47 | 73.3 | 206 |
| abl_no_clarification | 120 | 0 | **0.092** | 0.095 | 0.116 | 1.40 | 20.5 | 0 |
| abl_no_soft_asks | 120 | 0 | **0.379** | 0.361 | 0.341 | 5.50 | 74.0 | 197 |
| abl_reservation_values | 120 | 0 | **0.362** | 0.362 | 0.340 | 5.32 | 73.5 | 227 |
| abl_static_model | 120 | 0 | **0.350** | 0.362 | 0.339 | 5.36 | 73.8 | 226 |

### Per scenario family: MSMI/100 (expected-MSMI diagnostic)

| policy | development | sparse | cold_start | delayed | shift | drift |
|---|---|---|---|---|---|---|
| ours | 0.47 (0.44) | 0.07 (0.11) | 0.33 (0.39) | 0.45 (0.42) | 0.45 (0.40) | 0.45 (0.42) |
| greedy | 0.50 (0.44) | 0.17 (0.11) | 0.55 (0.37) | 0.47 (0.42) | 0.45 (0.39) | 0.50 (0.42) |
| no_asks | 0.07 (0.13) | 0.03 (0.04) | 0.12 (0.04) | 0.10 (0.13) | 0.07 (0.11) | 0.07 (0.12) |
| random | 0.30 (0.45) | 0.15 (0.12) | 0.47 (0.37) | 0.53 (0.42) | 0.42 (0.39) | 0.28 (0.43) |
| abl_greedy_allocation | 0.40 (0.46) | 0.10 (0.11) | 0.30 (0.38) | 0.38 (0.44) | 0.35 (0.41) | 0.35 (0.43) |
| abl_list_order_asks | 0.50 (0.44) | 0.12 (0.12) | 0.55 (0.37) | 0.68 (0.41) | 0.42 (0.39) | 0.47 (0.42) |
| abl_no_clarification | 0.10 (0.13) | 0.03 (0.04) | 0.10 (0.04) | 0.17 (0.12) | 0.05 (0.12) | 0.10 (0.13) |
| abl_no_soft_asks | 0.47 (0.44) | 0.10 (0.11) | 0.35 (0.39) | 0.47 (0.42) | 0.42 (0.38) | 0.45 (0.42) |
| abl_reservation_values | 0.45 (0.44) | 0.07 (0.11) | 0.33 (0.39) | 0.42 (0.42) | 0.45 (0.39) | 0.45 (0.42) |
| abl_static_model | 0.38 (0.44) | 0.07 (0.11) | 0.33 (0.39) | 0.47 (0.41) | 0.45 (0.38) | 0.40 (0.42) |

### Paired differences: ours minus comparator (positive = ours better)

| comparator | metric | diff | 95% CI (bootstrap over seeds) | Wilcoxon p |
|---|---|---|---|---|
| abl_greedy_allocation | msmi/100 | +0.058 | +0.004 … +0.117 | 0.052 |
| abl_greedy_allocation | expected_msmi/100 | -0.008 | -0.015 … -0.002 | 0.104 |
| abl_greedy_allocation | assignments | -0.250 | -1.033 … +0.517 | 0.740 |
| abl_greedy_allocation | mutual_acceptances/100 | -0.004 | -0.221 … +0.217 | 0.915 |
| abl_list_order_asks | msmi/100 | -0.088 | -0.171 … -0.008 | 0.052 |
| abl_list_order_asks | expected_msmi/100 | +0.005 | -0.005 … +0.014 | 0.635 |
| abl_list_order_asks | assignments | +0.583 | -0.350 … +1.475 | 0.193 |
| abl_list_order_asks | mutual_acceptances/100 | -0.096 | -0.383 … +0.192 | 0.757 |
| abl_no_clarification | msmi/100 | +0.279 | +0.208 … +0.354 | 0.000 |
| abl_no_clarification | expected_msmi/100 | +0.268 | +0.255 … +0.281 | 0.000 |
| abl_no_clarification | assignments | +53.458 | +51.650 … +55.250 | 0.000 |
| abl_no_clarification | mutual_acceptances/100 | +3.971 | +3.650 … +4.300 | 0.000 |
| abl_no_soft_asks | msmi/100 | -0.008 | -0.050 … +0.033 | 0.695 |
| abl_no_soft_asks | expected_msmi/100 | +0.002 | -0.002 … +0.005 | 0.580 |
| abl_no_soft_asks | assignments | -0.108 | -0.458 … +0.250 | 0.382 |
| abl_no_soft_asks | mutual_acceptances/100 | -0.129 | -0.254 … -0.004 | 0.088 |
| abl_reservation_values | msmi/100 | +0.008 | -0.008 … +0.029 | 0.414 |
| abl_reservation_values | expected_msmi/100 | +0.000 | -0.002 … +0.003 | 0.075 |
| abl_reservation_values | assignments | +0.450 | +0.225 … +0.683 | 0.000 |
| abl_reservation_values | mutual_acceptances/100 | +0.054 | +0.000 … +0.113 | 0.069 |
| abl_static_model | msmi/100 | +0.021 | -0.033 … +0.071 | 0.433 |
| abl_static_model | expected_msmi/100 | +0.001 | -0.003 … +0.005 | 0.752 |
| abl_static_model | assignments | +0.108 | -0.292 … +0.500 | 0.603 |
| abl_static_model | mutual_acceptances/100 | +0.008 | -0.142 … +0.163 | 0.848 |
| greedy | msmi/100 | -0.071 | -0.171 … +0.025 | 0.212 |
| greedy | expected_msmi/100 | +0.005 | -0.003 … +0.014 | 0.308 |
| greedy | assignments | -0.092 | -1.008 … +0.808 | 0.907 |
| greedy | mutual_acceptances/100 | +0.267 | -0.008 … +0.567 | 0.113 |
| no_asks | msmi/100 | +0.292 | +0.212 … +0.371 | 0.000 |
| no_asks | expected_msmi/100 | +0.268 | +0.255 … +0.281 | 0.000 |
| no_asks | assignments | +53.317 | +51.492 … +55.108 | 0.000 |
| no_asks | mutual_acceptances/100 | +3.925 | +3.621 … +4.263 | 0.000 |
| random | msmi/100 | +0.012 | -0.075 … +0.100 | 0.620 |
| random | expected_msmi/100 | +0.001 | -0.008 … +0.010 | 0.775 |
| random | assignments | -0.350 | -1.350 … +0.617 | 0.630 |
| random | mutual_acceptances/100 | +0.425 | +0.142 … +0.721 | 0.021 |

### Who is not served (mean per episode, ours)

| family | arrived | served | unserved | declined a hard field | no feasible partner exists | policy/capacity |
|---|---|---|---|---|---|---|
| development | 200 | 77.5 | 122.5 | 65.3 | 55.9 | 1.2 |
| sparse | 200 | 33.1 | 166.9 | 65.7 | 101.0 | 0.2 |
| cold_start | 200 | 65.3 | 134.7 | 80.0 | 53.5 | 1.2 |
| delayed | 200 | 77.2 | 122.8 | 65.3 | 55.9 | 1.6 |
| shift | 200 | 77.5 | 122.5 | 65.3 | 55.9 | 1.3 |
| drift | 200 | 77.5 | 122.5 | 65.3 | 55.9 | 1.2 |

### First-introduction waiting time, days from arrival (pooled over served members)

| family | ours median / p90 | greedy median / p90 |
|---|---|---|
| development | 3 / 14 | 4 / 16 |
| sparse | 1.0 / 14 | 4.0 / 15 |
| cold_start | 5.0 / 17 | 7.0 / 20 |
| delayed | 3 / 14 | 4 / 16 |
| shift | 3.0 / 14 | 4 / 16 |
| drift | 3 / 14 | 4 / 16 |
