"""Run: python -m unittest discover -s tests -v   (stdlib only)"""
import copy
import itertools
import json
import os
import random
import subprocess
import sys
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import kit  # noqa: E402
from smp import feasibility as F  # noqa: E402
from smp.allocate import max_weight_matching  # noqa: E402
from smp.cli import handle  # noqa: E402
from smp.policy import Policy  # noqa: E402

EMPTY = {'schema_version': '1.0.0', 'synthetic': True, 'day': 0, 'ask_budget_remaining': 12,
         'members': [], 'introductions': [], 'feedback': [], 'ask_log': []}


def observed_state(seed=7, variant='development', day=0, resolve_all=False):
    sim = kit.Simulator(kit.generate(seed, 200, 'evaluation', variant))
    if resolve_all:
        sim.resolve_asks([{'member_id': m['member_id'], 'field': 'constraints'}
                          for m in sim.observe()['members']][:4])
    for _ in range(day):
        sim.resolve_asks(kit.baseline_asks(sim.observe()))
        sim.advance(kit.baseline_match(sim.observe()))
    return sim, sim.observe()


class Eligibility(unittest.TestCase):
    def test_exact_copy_matches_kit(self):
        _, st = observed_state(day=12)
        ms = st['members']
        for a, b in itertools.islice(itertools.combinations(ms, 2), 6000):
            self.assertEqual(F.exact_eligibility(a, b), kit.eligibility(a, b))

    def test_fast_status_matches_kit_incl_partial_info(self):
        for seed, variant in ((3, 'development'), (4, 'sparse'), (5, 'cold_start')):
            _, st = observed_state(seed, variant, day=15)
            for a, b in itertools.islice(itertools.combinations(st['members'], 2), 8000):
                self.assertEqual(F.pair_status(a, b), kit.eligibility(a, b)['status'])

    def test_known_failure_beats_missing(self):
        _, st = observed_state()
        a, b = copy.deepcopy(st['members'][:2])
        a['fields']['who_to_meet'] = ['woman']
        b['gender'] = 'man'
        b['fields']['schedule'] = None
        self.assertEqual(F.pair_status(a, b), 'infeasible')


class Robustness(unittest.TestCase):
    def test_empty_population(self):
        for phase in ('ask', 'match'):
            r = handle({'phase': phase, 'state': EMPTY, 'memory': None})
            self.assertEqual(set(r), {'asks' if phase == 'ask' else 'pairs', 'memory'})
            self.assertEqual(r['asks' if phase == 'ask' else 'pairs'], [])

    def test_missing_state_and_garbage_memory(self):
        for mem in (None, {}, {'junk': [1, 2]}, 'x', 3):
            r = handle({'phase': 'match', 'state': EMPTY, 'memory': mem})
            self.assertEqual(r['pairs'], [])
            json.dumps(r, allow_nan=False)

    def test_all_declined_pool(self):
        _, st = observed_state()
        st = copy.deepcopy(st)
        for m in st['members']:
            m['fields']['age_min'] = None
            m['field_status']['age_min'] = 'declined'
        self.assertEqual(handle({'phase': 'ask', 'state': st, 'memory': None})['asks'], [])
        self.assertEqual(handle({'phase': 'match', 'state': st, 'memory': None})['pairs'], [])

    def test_no_feasible_edges(self):
        _, st = observed_state()
        st = copy.deepcopy(st)
        for m in st['members']:
            m['available'] = False
        self.assertEqual(handle({'phase': 'match', 'state': st, 'memory': None})['pairs'], [])
        self.assertEqual(handle({'phase': 'ask', 'state': st, 'memory': None})['asks'], [])

    def test_200_simultaneous_arrivals_dense_graph(self):
        _, st = observed_state()
        st = copy.deepcopy(st)
        every = {'age_min': 18, 'age_max': 65, 'who_to_meet': ['woman', 'man', 'non_binary'],
                 'relationship_structure': 'monogamous', 'smoking': 'no', 'partner_smoking': 'any',
                 'has_children': False, 'partner_children': 'any', 'wants_children': 'unsure',
                 'acceptable_zones': ['zone_a', 'zone_b', 'zone_c', 'zone_d'],
                 'schedule': ['weekday_evening', 'weekend_day', 'weekend_evening']}
        for m in st['members']:
            m['arrived_day'], m['available'] = 0, True
            m['fields'].update(copy.deepcopy(every))
            for k in every:
                m['field_status'][k] = 'observed'
        t = time.perf_counter()
        r = handle({'phase': 'match', 'state': st, 'memory': None})
        self.assertLess(time.perf_counter() - t, 8.0)
        self.assertEqual(F.validate_pairs(st, r['pairs']), r['pairs'])
        self.assertEqual(len(r['pairs']), len(st['members']) // 2)  # perfect matching of a complete graph
        t = time.perf_counter()
        r = handle({'phase': 'ask', 'state': st, 'memory': None})
        self.assertLess(time.perf_counter() - t, 8.0)

    def test_budget_and_shape_over_full_episode(self):
        sim = kit.Simulator(kit.generate(11, 200, 'evaluation', 'cold_start'))
        pol, mem = Policy(), None
        for _ in range(30):
            asks, mem = pol.ask(sim.observe(), mem)
            self.assertLessEqual(sum(3 if a['field'] == 'constraints' else 1 for a in asks), 12)
            sim.resolve_asks(asks)               # raises on any invalid ask
            pairs, mem = pol.match(sim.observe(), mem)
            sim.advance(pairs)                   # raises on any invalid pair
            self.assertLess(len(json.dumps(mem)), 1024 * 1024)

    def test_never_asks_declined_or_busy(self):
        sim, st = observed_state(day=20)
        asks, _ = Policy().ask(st, None)
        by = {m['member_id']: m for m in st['members']}
        for a in asks:
            self.assertTrue(by[a['member_id']]['available'])
            if a['field'] == 'constraints':
                self.assertFalse(F.has_declined_hard(by[a['member_id']]))

    def test_deterministic(self):
        _, st = observed_state(day=10)
        a = handle({'phase': 'match', 'state': st, 'memory': None})
        b = handle({'phase': 'match', 'state': copy.deepcopy(st), 'memory': None})
        self.assertEqual(a, b)

    def test_validator_drops_bad_pairs(self):
        sim, st = observed_state(day=25)
        ids = [m['member_id'] for m in st['members']]
        junk = [[ids[0], ids[0]], ['nope', ids[1]], [ids[0], ids[1]], [ids[0], ids[2]]]
        out = F.validate_pairs(st, junk)
        used = [i for p in out for i in p]
        self.assertEqual(len(used), len(set(used)))
        sim.advance(out)  # must not raise

    def test_runtime_per_call(self):
        _, st = observed_state(day=0)
        t = time.perf_counter()
        handle({'phase': 'ask', 'state': st, 'memory': None})
        handle({'phase': 'match', 'state': st, 'memory': None})
        self.assertLess(time.perf_counter() - t, 5.0)


class Protocol(unittest.TestCase):
    def run_cli(self, req, *args, script='policy.py'):
        p = subprocess.run([sys.executable, os.path.join(ROOT, script), *args], input=json.dumps(req).encode(),
                           capture_output=True, timeout=10)
        self.assertEqual(p.returncode, 0, p.stderr[:500])
        return json.loads(p.stdout.decode())

    def test_subprocess_roundtrip_and_memory(self):
        _, st = observed_state(day=5)
        r = self.run_cli({'schema_version': '1.0.0', 'phase': 'ask', 'state': st, 'memory': None})
        self.assertEqual(set(r), {'asks', 'memory'})
        r2 = self.run_cli({'schema_version': '1.0.0', 'phase': 'match', 'state': st, 'memory': r['memory']})
        self.assertEqual(set(r2), {'pairs', 'memory'})

    def test_baseline_flags_and_ignore_in_run_ours(self):
        _, st = observed_state(day=5)
        for b in ('greedy', 'no_asks', 'random'):
            r = self.run_cli({'phase': 'ask', 'state': st, 'memory': None}, '--baseline', b)
            self.assertEqual(set(r), {'asks', 'memory'})
        self.assertEqual(self.run_cli({'phase': 'ask', 'state': st, 'memory': None}, '--baseline', 'no_asks')['asks'], [])
        r = self.run_cli({'phase': 'ask', 'state': st, 'memory': None}, '--baseline', 'greedy', script='run_ours.py')
        self.assertEqual(set(r), {'asks', 'memory'})


class Hardening(unittest.TestCase):
    def test_same_output_under_different_hash_seeds(self):
        _, st = observed_state(day=18)
        outs = []
        for hs in ('0', '1', '12345'):
            env = dict(os.environ, PYTHONHASHSEED=hs)
            for phase in ('ask', 'match'):
                p = subprocess.run([sys.executable, os.path.join(ROOT, 'policy.py')], env=env, capture_output=True,
                                   input=json.dumps({'phase': phase, 'state': st, 'memory': None}).encode(), timeout=10)
                self.assertEqual(p.returncode, 0)
                outs.append((phase, p.stdout))
        self.assertEqual(len({o for o in outs if o[0] == 'ask'}), 1)
        self.assertEqual(len({o for o in outs if o[0] == 'match'}), 1)

    def test_internal_failure_still_yields_valid_action(self):
        import smp.policy as sp
        _, st = observed_state(day=10)
        orig = sp.Model
        sp.Model = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('boom'))
        try:
            for phase in ('ask', 'match'):
                r = handle({'phase': phase, 'state': st, 'memory': None})
                self.assertEqual(set(r), {'asks' if phase == 'ask' else 'pairs', 'memory'})
            sim = kit.Simulator(kit.generate(7, 200, 'evaluation', 'development'))
            sim.resolve_asks(r.get('asks', []))
            sim.advance(handle({'phase': 'match', 'state': sim.observe(), 'memory': None})['pairs'])
        finally:
            sp.Model = orig

    def test_stdout_is_only_json_and_finite(self):
        _, st = observed_state(day=12)
        p = subprocess.run([sys.executable, os.path.join(ROOT, 'policy.py')], capture_output=True, timeout=10,
                           input=json.dumps({'phase': 'match', 'state': st, 'memory': None}).encode())
        json.loads(p.stdout.decode(), parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))


class Matching(unittest.TestCase):
    def test_spec_example_prefers_global_optimum(self):
        e = [('A', 'B', .90), ('C', 'D', .05), ('A', 'D', .65), ('B', 'C', .65)]
        got = {tuple(sorted(p)) for p in max_weight_matching(e)}
        self.assertEqual(got, {('A', 'D'), ('B', 'C')})

    def test_exact_equals_networkx(self):
        try:
            import networkx as nx
        except ImportError:
            self.skipTest('networkx not installed')
        rng = random.Random(1)
        for _ in range(150):
            n = rng.randint(2, 11)
            edges = [(i, j, rng.random() + .01) for i in range(n) for j in range(i + 1, n) if rng.random() < .5]
            if not edges:
                continue
            g = nx.Graph()
            g.add_weighted_edges_from(edges)
            want = sum(g[a][b]['weight'] for a, b in nx.max_weight_matching(g))
            w = {tuple(sorted((a, b))): x for a, b, x in edges}
            got = sum(w[tuple(sorted(p))] for p in max_weight_matching(edges))
            self.assertAlmostEqual(got, want, places=9)


class Provenance(unittest.TestCase):
    def test_default_prior_uses_no_simulator_constants(self):
        from smp.policy import DEFAULT_CFG
        self.assertEqual(DEFAULT_CFG['prior'], 'neutral_emp')

    def test_policy_package_does_not_import_the_simulator(self):
        import glob
        for path in glob.glob(os.path.join(ROOT, 'smp', '*.py')) + [os.path.join(ROOT, 'policy.py')]:
            with open(path) as f:
                text = f.read()
            self.assertNotRegex(text, r'(?m)^\s*(import kit|from kit import)', path)

    def test_all_prior_modes_yield_valid_actions(self):
        sim, state = observed_state(seed=11, day=6)
        for prior in ('kit', 'neutral', 'neutral_emp'):
            pol = Policy({'prior': prior})
            state = sim.observe()
            asks, _ = pol.ask(state, None)
            self.assertLessEqual(sum(3 if a['field'] == 'constraints' else 1 for a in asks), state['ask_budget_remaining'])
            sim.resolve_asks(asks)
            pairs, _ = pol.match(sim.observe(), None)
            sim.advance(pairs)


if __name__ == '__main__':
    unittest.main()
