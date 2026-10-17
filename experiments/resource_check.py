"""Worst-case per-invocation wall time and peak RSS, as a fresh process (like evaluate.py), under a 1 GiB address-space cap."""
import json, os, resource, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from kit import Simulator, generate, baseline_asks, baseline_match

def child_limits():
    resource.setrlimit(resource.RLIMIT_AS, (1 << 30, 1 << 30))

worst = {'wall': 0, 'rss_mb': 0}
for variant in ('development', 'cold_start', 'sparse'):
    sim = Simulator(generate(2000, 200, 'evaluation', variant)); mem = None
    for day in range(0, 60, 6):                       # sample days across the episode
        for _ in range(6):
            sim.resolve_asks(baseline_asks(sim.observe())); sim.advance(baseline_match(sim.observe()))
        for phase in ('ask', 'match'):
            req = json.dumps({'schema_version': '1.0.0', 'phase': phase, 'state': sim.observe(), 'memory': mem}).encode()
            t = time.perf_counter()
            p = subprocess.run([sys.executable, os.path.join(ROOT, 'policy.py')], input=req, capture_output=True, preexec_fn=child_limits, timeout=10)
            wall = time.perf_counter() - t
            assert p.returncode == 0, p.stderr[:300]
            mem = json.loads(p.stdout)['memory']
            rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024
            worst['wall'] = max(worst['wall'], wall); worst['rss_mb'] = max(worst['rss_mb'], rss)
print('request bytes (last): %d | worst wall incl. startup: %.2fs (limit 10s) | peak RSS: %.0f MB (limit 1024 MB) | memory bytes: %d (limit 1 MiB)'
      % (len(req), worst['wall'], worst['rss_mb'], len(json.dumps(mem))))
