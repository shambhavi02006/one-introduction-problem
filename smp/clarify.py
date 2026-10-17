"""Value-of-information clarification.

Hard-constraint bundles (3 units) are bought where the answer unlocks the most
potential edge value soonest, pair-aware (two unresolved people who are each
other's best partner are asked on the same day). Members with a declined hard
field, or with no potential partner (q = 0), are never asked: those units buy
nothing. Spare units go to 1-unit soft asks only where the answer can change a
contested allocation.
"""
from .feasibility import (HARD, FEASIBLE, INFEASIBLE, is_resolved, has_declined_hard,
                          pair_status, past_pairs)
from .model import SOFT4

Q_MIN = 0.02
MIN_GAIN = 1e-4


def choose_asks(state, members, model, pot, cfg):
    budget = state.get('ask_budget_remaining', 0)
    if cfg['asks'] == 'none' or budget <= 0:
        return []
    past = past_pairs(state)
    asks = []
    cands = [m for m in members if m['available'] and not is_resolved(m) and not has_declined_hard(m)]
    if cfg['asks'] == 'list':
        # ablation: ask in list order like the supplied baseline (no VOI ranking)
        for m in cands[:budget // 3]:
            asks.append({'member_id': m['member_id'], 'field': 'constraints'})
        return asks

    partners = [m for m in members if not has_declined_hard(m)]
    cand_ids = {m['member_id'] for m in cands}
    edges = {}                      # cand id -> list of (partner id, weight)
    for a in cands:
        lst = []
        for b in partners:
            if a['member_id'] == b['member_id']:
                continue
            if tuple(sorted((a['member_id'], b['member_id']))) in past:
                continue
            if pair_status(a, b) == INFEASIBLE:
                continue
            q = pot.q(a, b)
            if q < Q_MIN:
                continue
            w = q * model.value(a, b)
            if not b['available']:
                w *= cfg['busy_discount']
            lst.append((b['member_id'], w))
        edges[a['member_id']] = lst
    resolved = {m['member_id'] for m in partners if is_resolved(m)}
    picked, remaining = [], set(cand_ids)
    for _ in range(budget // 3):
        best, best_gain = None, MIN_GAIN
        for i in sorted(remaining):
            gain = 0.0
            for b, w in edges[i]:
                if b in resolved or b in picked:
                    gain += w
                elif b in remaining:
                    gain += cfg['pair_credit'] * w
            if gain > best_gain + 1e-15:
                best, best_gain = i, gain
        if best is None:
            break
        picked.append(best)
        remaining.discard(best)
    asks = [{'member_id': i, 'field': 'constraints'} for i in picked]
    left = budget - 3 * len(picked)
    if cfg['soft_asks'] and left > 0:
        asks += _soft_asks(members, model, past, left, cfg.get('soft_min_contest', 1))
    return asks


def _soft_asks(members, model, past, left, min_contest=1):
    """Spend spare units only on contested edges (an endpoint has >= 2 feasible partners)."""
    live = [m for m in members if m['available'] and is_resolved(m)]
    nbr = {m['member_id']: [] for m in live}
    for i, a in enumerate(live):
        for b in live[i + 1:]:
            if tuple(sorted((a['member_id'], b['member_id']))) in past:
                continue
            if pair_status(a, b) == FEASIBLE:
                nbr[a['member_id']].append(b)
                nbr[b['member_id']].append(a)
    order = sorted(range(4), key=lambda j: -abs(model.beta[j + 1]))
    by_id = {m['member_id']: m for m in live}
    cand = []
    for ia, bs in nbr.items():
        a = by_id[ia]
        for b in bs:
            contest = max(len(bs), len(nbr[b['member_id']])) - 1
            if contest < min_contest or ia > b['member_id']:
                continue
            for j in order:
                k = SOFT4[j]
                need = [m for m in (a, b) if m['fields'].get(k) is None]
                if not need or any(m['field_status'].get(k) == 'declined' for m in need):
                    continue
                cand.append((-(contest * abs(model.beta[j + 1])) / len(need), ia, b['member_id'], k,
                             [m['member_id'] for m in need]))
                break
    cand.sort()
    out, seen = [], set()
    for _, _, _, k, ids in cand:
        new = [(i, k) for i in ids if (i, k) not in seen]
        if len(new) > left:
            continue
        for i, f in new:
            seen.add((i, f))
            out.append({'member_id': i, 'field': f})
        left -= len(new)
        if left <= 0:
            break
    return out
