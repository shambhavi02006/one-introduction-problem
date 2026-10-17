"""Build machine-readable + markdown result tables from results/test_*.json (held-out seeds).
Primary score follows the organisers' rule: mean over episodes within each variant family, then mean over families.
Paired statistics: per-seed differences, bootstrap over seeds within family (family-mean difference), Wilcoxon signed-rank."""
import glob, json, os, random, statistics as st, sys
from collections import defaultdict
try:
    from scipy.stats import wilcoxon
except Exception:  # analysis-only dependency
    wilcoxon = None

R = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results')
PREFIX = sys.argv[1] if len(sys.argv) > 1 else 'test_'
KEYS = ['msmi_per_100_arrived_members', 'coverage', 'mutual_acceptances_per_100', 'ask_cost', 'assignments',
        'dates', 'missing_feedback', 'expected_msmi_per_100', 'edge_utilisation', 'unserved_members']


def load():
    out = {}
    for f in sorted(glob.glob(os.path.join(R, PREFIX + '*.json'))):
        name = os.path.basename(f)[len(PREFIX):-5]
        d = json.load(open(f))
        out[name] = {(r['variant'], r['seed']): r for r in d['rows']}
        out[name]['_invalid'] = sum(not r['valid'] for r in d['rows'])
    return out


def fam_mean(rows, key):
    fam = defaultdict(list)
    for k, r in rows.items():
        if k != '_invalid' and r['valid']:
            fam[k[0]].append(r[key])
    return {v: st.mean(x) for v, x in fam.items()}


def score(rows, key):
    f = fam_mean(rows, key)
    return st.mean(f.values())


def paired(a, b, key, n=4000, seed=7):
    """a - b; returns family-averaged mean diff, bootstrap CI, wilcoxon p (pooled per-seed diffs)."""
    common = sorted(k for k in a if k != '_invalid' and k in b)
    fam = defaultdict(list)
    for k in common:
        fam[k[0]].append(a[k][key] - b[k][key])
    mean = st.mean(st.mean(v) for v in fam.values())
    rng = random.Random(seed)
    boots = sorted(st.mean(st.mean(rng.choices(v, k=len(v))) for v in fam.values()) for _ in range(n))
    diffs = [x for v in fam.values() for x in v]
    p = None
    if wilcoxon and any(d != 0 for d in diffs):
        try:
            p = float(wilcoxon(diffs).pvalue)
        except Exception:
            p = None
    return mean, boots[int(.025 * n)], boots[int(.975 * n)], p


def main():
    data = load()
    if 'ours' not in data:
        sys.exit('no ours result')
    summary = {'policies': {}, 'paired': {}, 'per_variant': {}, 'waits': {}, 'non_service': {}}
    for name, rows in data.items():
        n = len([k for k in rows if k != '_invalid'])
        summary['policies'][name] = {'episodes': n, 'invalid': rows['_invalid'],
                                     **{k: score(rows, k) for k in KEYS}}
        summary['per_variant'][name] = {k: fam_mean(rows, k) for k in ('msmi_per_100_arrived_members', 'expected_msmi_per_100')}
    for name in data:
        if name in ('ours',):
            continue
        summary['paired'][name + ' -> ours minus it'] = {}
        for key in ('msmi_per_100_arrived_members', 'expected_msmi_per_100', 'assignments', 'mutual_acceptances_per_100'):
            m, lo, hi, p = paired(data['ours'], data[name], key)
            summary['paired'][name + ' -> ours minus it'][key] = {'diff': m, 'ci95': [lo, hi], 'wilcoxon_p': p}
    for name in ('ours', 'greedy'):
        if name not in data:
            continue
        w = defaultdict(list); ns = defaultdict(lambda: defaultdict(list))
        for k, r in data[name].items():
            if k == '_invalid':
                continue
            w[k[0]] += r['waits']
            for f in ('arrived_members', 'served_members', 'unserved_members', 'unserved_declined_hard',
                      'unserved_no_feasible_partner', 'unserved_policy_or_capacity'):
                ns[k[0]][f].append(r[f])
        summary['waits'][name] = {v: {'median_wait_days': st.median(x) if x else None,
                                      'p90_wait_days': sorted(x)[int(.9 * len(x))] if x else None} for v, x in w.items()}
        summary['non_service'][name] = {v: {f: st.mean(x) for f, x in d.items()} for v, d in ns.items()}
    json.dump(summary, open(os.path.join(R, PREFIX + 'summary.json'), 'w'), indent=2)

    L = []
    order = [n for n in ('ours', 'greedy', 'no_asks', 'random') if n in data] + sorted(n for n in data if n not in ('ours', 'greedy', 'no_asks', 'random'))
    L.append('### Overall (organiser scoring rule: mean of six family means; 20 seeds/family)\n')
    L.append('| policy | eps | invalid | **MSMI/100** | expected-MSMI/100 (diag.) | coverage | mutual acc/100 | assignments | ask cost |')
    L.append('|---|---|---|---|---|---|---|---|---|')
    for n in order:
        s = summary['policies'][n]
        L.append('| %s | %d | %d | **%.3f** | %.3f | %.3f | %.2f | %.1f | %.0f |' % (n, s['episodes'], s['invalid'], s['msmi_per_100_arrived_members'],
                 s['expected_msmi_per_100'], s['coverage'], s['mutual_acceptances_per_100'], s['assignments'], s['ask_cost']))
    L.append('\n### Per scenario family: MSMI/100 (expected-MSMI diagnostic)\n')
    fams = ['development', 'sparse', 'cold_start', 'delayed', 'shift', 'drift']
    L.append('| policy | ' + ' | '.join(fams) + ' |'); L.append('|---|' + '---|' * len(fams))
    for n in order:
        pv = summary['per_variant'][n]
        L.append('| %s | ' % n + ' | '.join('%.2f (%.2f)' % (pv['msmi_per_100_arrived_members'][f], pv['expected_msmi_per_100'][f]) for f in fams) + ' |')
    L.append('\n### Paired differences: ours minus comparator (positive = ours better)\n')
    L.append('| comparator | metric | diff | 95% CI (bootstrap over seeds) | Wilcoxon p |'); L.append('|---|---|---|---|---|')
    for n, d in summary['paired'].items():
        for key, v in d.items():
            L.append('| %s | %s | %+.3f | %+.3f … %+.3f | %s |' % (n.split(' ->')[0], key.replace('_per_100_arrived_members', '/100').replace('_per_100', '/100'), v['diff'], v['ci95'][0], v['ci95'][1], 'n/a' if v['wilcoxon_p'] is None else '%.3f' % v['wilcoxon_p']))
    L.append('\n### Who is not served (mean per episode, ours)\n')
    L.append('| family | arrived | served | unserved | declined a hard field | no feasible partner exists | policy/capacity |'); L.append('|---|---|---|---|---|---|---|')
    for f in fams:
        d = summary['non_service']['ours'][f]
        L.append('| %s | %.0f | %.1f | %.1f | %.1f | %.1f | %.1f |' % (f, d['arrived_members'], d['served_members'], d['unserved_members'], d['unserved_declined_hard'], d['unserved_no_feasible_partner'], d['unserved_policy_or_capacity']))
    L.append('\n### First-introduction waiting time, days from arrival (pooled over served members)\n')
    L.append('| family | ours median / p90 | greedy median / p90 |'); L.append('|---|---|---|')
    for f in fams:
        o = summary['waits']['ours'][f]; g = summary['waits'].get('greedy', {}).get(f, {'median_wait_days': float('nan'), 'p90_wait_days': float('nan')})
        L.append('| %s | %s / %s | %s / %s |' % (f, o['median_wait_days'], o['p90_wait_days'], g['median_wait_days'], g['p90_wait_days']))
    open(os.path.join(R, PREFIX + 'summary.md'), 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
