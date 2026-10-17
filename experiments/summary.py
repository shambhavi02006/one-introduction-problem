"""Summaries and paired comparisons. Usage: summary.py A.json [B.json ...]  (first file = reference)"""
import json
import random
import statistics as st
import sys
from collections import defaultdict

KEYS = ['msmi_per_100_arrived_members', 'expected_msmi_per_100', 'coverage', 'mutual_acceptances_per_100',
        'assignments', 'edge_utilisation', 'ask_cost']


def load(path):
    d = json.load(open(path))
    return d, {(r['variant'], r['seed']): r for r in d['rows'] if r['valid']}


def family_means(rows, key):
    fam = defaultdict(list)
    for (v, _), r in rows.items():
        fam[v].append(r[key])
    return {v: st.mean(x) for v, x in fam.items()}


def overall(rows, key):
    f = family_means(rows, key)
    return st.mean(f.values()) if f else float('nan')


def boot_ci(diffs, n=2000, seed=1):
    rng = random.Random(seed)
    m = [st.mean(rng.choices(diffs, k=len(diffs))) for _ in range(n)]
    m.sort()
    return m[int(.025 * n)], m[int(.975 * n)]


def main(paths):
    ref_d, ref = load(paths[0])
    for path in paths:
        d, rows = load(path)
        label = d['policy'] + (' ' + json.dumps(d['cfg'], sort_keys=True) if d['cfg'] else '')
        print('==', path, label, '| episodes', len(rows), '| invalid', len(d['rows']) - len(rows))
        print('  ' + '  '.join('%s=%.3f' % (k.split('_')[0] + ('_' + k.split('_')[1] if k.startswith(('msmi', 'expected', 'mutual', 'edge')) else ''), overall(rows, k)) for k in KEYS))
        fm = family_means(rows, 'msmi_per_100_arrived_members')
        fe = family_means(rows, 'expected_msmi_per_100')
        print('  per-family MSMI/100 (expected): ' + '  '.join('%s %.2f(%.2f)' % (v[:5], fm[v], fe[v]) for v in sorted(fm)))
        if path != paths[0]:
            common = sorted(set(rows) & set(ref))
            for key in ('msmi_per_100_arrived_members', 'expected_msmi_per_100'):
                # paired per-seed difference, averaged within family then across families (matches the ranking score)
                fam = defaultdict(list)
                for k in common:
                    fam[k[0]].append(rows[k][key] - ref[k][key])
                diffs = [x for v in fam.values() for x in v]
                fmean = st.mean(st.mean(v) for v in fam.values())
                lo, hi = boot_ci(diffs)
                print('  paired diff vs ref [%s]: %+.3f  (pooled-seed 95%% CI %+.3f..%+.3f, n=%d)' % (key[:12], fmean, lo, hi, len(diffs)))


if __name__ == '__main__':
    main(sys.argv[1:])
