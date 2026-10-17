#!/bin/bash
cd "$(dirname "$0")/.."
experiments/run_val.sh abl_no_asks      ours '{"asks":"none"}'
experiments/run_val.sh abl_list_asks    ours '{"asks":"list"}'
experiments/run_val.sh abl_greedy_alloc ours '{"alloc":"greedy"}'
experiments/run_val.sh abl_static_model ours '{"adapt":false}'
experiments/run_val.sh abl_no_soft_asks ours '{"soft_asks":false}'
experiments/run_val.sh abl_no_first_bonus ours '{"eps_first":0.0}'
echo ALL_DONE
