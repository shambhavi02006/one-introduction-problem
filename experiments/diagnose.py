"""Why do truly-feasible pairs go untried? (analysis only: reads latent truth, never used by the policy)"""
import itertools, json, os, sys, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'experiments'))
from kit import Simulator, generate, eligibility, HARD
from harness import make_actor
from smp.feasibility import is_resolved


def run(spec, seed, variant):
    world = generate(seed, 200, 'evaluation', variant)
    sim = Simulator(world); actor = make_actor(spec); mem = None
    free_days = collections.defaultdict(set)   # day -> ids available & resolved at match time
    resolved_day = {}
    for day in range(60):
        out, mem = actor('ask', sim.observe(), mem); sim.resolve_asks(out)
        st = sim.observe()
        for m in st['members']:
            if is_resolved(m):
                resolved_day.setdefault(m['member_id'], day)
                if m['available']:
                    free_days[day].add(m['member_id'])
        out, mem = actor('match', st, mem); sim.advance(out)
    for _ in range(40): sim.advance([])
    tried = {tuple(sorted((i['user_a'], i['user_b']))) for i in sim.introductions}
    ms = {}
    for m in world['members']:
        if m['arrived_day'] > 59 or any(m['field_status'][k] == 'declined' for k in HARD): continue
        c = dict(m); c['fields'] = {k: (m['truth'][k] if k in HARD else v) for k, v in m['fields'].items()}
        ms[m['member_id']] = c
    cls = collections.Counter(); n_feas = 0
    for a, b in itertools.combinations(sorted(ms), 2):
        if eligibility(ms[a], ms[b])['status'] != 'feasible': continue
        n_feas += 1
        if (a, b) in tried: cls['tried'] += 1; continue
        ma, mb = world['members'][0], None
        A, B = ms[a], ms[b]
        both = [d for d in range(60) if a in free_days[d] and b in free_days[d]]
        if a not in resolved_day or b not in resolved_day: cls['never_resolved'] += 1
        elif not both:
            if max(A['exit_day'], 0) < 60 or B['exit_day'] < 60: cls['never_jointly_free(exit involved)'] += 1
            else: cls['never_jointly_free'] += 1
        else: cls['jointly_free_but_matched_elsewhere'] += 1
    return n_feas, cls


if __name__ == '__main__':
    spec = (sys.argv[1], json.loads(sys.argv[2]) if len(sys.argv) > 2 else {})
    variant = sys.argv[3] if len(sys.argv) > 3 else 'development'
    tot = collections.Counter(); nf = 0
    for seed in range(2000, 2008):
        n, c = run(spec, seed, variant); nf += n; tot.update(c)
    print(spec[0], variant, 'true feasible pairs (8 seeds):', nf)
    for k, v in tot.most_common(): print('  %-42s %5d  %5.1f%%' % (k, v, 100 * v / nf))
