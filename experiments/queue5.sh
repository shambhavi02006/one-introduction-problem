#!/bin/bash
# Final-config re-run after prior=neutral_emp was adopted (decided on validation seeds 2000-2019 only).
cd "$(dirname "$0")/.."
while ! grep -q QUEUE4_DONE results/queue4.log; do sleep 20; done
python3 experiments/harness.py --policy ours --seeds 3020-3119 --variants all --out results/test2_ours.json
python3 evaluate.py --policy run_ours.py --seeds 101,102,103 --variants all --output results/official_ours.json > results/official_ours.log
python3 experiments/calibration_h3.py > results/calibration_h3.log 2>&1
python3 experiments/calibration_h4.py > results/calibration_h4.log 2>&1
echo QUEUE5_DONE
