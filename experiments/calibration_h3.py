"""H3 check: does online adaptation improve calibration of directional P(Yes), especially under shifted weights?
Protocol (analysis only): run our policy on `variant` seeds, collect all matured directional responses at the end.
Fit on responses observed by day 30 (what the policy would know), score held-out log-loss on responses observed after day 30.
Compares prior-only coefficients (static) with the online MAP fit. Responses are Yes/No only; non-responses are not labels."""
import json, math, os, sys, statistics as st
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'experiments'))
from kit import Simulator, generate
from harness import make_actor
from smp.model import Model, sigmoid

def run(seed, variant):
    sim = Simulator(generate(seed, 200, 'evaluation', variant)); act = make_actor(('ours', {})); mem = None
    for _ in range(60):
        out, mem = act('ask', sim.observe(), mem); sim.resolve_asks(out)
        out, mem = act('match', sim.observe(), mem); sim.advance(out)
    for _ in range(40): sim.advance([])
    return sim.observe()

def loglik(model, state, members, lo, hi):
    intros = {i['introduction_id']: i for i in state['introductions']}
    ll, n, br = 0.0, 0, 0.0
    for e in state['feedback']:
        if e['event'] != 'introduction_response' or e['value'] not in ('yes', 'no') or not (lo < e['observed_day'] <= hi): continue
        i = intros[e['introduction_id']]; a = e['member_id']; b = i['user_b'] if i['user_a'] == a else i['user_a']
        st_ = model.feat_state(members[a], members[b]); x = model._x(st_)
        p = sigmoid(sum(w * xi for w, xi in zip(model.beta, x)) + model.u.get(a, 0.0))
        y = 1.0 if e['value'] == 'yes' else 0.0
        p = min(max(p, 1e-6), 1 - 1e-6); ll += y * math.log(p) + (1 - y) * math.log(1 - p); br += (p - y) ** 2; n += 1
    return ll, br, n

res = {}
for variant in ('development', 'shift'):
    tot = {'static': [0, 0, 0], 'adapted': [0, 0, 0]}
    for seed in range(2000, 2012):
        state = run(seed, variant); members = {m['member_id']: m for m in state['members']}
        early = dict(state); early['feedback'] = [e for e in state['feedback'] if e['observed_day'] <= 30]
        early['introductions'] = [i for i in state['introductions'] if i['assigned_day'] <= 30]
        for name, adapt in (('static', False), ('adapted', True)):
            m = Model(early, members, adapt=adapt, prior='neutral')
            ll, br, n = loglik(m, state, members, 30, 100)
            tot[name][0] += ll; tot[name][1] += br; tot[name][2] += n
    res[variant] = {k: {'held_out_responses': v[2], 'log_loss': -v[0] / v[2], 'brier': v[1] / v[2]} for k, v in tot.items()}
    print(variant, json.dumps(res[variant]))
json.dump(res, open(os.path.join(ROOT, 'results', 'calibration_h3.json'), 'w'), indent=2)
