"""For feasible pairs that were jointly free yet never tried: were the endpoints capacity-bound or idle?"""
import itertools, json, os, sys, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'experiments'))
from kit import Simulator, generate, eligibility, HARD
from harness import make_actor
from smp.feasibility import is_resolved

def run(spec, seed, variant):
    world = generate(seed, 200, 'evaluation', variant)
    sim = Simulator(world); actor = make_actor(spec); mem = None
    free = collections.defaultdict(set); matched = collections.defaultdict(set)
    for day in range(60):
        out, mem = actor('ask', sim.observe(), mem); sim.resolve_asks(out)
        st = sim.observe()
        for m in st['members']:
            if is_resolved(m) and m['available']: free[day].add(m['member_id'])
        out, mem = actor('match', st, mem)
        for a, b in out: matched[day].update((a, b))
        sim.advance(out)
    for _ in range(40): sim.advance([])
    tried = {tuple(sorted((i['user_a'], i['user_b']))) for i in sim.introductions}
    ms = {}
    for m in world['members']:
        if m['arrived_day'] > 59 or any(m['field_status'][k] == 'declined' for k in HARD): continue
        c = dict(m); c['fields'] = {k: (m['truth'][k] if k in HARD else v) for k, v in m['fields'].items()}
        ms[m['member_id']] = c
    deg = collections.Counter()
    feas = []
    for a, b in itertools.combinations(sorted(ms), 2):
        if eligibility(ms[a], ms[b])['status'] == 'feasible':
            feas.append((a, b)); deg[a] += 1; deg[b] += 1
    out = collections.Counter(); hubdeg = []
    for a, b in feas:
        if (a, b) in tried: continue
        days = [d for d in range(60) if a in free[d] and b in free[d]]
        if not days: continue
        idle_both = [d for d in days if a not in matched[d] and b not in matched[d]]
        last = max(days)
        if idle_both: out['both_idle_same_day (policy omission)'] += 1
        elif last >= 50: out['contention, last joint-free day >= 50 (horizon-bound)'] += 1
        else: out['contention earlier (a or b taken by other partner each joint day)'] += 1
        hubdeg.append(max(deg[a], deg[b]))
    return out, hubdeg

if __name__ == '__main__':
    tot = collections.Counter(); hd = []
    for seed in range(2000, 2008):
        o, h = run((sys.argv[1], {}), seed, 'development'); tot.update(o); hd += h
    n = sum(tot.values()); print('untried-but-jointly-free pairs:', n)
    for k, v in tot.most_common(): print('  %-70s %4d %5.1f%%' % (k, v, 100 * v / n))
    print('  endpoint max-degree of these pairs: mean %.1f, median %d' % (sum(hd)/len(hd), sorted(hd)[len(hd)//2]))
