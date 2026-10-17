#!/bin/bash
# 1) official evaluator on public seeds; 2) extra held-out seeds 3020-3119 (not used for any tuning).
cd "$(dirname "$0")/.."
bash experiments/run_official.sh
run() { python3 experiments/harness.py --policy "$2" --cfg "${3:-{\}}" --seeds 3020-3119 --variants all --out results/test2_$1.json; }
run ours ours
run greedy greedy
run abl_list_order_asks ours '{"asks":"list"}'
run abl_greedy_allocation ours '{"alloc":"greedy"}'
run random random
echo QUEUE3_DONE
