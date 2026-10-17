#!/bin/bash
# FINAL configuration (prior=neutral default). Official evaluator on public seeds, then extra held-out seeds 3020-3119
# (never used for tuning). Sequential so timing numbers are not distorted by contention.
# results/test2_ours_kit_prior.json was produced earlier with {"prior":"kit"} (the previous default) on the same seeds.
cd "$(dirname "$0")/.."
bash experiments/run_official.sh
run() { python3 experiments/harness.py --policy "$2" --cfg "${3:-{\}}" --seeds 3020-3119 --variants all --out results/test2_$1.json; }
run ours ours
run greedy greedy
run random random
run abl_list_order_asks ours '{"asks":"list"}'
run abl_greedy_allocation ours '{"alloc":"greedy"}'
run no_asks no_asks
echo QUEUE4_DONE
