#!/bin/bash
cd "$(dirname "$0")/.."
experiments/run_val.sh abl_reservation_1.0  ours '{"lam":1.0}'
experiments/run_val.sh abl_reservation_0.25 ours '{"lam":0.25}'
experiments/run_val.sh var_soft_everywhere  ours '{"soft_min_contest":0}'
echo ALL_DONE
