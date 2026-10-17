"""H4 check: is a model with a pair-level shared shock better calibrated for 'both said Yes' than the product of
directional probabilities?  Analysis only (never part of the policy).
Protocol: roll out our policy; fit the model on responses observed by day 30 (what the policy would know);
evaluate on introductions assigned after day 30 where BOTH people responded (a missing response is not a label).
Target: both returned Yes by the 7-day deadline, conditional on both responding.
Features come from the final state (post-hoc, same simplification as calibration_h3.py)."""
import json, math, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'experiments'))
from kit import Simulator, generate
from harness import make_actor
from smp.model import Model, SOFT4, GH, sigmoid

def rollout(seed, variant):
    sim = Simulator(generate(seed, 200, 'evaluation', variant)); act = make_actor(('ours', {})); mem = None
    for _ in range(60):
        out, mem = act('ask', sim.observe(), mem); sim.resolve_asks(out)
        out, mem = act('match', sim.observe(), mem); sim.advance(out)
    for _ in range(40): sim.advance([])
    return sim.observe()

def predict(model, a, b):
    """(P(a yes), P(b yes), P(both yes) with shared shock) integrating over unknown soft fields."""
    st = model.feat_state(a, b); unk = [j for j, s in enumerate(st) if s is None]
    ua, ub = model.u.get(a['member_id'], 0.0), model.u.get(b['member_id'], 0.0)
    pa = pb = pj = 0.0
    for mask in range(1 << len(unk)):
        m = [0 if s is None else s for s in st]; pr = 1.0
        for bit, j in enumerate(unk):
            pj_ = model.pm[SOFT4[j]]
            if mask >> bit & 1: m[j] = 1; pr *= pj_
            else: pr *= 1 - pj_
        zb = model.beta[0] + sum(model.beta[j + 1] * m[j] for j in range(4))
        pa += pr * sigmoid(zb + ua); pb += pr * sigmoid(zb + ub)
        pj += pr * sum(w * sigmoid(zb + ua + s) * sigmoid(zb + ub + s) for s, w in GH)
    return pa, pb, pj

def main():
    rows = []
    for variant in ('development', 'shift'):
        for seed in range(2000, 2024):
            state = rollout(seed, variant); members = {m['member_id']: m for m in state['members']}
            early = dict(state); early['feedback'] = [e for e in state['feedback'] if e['observed_day'] <= 30]
            early['introductions'] = [i for i in state['introductions'] if i['assigned_day'] <= 30]
            model = Model(early, members, adapt=True, prior='neutral')
            resp = {}
            for e in state['feedback']:
                if e['event'] == 'introduction_response' and e['value'] in ('yes', 'no'):
                    resp.setdefault(e['introduction_id'], {})[e['member_id']] = e['value']
            for i in state['introductions']:
                r = resp.get(i['introduction_id'], {})
                if i['assigned_day'] <= 30 or len(r) < 2: continue
                a, b = members[i['user_a']], members[i['user_b']]
                pa, pb, pj = predict(model, a, b)
                rows.append((variant, pa * pb, pj, float(all(v == 'yes' for v in r.values()))))
    out = {}
    for variant in ('development', 'shift', 'all'):
        sel = [r for r in rows if variant == 'all' or r[0] == variant]
        res = {'n_both_responded': len(sel), 'observed_both_yes_rate': sum(r[3] for r in sel) / len(sel)}
        for name, idx in (('product_of_directional', 1), ('joint_shared_shock', 2)):
            p = [min(max(r[idx], 1e-6), 1 - 1e-6) for r in sel]
            res[name] = {'mean_predicted': sum(p) / len(p),
                         'log_loss': -sum(r[3] * math.log(q) + (1 - r[3]) * math.log(1 - q) for r, q in zip(sel, p)) / len(p),
                         'brier': sum((q - r[3]) ** 2 for r, q in zip(sel, p)) / len(p)}
        out[variant] = res
        print(variant, json.dumps(res))
    json.dump(out, open(os.path.join(ROOT, 'results', 'calibration_h4.json'), 'w'), indent=2)

if __name__ == '__main__':
    main()
