"""Max size of the request evaluate.py would send (limit 1 MiB), over a full 60+ day episode, for ours and greedy."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'experiments'))
from kit import Simulator, generate
from harness import make_actor
for spec in (('ours', {}), ('greedy', {})):
    for variant in ('development', 'cold_start', 'delayed'):
        sim = Simulator(generate(2003, 200, 'evaluation', variant)); act = make_actor(spec); mem = None; worst = 0
        for _ in range(60):
            for phase in ('ask', 'match'):
                st = sim.observe()
                worst = max(worst, len(json.dumps({'schema_version': '1.0.0', 'phase': phase, 'state': st, 'memory': mem}).encode()))
                out, mem = act(phase, st, mem)
                sim.resolve_asks(out) if phase == 'ask' else sim.advance(out)
        print('%-7s %-12s max request %7d bytes = %4.1f%% of 1 MiB' % (spec[0], variant, worst, 100 * worst / 1048576))
