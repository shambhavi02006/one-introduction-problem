"""Always runs OUR policy, ignoring evaluate.py's --baseline flag.
Ablations: SMP_CONFIG='{"asks":"none"}' python evaluate.py --policy run_ours.py ..."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smp.cli import main

if __name__ == '__main__':
    main('ours')
