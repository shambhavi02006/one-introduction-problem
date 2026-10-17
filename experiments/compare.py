"""Paired comparison of two harness result files (same seeds/variants).
usage: python experiments/compare.py A.json B.json [label_a label_b]
Score = organiser rule (mean over seeds within variant, then mean over the six variants).
Bootstrap CI resamples seeds within each variant (paired), 95%. expected_msmi is an analysis-only diagnostic."""
import json, random, statistics as st, sys
from collections import defaultdict
KEYS = ['msmi_per_100_arrived_members', 'expected_msmi_per_100', 'assignments', 'mutual_acceptances_per_100',
        'coverage', 'edge_utilisation', 'ask_cost']

def load(p):
    return {(r['variant'], r['seed']): r for r in json.load(open(p))['rows'] if r['valid']}

def score(rows, key):
    f = defaultdict(list)
    for (v, s), r in rows.items():
        f[v].append(r[key])
    return st.mean(st.mean(x) for x in f.values())

def paired(a, b, key, n=3000, seed=11):
    keys = sorted(set(a) & set(b)); fam = defaultdict(list)
    for k in keys:
        fam[k[0]].append(a[k][key] - b[k][key])
    d = st.mean(st.mean(x) for x in fam.values())
    rnd = random.Random(seed); boots = []
    for _ in range(n):
        boots.append(st.mean(st.mean(rnd.choices(x, k=len(x))) for x in fam.values()))
    boots.sort()
    return d, boots[int(.025 * n)], boots[int(.975 * n)]

if __name__ == '__main__':
    A, B = load(sys.argv[1]), load(sys.argv[2])
    la, lb = (sys.argv[3], sys.argv[4]) if len(sys.argv) > 4 else ('A', 'B')
    print('episodes', len(A), len(B), '| common', len(set(A) & set(B)))
    print('%-30s %9s %9s %9s  %s' % ('metric (family-mean)', la, lb, 'A-B', '95% CI (paired bootstrap)'))
    for k in KEYS:
        d, lo, hi = paired(A, B, k)
        print('%-30s %9.3f %9.3f %+9.3f  [%+.3f, %+.3f]' % (k, score(A, k), score(B, k), d, lo, hi))
