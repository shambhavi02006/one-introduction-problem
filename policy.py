"""Entry point. No arguments -> our policy (what the Docker image runs).
`--baseline greedy|no_asks|random` -> supplied-baseline behaviour for evaluate.py comparisons."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smp.cli import main

if __name__ == '__main__':
    main('auto')
