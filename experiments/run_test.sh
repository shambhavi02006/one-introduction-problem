#!/bin/bash
# Held-out test seeds 3000-3019 (20 per family = the size of the private assessment). Touched once, at the end.
cd "$(dirname "$0")/.."
run() { python3 experiments/harness.py --policy "$2" --cfg "${3:-{\}}" --seeds 3000-3019 --variants all --out results/test_$1.json; }
run ours ours
run greedy greedy
run no_asks no_asks
run random random
run abl_no_clarification ours '{"asks":"none"}'
run abl_list_order_asks  ours '{"asks":"list"}'
run abl_greedy_allocation ours '{"alloc":"greedy"}'
run abl_static_model ours '{"adapt":false}'
run abl_no_soft_asks ours '{"soft_asks":false}'
run abl_reservation_values ours '{"lam":0.25}'
echo ALL_DONE
