#!/bin/bash
# Official evaluate.py (trusted-local subprocess mode) on the public seeds, all six variants.
# Baselines run through policy.py --baseline X; our policy through run_ours.py (ignores that flag).
cd "$(dirname "$0")/.."
SEEDS=${SEEDS:-101,102,103}
for b in greedy no_asks random; do
  python3 evaluate.py --policy policy.py --baseline $b --seeds $SEEDS --variants all --output results/official_$b.json > results/official_$b.log
done
python3 evaluate.py --policy run_ours.py --seeds $SEEDS --variants all --output results/official_ours.json > results/official_ours.log
