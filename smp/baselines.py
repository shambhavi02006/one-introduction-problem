"""Re-implementations of the three supplied baselines (greedy, no_asks, random-feasible).

The starter policy.py was not in the files we received, so these follow
kit.baseline_asks / kit.baseline_match; random-feasible = greedy asks +
random-order maximal feasible matching.
"""
import hashlib
import itertools
import random

from .feasibility import HARD, SOFT, exact_eligibility


def baseline_asks(state):
    eligible = [m for m in state['members'] if m['available'] and any(m['fields'][k] is None for k in HARD)
                and not any(m['field_status'][k] == 'declined' for k in HARD)]
    return [{'member_id': m['member_id'], 'field': 'constraints'}
            for m in eligible[:state['ask_budget_remaining'] // 3]]


def _feasible_edges(state):
    members = [m for m in state['members'] if m['available']]
    past = {tuple(sorted((i['user_a'], i['user_b']))) for i in state['introductions']}
    edges = []
    for a, b in itertools.combinations(members, 2):
        key = tuple(sorted((a['member_id'], b['member_id'])))
        if key in past or exact_eligibility(a, b)['status'] != 'feasible':
            continue
        score = sum(a['fields'].get(k) is not None and a['fields'].get(k) == b['fields'].get(k) for k in SOFT)
        edges.append((-score, key))
    return edges


def baseline_match(state):
    used, out = set(), []
    for _, pair in sorted(_feasible_edges(state)):
        if not used.intersection(pair):
            out.append(list(pair))
            used.update(pair)
    return out


def random_match(state):
    edges = _feasible_edges(state)
    seed = hashlib.sha256(('%s|%s' % (state['day'], len(state['members']))).encode()).hexdigest()
    rng = random.Random(seed)
    rng.shuffle(edges)
    used, out = set(), []
    for _, pair in edges:
        if not used.intersection(pair):
            out.append(list(pair))
            used.update(pair)
    return out


def respond(name, phase, state, memory):
    if phase == 'ask':
        asks = [] if name == 'no_asks' else baseline_asks(state)
        return {'asks': asks, 'memory': memory if isinstance(memory, dict) else {}}
    pairs = random_match(state) if name == 'random' else baseline_match(state)
    return {'pairs': pairs, 'memory': memory if isinstance(memory, dict) else {}}
