#!/bin/bash
# Validation-seed runs (2000-2019). Usage: run_val.sh name policy 'cfg-json'
cd "$(dirname "$0")/.."
python3 experiments/harness.py --policy "$2" --cfg "${3:-{\}}" --seeds 2000-2019 --variants all --out results/val_$1.json
