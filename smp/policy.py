"""Policy orchestration: normalise -> model -> clarify / allocate -> validate."""
import json
import sys
import time

from .feasibility import (FEASIBLE, has_declined_hard, is_resolved, pair_status, past_pairs,
                          validate_asks, validate_pairs)
from .model import Model
from .potential import Potential
from .clarify import choose_asks
from .allocate import max_weight_matching, greedy_matching
from . import baselines

DEFAULT_CFG = {
    'asks': 'voi',            # voi | list | none
    'soft_asks': True,
    'alloc': 'blossom',       # blossom | greedy
    'prior': 'neutral_emp',        # kit | neutral | neutral_emp  (neutral = generic priors, no simulator-derived constants)
    'adapt': True,            # online weight + member effects
    'eps_first': 0.15,        # first-introduction bonus, in units of mean pair value
    'lam': 0.0,               # reservation-value scale (0 = off)
    'slot_len': 9.0,          # days one introduction occupies a member (>= 8, longer if they date)
    'pot_weight': 0.7,        # weight of not-yet-resolved potential partners in a hub's edge count
    'soft_min_contest': 1,    # soft asks only on edges where an endpoint has >= this many alternatives (0 = every edge)
    'busy_discount': 0.8,
    'pair_credit': 0.5,
    'guard_seconds': 6.0,
    'seed': 0,
}


def make_cfg(overrides=None):
    cfg = dict(DEFAULT_CFG)
    cfg.update(overrides or {})
    return cfg


class Policy:
    def __init__(self, cfg=None):
        self.cfg = make_cfg(cfg)

    def _prep(self, state):
        members = list(state.get('members', []))
        by_id = {m['member_id']: m for m in members}
        model = Model(state, by_id, adapt=self.cfg['adapt'], prior=self.cfg['prior'])
        return members, by_id, model

    def ask(self, state, memory):
        t0 = time.perf_counter()
        members, by_id, model = self._prep(state)
        pot = Potential(members, neutral=self.cfg['prior'] != 'kit', empirical_age=self.cfg['prior'] == 'neutral_emp')
        try:
            asks = choose_asks(state, members, model, pot, self.cfg)
        except Exception as err:
            print('ask fallback: %r' % (err,), file=sys.stderr)
            asks = baselines.baseline_asks(state)
        if time.perf_counter() - t0 > self.cfg['guard_seconds']:
            asks = baselines.baseline_asks(state)
        return validate_asks(state, asks), self._memory(memory, state)

    def match(self, state, memory):
        t0 = time.perf_counter()
        try:
            pairs = self._match(state, t0)
        except Exception as err:
            print('match fallback: %r' % (err,), file=sys.stderr)
            pairs = baselines.baseline_match(state)
        return validate_pairs(state, pairs), self._memory(memory, state)

    def _match(self, state, t0):
        cfg = self.cfg
        members, by_id, model = self._prep(state)
        past = past_pairs(state)
        day = state.get('day', 0)
        introduced = {i for p in past for i in p}
        resolved = [m for m in members if is_resolved(m)]
        edges, nbr = [], {}                       # all feasible edges (busy partners included)
        for x in range(len(resolved)):
            a = resolved[x]
            for y in range(x + 1, len(resolved)):
                b = resolved[y]
                if pair_status(a, b) != FEASIBLE:
                    continue
                if tuple(sorted((a['member_id'], b['member_id']))) in past:
                    continue
                v = model.value(a, b)
                edges.append((a, b, v))
                nbr.setdefault(a['member_id'], []).append((v, 1.0, b['available']))
                nbr.setdefault(b['member_id'], []).append((v, 1.0, a['available']))
            if time.perf_counter() - t0 > cfg['guard_seconds']:
                return baselines.baseline_match(state)
        live_edges = [e for e in edges if e[0]['available'] and e[1]['available']]
        if not live_edges:
            return []
        mean_v = sum(e[2] for e in live_edges) / len(live_edges)
        lam = {}
        if cfg['lam'] > 0:
            lam = self._reservation(state, members, model, past, nbr, day, mean_v)
        weighted = []
        for a, b, v in live_edges:
            ia, ib = a['member_id'], b['member_id']
            w = v / mean_v if mean_v > 0 else 1.0
            w -= cfg['lam'] * (lam.get(ia, 0.0) + lam.get(ib, 0.0))
            for i in (ia, ib):
                if i not in introduced:
                    w += cfg['eps_first']
            if w > 1e-9:
                weighted.append((ia, ib, w))
        if not weighted:
            return []
        if cfg['alloc'] == 'greedy':
            return [list(p) for p in greedy_matching(weighted)]
        return [list(p) for p in max_weight_matching(weighted)]

    def _reservation(self, state, members, model, past, nbr, day, mean_v):
        """lambda_a = normalised value of a's S_a-th best remaining edge, 0 if every edge fits."""
        cfg = self.cfg
        slots = int((59 - day) // cfg['slot_len']) + 1
        pot = Potential(members, neutral=self.cfg['prior'] != 'kit', empirical_age=self.cfg['prior'] == 'neutral_emp')
        unresolved = [m for m in members if not is_resolved(m) and not has_declined_hard(m)]
        out = {}
        for m in members:
            i = m['member_id']
            ent = [(v, 1.0) for v, _, _ in nbr.get(i, [])]
            if is_resolved(m):
                for u in unresolved:
                    if tuple(sorted((i, u['member_id']))) in past or pair_status(m, u) == 'infeasible':
                        continue
                    q = pot.q(m, u)
                    if q >= 0.05:
                        ent.append((model.value(m, u), q * cfg['pot_weight']))
            mass = sum(p for _, p in ent)
            if mass <= slots + 1e-9:
                continue
            acc = 0.0
            for v, p in sorted(ent, reverse=True):
                acc += p
                if acc >= slots:
                    out[i] = v / mean_v if mean_v > 0 else 0.0
                    break
        return out

    @staticmethod
    def _memory(memory, state):
        calls = memory.get('calls', 0) + 1 if isinstance(memory, dict) else 1
        return {'v': 1, 'calls': calls, 'last_day': state.get('day', 0)}
