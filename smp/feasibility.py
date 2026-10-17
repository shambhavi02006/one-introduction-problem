"""Rule-based feasibility layer. Never learned, never overridden by a score.

`pair_status` is a fast early-exit port of the supplied `eligibility()` and is
property-tested against it. `exact_eligibility` is a verbatim copy used only by
the final output validator, so an invalid pair cannot be emitted.
"""
HARD = ['age_min', 'age_max', 'who_to_meet', 'relationship_structure', 'smoking',
        'partner_smoking', 'has_children', 'partner_children', 'wants_children',
        'acceptable_zones', 'schedule']
SOFT = ['relationship_goal', 'relationship_pace', 'lifestyle', 'conversations',
        'emotional_availability', 'space_for_relationship', 'relocate']

INFEASIBLE, NEEDS, FEASIBLE = 'infeasible', 'needs_clarification', 'feasible'


def hard_missing(m):
    f = m['fields']
    return [k for k in HARD if f.get(k) is None]


def is_resolved(m):
    f = m['fields']
    for k in HARD:
        if f.get(k) is None:
            return False
    return True


def has_declined_hard(m):
    s = m['field_status']
    for k in HARD:
        if s.get(k) == 'declined':
            return True
    return False


def known_failure(a, b):
    """True if the information already observed proves the pair infeasible."""
    fa, fb = a['fields'], b['fields']
    for x, y, fx, fy in ((a, b, fa, fb), (b, a, fb, fa)):
        w = fx.get('who_to_meet')
        if w is not None and y['gender'] not in w:
            return True
        v = fx.get('age_min')
        if v is not None and y['age'] < v:
            return True
        v = fx.get('age_max')
        if v is not None and y['age'] > v:
            return True
        z = fx.get('acceptable_zones')
        if z is not None and y['zone'] not in z:
            return True
        if fx.get('partner_smoking') == 'no_smoking' and fy.get('smoking') in ('yes', 'occasionally'):
            return True
        if fx.get('partner_children') == 'no_children' and fy.get('has_children') is True:
            return True
    sa, sb = fa.get('relationship_structure'), fb.get('relationship_structure')
    if sa is not None and sb is not None and sa != sb:
        return True
    if {fa.get('wants_children'), fb.get('wants_children')} == {'yes', 'no'}:
        return True
    ca, cb = fa.get('schedule'), fb.get('schedule')
    if ca is not None and cb is not None and not set(ca) & set(cb):
        return True
    return False


def pair_status(a, b):
    if a['member_id'] == b['member_id'] or a['pool_id'] != b['pool_id']:
        return INFEASIBLE
    if min(a['age'], b['age']) < 18:
        return INFEASIBLE
    if known_failure(a, b):
        return INFEASIBLE
    if is_resolved(a) and is_resolved(b):
        return FEASIBLE
    return NEEDS


def exact_eligibility(a, b):
    """Verbatim copy of kit.eligibility (public pair-level hard checks)."""
    if a['member_id'] == b['member_id']:
        return {'status': 'infeasible', 'reasons': ['same_member']}
    if a['pool_id'] != b['pool_id']:
        return {'status': 'infeasible', 'reasons': ['different_pool']}
    if min(a['age'], b['age']) < 18:
        return {'status': 'infeasible', 'reasons': ['underage']}
    fa, fb = a['fields'], b['fields']
    missing = []
    failures = []
    for member, f in ((a, fa), (b, fb)):
        missing += [member['member_id'] + ':' + k for k in HARD if f.get(k) is None]
    for x, y, fx, fy in ((a, b, fa, fb), (b, a, fb, fa)):
        if fx.get('who_to_meet') is not None and y['gender'] not in fx['who_to_meet']:
            failures.append('who_to_meet')
        if fx.get('age_min') is not None and y['age'] < fx['age_min']:
            failures.append('age')
        if fx.get('age_max') is not None and y['age'] > fx['age_max']:
            failures.append('age')
        if fx.get('acceptable_zones') is not None and y['zone'] not in fx['acceptable_zones']:
            failures.append('geography')
        if fx.get('partner_smoking') == 'no_smoking' and fy.get('smoking') in ('yes', 'occasionally'):
            failures.append('smoking')
        if fx.get('partner_children') == 'no_children' and fy.get('has_children') is True:
            failures.append('children_present')
    if fa.get('relationship_structure') is not None and fb.get('relationship_structure') is not None \
            and fa['relationship_structure'] != fb['relationship_structure']:
        failures.append('relationship_structure')
    if {fa.get('wants_children'), fb.get('wants_children')} == {'yes', 'no'}:
        failures.append('children_plans')
    if fa.get('schedule') is not None and fb.get('schedule') is not None \
            and not set(fa['schedule']) & set(fb['schedule']):
        failures.append('schedule')
    return {'status': 'infeasible' if failures else ('needs_clarification' if missing else 'feasible'),
            'reasons': sorted(set(failures)), 'missing': missing}


def past_pairs(state):
    return {tuple(sorted((i['user_a'], i['user_b']))) for i in state.get('introductions', [])}


def validate_pairs(state, pairs):
    """Drop (never repair) any pair that could make the episode invalid."""
    members = {m['member_id']: m for m in state.get('members', [])}
    past = past_pairs(state)
    used, out = set(), []
    for pair in pairs:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            continue
        a, b = pair
        if a == b or a in used or b in used or a not in members or b not in members:
            continue
        ma, mb = members[a], members[b]
        if not (ma.get('available') and mb.get('available')):
            continue
        if tuple(sorted((a, b))) in past:
            continue
        if exact_eligibility(ma, mb)['status'] != 'feasible':
            continue
        used.update((a, b))
        out.append([a, b])
    return out


def validate_asks(state, asks):
    members = {m['member_id']: m for m in state.get('members', [])}
    budget = state.get('ask_budget_remaining', 0)
    seen, out, cost = set(), [], 0
    for ask in asks:
        i, f = ask.get('member_id'), ask.get('field')
        m = members.get(i)
        if m is None or not m.get('available') or (i, f) in seen:
            continue
        if f != 'constraints' and f not in SOFT:
            continue
        c = 3 if f == 'constraints' else 1
        if cost + c > budget:
            continue
        seen.add((i, f))
        cost += c
        out.append({'member_id': i, 'field': f})
    return out
