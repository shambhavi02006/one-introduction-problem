"""Fast in-process harness that mirrors evaluate.episode() (same loop, same metrics).

Adds ANALYSIS-ONLY diagnostics that read the simulator's latent values; the policy never sees them:
  expected_msmi : sum over introductions of the exact conditional probability of qualifying
                  (removes coin-flip noise of dates / 3-day answers; labelled a diagnostic everywhere)
  edge_utilisation : tried / truly-feasible servable pairs
Official numbers always come from evaluate.py (see run_official.sh).
"""
import argparse
import itertools
import json
import math
import os
import sys
import time
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from kit import Simulator, generate, rand_for, eligibility, HARD  # noqa: E402
from smp.policy import Policy  # noqa: E402
from smp import baselines  # noqa: E402

VARIANTS = ('development', 'sparse', 'cold_start', 'delayed', 'shift', 'drift')


def _sig(z):
    return 1 / (1 + math.exp(-z))


def _window_prob(delayed):
    """P(date_day - assigned_day <= 30)."""
    ok = tot = 0
    for d1, d2, r1 in itertools.product(range(1, 8), range(1, 8), range(1, 15)):
        for r2 in (range(5, 13) if delayed else (0,)):
            tot += 1
            ok += max(d1, d2) + r1 + r2 <= 30
    return ok / tot


WINDOW = {False: _window_prob(False), True: _window_prob(True)}


def expected_msmi(sim):
    total = 0.0
    delayed = sim.world['variant'] == 'delayed'
    for intro in sim.introductions:
        a, b, day = intro['user_a'], intro['user_b'], intro['assigned_day']
        ma, mb = sim.members[a], sim.members[b]
        shared = rand_for(sim.world['seed'], a, b, day).gauss(0, .45)
        saved, sim.day = sim.day, day
        pa, pb = sim._prob(ma, mb, shared), sim._prob(mb, ma, shared)
        sim.day = saved
        p = ma['response_rate'] * mb['response_rate'] * pa * pb * WINDOW[delayed] * .78
        goal = ma['truth']['relationship_goal'] == mb['truth']['relationship_goal']
        for actor in (ma, mb):
            ps = _sig(.15 + actor['second_bias'] + shared + .4 * goal)
            p *= actor['response_rate'] * .6 * ps
        total += p
    return total


def true_feasible_pairs(world):
    """(#truly feasible pairs among servable arrived members, ids with >=1 partner, ids that declined a hard field)."""
    ms, declined = [], set()
    for m in world['members']:
        if m['arrived_day'] > 59:
            continue
        if any(m['field_status'][k] == 'declined' for k in HARD):
            declined.add(m['member_id'])
            continue
        c = dict(m)
        c['fields'] = {k: (m['truth'][k] if k in HARD else v) for k, v in m['fields'].items()}
        ms.append(c)
    n, has_partner = 0, set()
    for a, b in itertools.combinations(ms, 2):
        if eligibility(a, b)['status'] == 'feasible':
            n += 1
            has_partner.update((a['member_id'], b['member_id']))
    return n, has_partner, declined


def make_actor(spec):
    kind, cfg = spec
    if kind == 'ours':
        pol = Policy(cfg)
        return lambda phase, state, memory: (pol.ask if phase == 'ask' else pol.match)(state, memory)
    def run(phase, state, memory):
        r = baselines.respond(kind, phase, state, memory)
        return r['asks' if phase == 'ask' else 'pairs'], r['memory']
    return run


def episode(args):
    spec, seed, variant = args
    world = generate(seed, 200, 'evaluation', variant)
    sim = Simulator(world)
    actor = make_actor(spec)
    memory = None
    row = {'seed': seed, 'variant': variant, 'valid': True}
    calls = []
    try:
        for _ in range(60):
            for phase in ('ask', 'match'):
                t0 = time.perf_counter()
                out, memory = actor(phase, sim.observe(), memory)
                calls.append(time.perf_counter() - t0)
                json.dumps({'a': out, 'm': memory}, allow_nan=False)
                if phase == 'ask':
                    sim.resolve_asks(out)
                else:
                    sim.advance(out)
        arrived = {m['member_id']: m['arrived_day'] for m in sim.observe()['members'] if m['arrived_day'] <= 59}
        for _ in range(40):
            sim.advance([])
        res = sim.metrics()
        first = {}
        for intro in sim.introductions:
            for member in (intro['user_a'], intro['user_b']):
                first.setdefault(member, intro['assigned_day'])
        row.update(res)
        row.update(arrived_members=len(arrived),
                   msmi_per_100_arrived_members=100 * res['mutual_second_meeting_intention'] / max(1, len(arrived)),
                   served_members=len(first), coverage=len(first) / max(1, len(arrived)),
                   mutual_acceptances_per_100=100 * res['mutual_acceptances'] / max(1, len(arrived)),
                   waits=sorted(first[i] - arrived[i] for i in first if i in arrived),
                   expected_msmi_per_100=100 * expected_msmi(sim) / max(1, len(arrived)))
        n_feas, has_partner, declined = true_feasible_pairs(world)
        unserved = [i for i in arrived if i not in first]
        row.update(feasible_true=n_feas,
                   unserved_members=len(unserved),
                   unserved_declined_hard=sum(i in declined for i in unserved),
                   unserved_no_feasible_partner=sum(i not in declined and i not in has_partner for i in unserved),
                   unserved_policy_or_capacity=sum(i not in declined and i in has_partner for i in unserved),
                   max_call_seconds=max(calls), mean_call_seconds=sum(calls) / len(calls))
        row['edge_utilisation'] = row['assignments'] / max(1, row['feasible_true'])
    except Exception as err:  # noqa: BLE001
        row.update(valid=False, error=repr(err))
    return row


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--policy', default='ours')            # ours | greedy | no_asks | random
    p.add_argument('--cfg', default='{}')
    p.add_argument('--seeds', default='2000-2009')
    p.add_argument('--variants', default='all')
    p.add_argument('--out', required=True)
    p.add_argument('--procs', type=int, default=2)
    a = p.parse_args()
    lo, _, hi = a.seeds.partition('-')
    seeds = list(range(int(lo), int(hi or lo) + 1)) if '-' in a.seeds else [int(s) for s in a.seeds.split(',')]
    variants = VARIANTS if a.variants == 'all' else a.variants.split(',')
    spec = (a.policy, json.loads(a.cfg))
    jobs = [(spec, s, v) for v in variants for s in seeds]
    with Pool(a.procs) as pool:
        rows = pool.map(episode, jobs, chunksize=1)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump({'policy': a.policy, 'cfg': spec[1], 'rows': rows}, open(a.out, 'w'))
    bad = [r for r in rows if not r['valid']]
    print('episodes', len(rows), 'invalid', len(bad))
    for r in bad[:3]:
        print(r['variant'], r['seed'], r['error'])


if __name__ == '__main__':
    main()
