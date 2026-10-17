"""JSON stdin/stdout protocol: one request in, one response out, then exit."""
import argparse
import json
import os
import sys

from .policy import Policy
from . import baselines


def handle(request, baseline=None, cfg=None):
    phase = request['phase']
    state = request.get('state') or {'members': [], 'introductions': [], 'feedback': [], 'day': 0,
                                     'ask_budget_remaining': 0}
    memory = request.get('memory')
    if baseline:
        return baselines.respond(baseline, phase, state, memory)
    pol = Policy(cfg)
    try:
        if phase == 'ask':
            asks, mem = pol.ask(state, memory)
            return {'asks': asks, 'memory': mem}
        pairs, mem = pol.match(state, memory)
        return {'pairs': pairs, 'memory': mem}
    except Exception as err:  # last lines of defence: baseline behaviour, then an empty action (always valid)
        print('policy failure, falling back: %r' % (err,), file=sys.stderr)
        try:
            out = baselines.respond('greedy', phase, state, memory)
            key = 'asks' if phase == 'ask' else 'pairs'
            from .feasibility import validate_asks, validate_pairs
            out[key] = (validate_asks if phase == 'ask' else validate_pairs)(state, out[key])
            out['memory'] = {'v': 1, 'calls': 0}
            return out
        except Exception as err2:
            print('baseline fallback failed too: %r' % (err2,), file=sys.stderr)
            return {('asks' if phase == 'ask' else 'pairs'): [], 'memory': {'v': 1, 'calls': 0}}


def main(mode='auto'):
    ap = argparse.ArgumentParser()
    ap.add_argument('--baseline', default=None)
    known, _ = ap.parse_known_args()
    baseline = known.baseline if mode == 'auto' else None
    cfg = json.loads(os.environ['SMP_CONFIG']) if os.environ.get('SMP_CONFIG') else None
    request = json.loads(sys.stdin.read())
    response = handle(request, baseline, cfg)
    sys.stdout.write(json.dumps(response, allow_nan=False))
    sys.stdout.flush()
