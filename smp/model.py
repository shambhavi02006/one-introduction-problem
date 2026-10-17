"""Outcome-chain model: P(MSMI | a, b) from observable history only.

P(MSMI) = P(both respond) * P(both accept) * P(date) * P(both yes again, on time)

* Directional acceptance: logistic in goal/pace/lifestyle/conversation agreement,
  MAP-fitted online (Gaussian prior around simulator-documentation defaults,
  shrunk member random effects). Unknown soft fields are integrated out under
  the population distribution rather than imputed as a point.
* Both directions share a pair-level shock, handled by 3-point Gauss-Hermite
  quadrature, so P(both accept) is NOT the product of the directional values.
* Response rate: Beta posterior per member. Missing responses are never labelled
  as 'No'; they update only the response-rate term.
* Everything is recomputed from the request, so the policy is stateless and
  only data with observed_day <= today is ever used.
"""
import math

SOFT4 = ['relationship_goal', 'relationship_pace', 'lifestyle', 'conversations']
N_OPT = {'relationship_goal': 2, 'relationship_pace': 3, 'lifestyle': 3, 'conversations': 4}
# prior on logit coefficients: intercept, then agreement slopes (documentation-level defaults)
PRIOR_BETA = [-1.025, 1.05, 0.60, 0.375, 0.30]
PRIOR_SD = 0.6
NEUTRAL_BETA = [-0.5, 0.4, 0.4, 0.4, 0.4]
NEUTRAL_SD = 1.0
TAU = 0.7                       # member random-effect sd
SHOCK_SD = 0.45                 # pair-level shared shock sd
GH = ((0.0, 2 / 3), (math.sqrt(3) * SHOCK_SD, 1 / 6), (-math.sqrt(3) * SHOCK_SD, 1 / 6))
RR_A, RR_B = 8.6, 2.6           # Beta prior on response rate (mean ~0.77)
DATE_RATE = 0.78
ON_TIME = 0.6                   # P(answer within the 3-day window | answers)


def sigmoid(z):
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def _solve(H, g):
    n = len(g)
    A = [row[:] + [g[i]] for i, row in enumerate(H)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(A[r][c]))
        if abs(A[piv][c]) < 1e-12:
            continue
        A[c], A[piv] = A[piv], A[c]
        for r in range(c + 1, n):
            f = A[r][c] / A[c][c]
            if f:
                for k in range(c, n + 1):
                    A[r][k] -= f * A[c][k]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        s = A[r][n] - sum(A[r][k] * x[k] for k in range(r + 1, n))
        x[r] = s / A[r][r] if abs(A[r][r]) > 1e-12 else 0.0
    return x


class Model:
    def __init__(self, state, members_by_id, adapt=True, member_effects=True, hierarchical_rr=True, prior='kit'):
        self.members = members_by_id
        self.day = state.get('day', 0)
        self.adapt = adapt
        self.pm = self._match_probs()
        self.prior = prior
        # 'kit' = coefficients implied by the public kit's documented mechanics; 'neutral' = generic weakly
        # informative prior (same sign for every soft agreement, wide sd) learned online from the episode.
        self.prior_beta = list(PRIOR_BETA) if prior == 'kit' else list(NEUTRAL_BETA)
        self.prior_sd = PRIOR_SD if prior == 'kit' else NEUTRAL_SD
        self.beta = list(self.prior_beta)
        self.u = {}
        self.rr_resp, self.rr_miss = {}, {}
        self.n_samples = 0
        self._cache = {}
        intros = {i['introduction_id']: i for i in state.get('introductions', [])}
        samples = []
        for e in state.get('feedback', []):
            if e.get('event') != 'introduction_response' or e.get('member_id') is None:
                continue
            i = intros.get(e['introduction_id'])
            if i is None:
                continue
            actor = e['member_id']
            if e.get('value') is None:
                if hierarchical_rr:
                    self.rr_miss[actor] = self.rr_miss.get(actor, 0) + 1
                continue
            if hierarchical_rr:
                self.rr_resp[actor] = self.rr_resp.get(actor, 0) + 1
            other = i['user_b'] if i['user_a'] == actor else i['user_a']
            if actor in self.members and other in self.members:
                samples.append((actor, other, 1.0 if e['value'] == 'yes' else 0.0))
        self.n_samples = len(samples)
        if adapt and samples:
            self._fit(samples, member_effects)

    # ---------- population match probabilities
    def _match_probs(self):
        out = {}
        for k in SOFT4:
            vals = [m['fields'][k] for m in self.members.values() if m['fields'].get(k) is not None]
            n = N_OPT[k]
            counts = {}
            for v in vals:
                counts[v] = counts.get(v, 0) + 1
            tot = len(vals) + 4.0
            freqs = [(c + 4.0 / n) / tot for c in counts.values()]
            unseen = n - len(counts)
            out[k] = max(0.05, min(0.95, sum(f * f for f in freqs) + unseen * (4.0 / n / tot) ** 2))
        return out

    def feat_state(self, a, b):
        """Per soft feature: 1 match, 0 mismatch, None unknown."""
        fa, fb = a['fields'], b['fields']
        out = []
        for k in SOFT4:
            x, y = fa.get(k), fb.get(k)
            out.append(None if x is None or y is None else int(x == y))
        return tuple(out)

    def _x(self, st):
        return [1.0] + [float(s) if s is not None else self.pm[k] for s, k in zip(st, SOFT4)]

    # ---------- fitting
    def _fit(self, samples, member_effects):
        data = []
        for actor, other, y in samples:
            st = self.feat_state(self.members[actor], self.members[other])
            data.append((actor, self._x(st), y))
        beta = list(self.prior_beta)
        u = {}
        k = len(beta)
        inv = 1.0 / self.prior_sd ** 2
        for _ in range(3):
            for _ in range(4):
                g = [-(beta[j] - self.prior_beta[j]) * inv for j in range(k)]
                H = [[inv if i == j else 0.0 for j in range(k)] for i in range(k)]
                for actor, x, y in data:
                    z = sum(beta[j] * x[j] for j in range(k)) + u.get(actor, 0.0)
                    p = sigmoid(z)
                    r, w = y - p, p * (1 - p)
                    for i in range(k):
                        g[i] += r * x[i]
                        wi = w * x[i]
                        for j in range(k):
                            H[i][j] += wi * x[j]
                step = _solve(H, g)
                beta = [beta[j] + step[j] for j in range(k)]
            if member_effects:
                num, den = {}, {}
                for actor, x, y in data:
                    p = sigmoid(sum(beta[j] * x[j] for j in range(k)))
                    num[actor] = num.get(actor, 0.0) + (y - p)
                    den[actor] = den.get(actor, 0.0) + p * (1 - p)
                u = {a: num[a] / (den[a] + 1.0 / TAU ** 2) for a in num}
        self.beta, self.u = beta, u

    # ---------- member terms
    def rr_mean(self, i):
        r, m = self.rr_resp.get(i, 0), self.rr_miss.get(i, 0)
        return (RR_A + r) / (RR_A + RR_B + r + m)

    def rr2(self, i):
        r, m = self.rr_resp.get(i, 0), self.rr_miss.get(i, 0)
        a, b = RR_A + r, RR_B + m
        mean = a / (a + b)
        var = a * b / ((a + b) ** 2 * (a + b + 1))
        return mean * mean + var

    # ---------- pair value
    def _core(self, st, ua, ub):
        key = (st, round(ua * 20), round(ub * 20))
        c = self._cache.get(key)
        if c is not None:
            return c
        unk = [j for j, s in enumerate(st) if s is None]
        tot = 0.0
        for mask in range(1 << len(unk)):
            m = [0 if s is None else s for s in st]
            pr = 1.0
            for bit, j in enumerate(unk):
                pj = self.pm[SOFT4[j]]
                if mask >> bit & 1:
                    m[j] = 1
                    pr *= pj
                else:
                    pr *= 1 - pj
            zb = self.beta[0] + sum(self.beta[j + 1] * m[j] for j in range(4))
            c2 = 0.15 + 0.4 * m[0]
            inner = 0.0
            for s, w in GH:
                sc = sigmoid(c2 + s)
                inner += w * sigmoid(zb + ua + s) * sigmoid(zb + ub + s) * sc * sc
            tot += pr * inner
        self._cache[key] = tot
        return tot

    def value(self, a, b):
        st = self.feat_state(a, b)
        ia, ib = a['member_id'], b['member_id']
        core = self._core(st, self.u.get(ia, 0.0), self.u.get(ib, 0.0))
        return self.rr2(ia) * self.rr2(ib) * DATE_RATE * ON_TIME * ON_TIME * core
