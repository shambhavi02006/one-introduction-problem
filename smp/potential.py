"""Potential-feasibility q_ab: P(pair becomes feasible once both answer).

Product of per-constraint pass probabilities for the constraints that are still
unresolved. Known failures give q = 0 (checked by the caller via known_failure).
Priors are structural frequencies of the public synthetic generator, then
re-estimated from the members observed in the current state so that a changed
world (for example sparse geography) is picked up without re-training.
"""
GENDERS = ['woman', 'man', 'non_binary']


def _age_pass(d):
    # P(U >= d) for U uniform on {3..10}
    if d <= 3:
        return 1.0
    if d > 10:
        return 0.0
    return (11 - d) / 8.0


def _frac(count, n, prior, strength=6.0):
    return (count + prior * strength) / (n + strength)


class Potential:
    def __init__(self, members, neutral=False, empirical_age=False):
        """neutral=True: generic weakly-informative priors (0.5, strength 2) instead of the public generator's
        structural frequencies; estimates then come almost entirely from the members observed in the state."""
        self.neutral = neutral
        self.empirical_age = neutral and empirical_age
        f = [m['fields'] for m in members]
        _pr = (lambda v: 0.5) if neutral else (lambda v: v)
        _frac = (lambda c, n, pr, strength=2.0: (c + pr * strength) / (n + strength)) if neutral else globals()['_frac']
        wtm = [x['who_to_meet'] for x in f if x.get('who_to_meet') is not None]
        self.pg = {g: _frac(sum(g in w for w in wtm), len(wtm), _pr(0.4667)) for g in GENDERS}
        smk = [x['smoking'] for x in f if x.get('smoking') is not None]
        self.p_smoker = _frac(sum(s in ('yes', 'occasionally') for s in smk), len(smk), _pr(0.25))
        ps = [x['partner_smoking'] for x in f if x.get('partner_smoking') is not None]
        self.p_req_nosmoke = _frac(sum(s == 'no_smoking' for s in ps), len(ps), _pr(0.5))
        hc = [x['has_children'] for x in f if x.get('has_children') is not None]
        self.p_kids = _frac(sum(bool(h) for h in hc), len(hc), _pr(0.15))
        pc = [x['partner_children'] for x in f if x.get('partner_children') is not None]
        self.p_req_nokids = _frac(sum(s == 'no_children' for s in pc), len(pc), _pr(0.5))
        st = [x['relationship_structure'] for x in f if x.get('relationship_structure') is not None]
        self.p_mono = _frac(sum(s == 'monogamous' for s in st), len(st), _pr(0.9))
        wc = [x['wants_children'] for x in f if x.get('wants_children') is not None]
        self.p_wc = {v: _frac(sum(s == v for s in wc), len(wc), 1 / 3) for v in ('yes', 'no', 'unsure')}
        # neutral mode: age-window pass probability estimated from the observed members' own stated windows
        self._gaps = []
        if self.empirical_age:
            for m in members:
                x = m['fields']
                if x.get('age_min') is not None:
                    self._gaps.append(m['age'] - x['age_min'])
                if x.get('age_max') is not None:
                    self._gaps.append(x['age_max'] - m['age'])
        zones = {m['zone'] for m in members}
        obs = [(m['zone'], m['fields']['acceptable_zones']) for m in members
               if m['fields'].get('acceptable_zones') is not None]
        cross = sum(len([z for z in az if z != zone]) for zone, az in obs)
        self.p_cross = (cross + 0.1) / (len(obs) * max(1, len(zones) - 1) + 6.0)

    def _age(self, d):
        """P(partner's age is within a window with gap d). Kit mode: structural prior. Neutral mode: empirical
        distribution of the observed members' own stated windows, smoothed towards 0.5 (no simulator constants)."""
        if not self.empirical_age:
            return 0.5 if self.neutral else _age_pass(d)
        n = len(self._gaps)
        return (sum(g >= d for g in self._gaps) + 1.0) / (n + 2.0)

    def _disjoint(self, k):
        if self.neutral:
            return 0.3
        return {1: 1 / 3, 2: 1 / 9, 3: 0.0}.get(k, 0.0)

    def q(self, a, b):
        p = 1.0
        fa, fb = a['fields'], b['fields']
        for x, y, fx, fy in ((a, b, fa, fb), (b, a, fb, fa)):
            if fx.get('who_to_meet') is None:
                p *= self.pg[y['gender']]
            if fx.get('age_min') is None:
                p *= self._age(x['age'] - y['age'])
            if fx.get('age_max') is None:
                p *= self._age(y['age'] - x['age'])
            if fx.get('acceptable_zones') is None and x['zone'] != y['zone']:
                p *= self.p_cross
            ys = fy.get('smoking')
            smokes = (1.0 if ys in ('yes', 'occasionally') else 0.0) if ys is not None else self.p_smoker
            ps = fx.get('partner_smoking')
            if ps is None:
                p *= 1.0 - self.p_req_nosmoke * smokes
            elif ps == 'no_smoking':
                p *= 1.0 - smokes
            yc = fy.get('has_children')
            kids = (1.0 if yc else 0.0) if yc is not None else self.p_kids
            pc = fx.get('partner_children')
            if pc is None:
                p *= 1.0 - self.p_req_nokids * kids
            elif pc == 'no_children':
                p *= 1.0 - kids
        sa, sb = fa.get('relationship_structure'), fb.get('relationship_structure')
        if sa is None and sb is None:
            p *= self.p_mono ** 2 + (1 - self.p_mono) ** 2
        elif sa is None or sb is None:
            known = sa if sa is not None else sb
            p *= self.p_mono if known == 'monogamous' else 1 - self.p_mono
        wa, wb = fa.get('wants_children'), fb.get('wants_children')
        if wa is None and wb is None:
            p *= 1 - 2 * self.p_wc['yes'] * self.p_wc['no']
        elif wa is None or wb is None:
            known = wa if wa is not None else wb
            if known == 'yes':
                p *= 1 - self.p_wc['no']
            elif known == 'no':
                p *= 1 - self.p_wc['yes']
        ca, cb = fa.get('schedule'), fb.get('schedule')
        if ca is None and cb is None:
            p *= 0.7 if self.neutral else 1 - 4 / 27
        elif ca is None or cb is None:
            known = ca if ca is not None else cb
            p *= 1 - self._disjoint(len(set(known)))
        return p
