"""Build results/final_tables.md (+ results/final_summary.json) from result files only. No hand-typed numbers.
Sections: official evaluator (public seeds), held-out batch B (seeds 3020-3119), invalid-episode audit."""
import glob, json, os, statistics as st
from collections import defaultdict
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); R = os.path.join(ROOT, 'results')
import sys; sys.path.insert(0, os.path.join(ROOT, 'experiments'))
from compare import load, score, paired

L = []
# ---- official evaluator on public seeds
L.append('### A. Official `evaluate.py`, public seeds 101-103, all six variants (18 episodes per policy)\n')
L.append('| policy | eligible | invalid | primary score | coverage | mutual acc/100 | ask cost | inference s/episode |')
L.append('|---|---|---|---|---|---|---|---|')
for n in ('ours', 'greedy', 'random', 'no_asks'):
    f = os.path.join(R, 'official_%s.json' % n)
    if not os.path.exists(f): continue
    d = json.load(open(f)); s = d['summary']; o = s.get('overall', {})
    inv = sum(not e['valid'] for e in d['episodes'])
    L.append('| %s | %s | %d/%d | %.3f | %.3f | %.2f | %.0f | %.1f |' % (n, s['eligible'], inv, len(d['episodes']), s['primary_score'] or 0,
             o.get('coverage', 0), o.get('mutual_acceptances_per_100', 0), o.get('ask_cost', 0), o.get('inference_seconds', 0)))
L.append('')
L.append('Per-family primary score (public seeds):\n')
fams = ['development', 'sparse', 'cold_start', 'delayed', 'shift', 'drift']
L.append('| policy | ' + ' | '.join(fams) + ' |'); L.append('|---|' + '---|' * len(fams))
for n in ('ours', 'greedy', 'random', 'no_asks'):
    f = os.path.join(R, 'official_%s.json' % n)
    if os.path.exists(f):
        sm = json.load(open(f))['summary']['scenario_means']
        L.append('| %s | ' % n + ' | '.join('%.2f' % sm[v]['msmi_per_100_arrived_members'] for v in fams) + ' |')
L.append('')

# ---- held-out batch B
files = {os.path.basename(p)[len('test2_'):-5]: load(p) for p in sorted(glob.glob(os.path.join(R, 'test2_*.json')))}
raw_invalid = {os.path.basename(p)[len('test2_'):-5]: sum(not r['valid'] for r in json.load(open(p))['rows']) for p in glob.glob(os.path.join(R, 'test2_*.json'))}
order = [n for n in ('ours', 'greedy', 'random', 'no_asks', 'abl_list_order_asks', 'abl_greedy_allocation', 'ours_kit_prior', 'ours_neutral_prior') if n in files]
L.append('### B. Held-out batch, seeds 3020-3119 (100 per family, 600 episodes per policy; never used for tuning)\n')
L.append('Primary score = mean over seeds within each family, then mean of the six families (organiser rule). `expected MSMI` is an analysis-only diagnostic from the simulator latent values (not available to a policy).\n')
L.append('| policy | invalid | **MSMI/100** | expected MSMI/100 (diag.) | coverage | mutual acc/100 | assignments | edge utilisation | ask cost |')
L.append('|---|---|---|---|---|---|---|---|---|')
for n in order:
    r = files[n]
    L.append('| %s | %d | **%.3f** | %.3f | %.3f | %.2f | %.1f | %.3f | %.0f |' % (n, raw_invalid[n], score(r, 'msmi_per_100_arrived_members'),
             score(r, 'expected_msmi_per_100'), score(r, 'coverage'), score(r, 'mutual_acceptances_per_100'), score(r, 'assignments'),
             score(r, 'edge_utilisation'), score(r, 'ask_cost')))
L.append('')
L.append('Per-family MSMI/100 (diagnostic expected MSMI in parentheses):\n')
L.append('| policy | ' + ' | '.join(fams) + ' |'); L.append('|---|' + '---|' * len(fams))
for n in order:
    cells = []
    for v in fams:
        rows = [r for (vv, s), r in files[n].items() if vv == v]
        cells.append('%.2f (%.2f)' % (st.mean(r['msmi_per_100_arrived_members'] for r in rows), st.mean(r['expected_msmi_per_100'] for r in rows)))
    L.append('| %s | ' % n + ' | '.join(cells) + ' |')
L.append('')
L.append('Paired differences, ours minus comparator (same 600 world seeds; 95% bootstrap CI resampling seeds within family):\n')
L.append('| comparator | MSMI/100 diff [95% CI] | expected-MSMI diff [95% CI] | assignments diff | mutual acc/100 diff | coverage diff |')
L.append('|---|---|---|---|---|---|')
summ = {}
for n in order:
    if n == 'ours': continue
    cells = []
    for k in ('msmi_per_100_arrived_members', 'expected_msmi_per_100', 'assignments', 'mutual_acceptances_per_100', 'coverage'):
        d, lo, hi = paired(files['ours'], files[n], k)
        summ.setdefault(n, {})[k] = [d, lo, hi]
        cells.append('%+.3f [%+.3f, %+.3f]' % (d, lo, hi) if k in ('msmi_per_100_arrived_members', 'expected_msmi_per_100') else '%+.3f' % d)
    L.append('| %s | ' % n + ' | '.join(cells) + ' |')
L.append('')
L.append('Who is not served (ours, mean members per 200-member episode):\n')
L.append('| family | served | unserved | declined a hard field | no feasible partner exists | policy/capacity |'); L.append('|---|---|---|---|---|---|')
for v in fams:
    rows = [r for (vv, s), r in files['ours'].items() if vv == v]
    m = lambda k: st.mean(r[k] for r in rows)
    L.append('| %s | %.1f | %.1f | %.1f | %.1f | %.1f |' % (v, m('served_members'), m('unserved_members'), m('unserved_declined_hard'), m('unserved_no_feasible_partner'), m('unserved_policy_or_capacity')))
L.append('')
L.append('First-introduction wait, days from arrival (pooled over served members):\n')
L.append('| family | ours median / p90 | greedy median / p90 |'); L.append('|---|---|---|')
def wq(pol, v):
    w = sorted(x for (vv, s), r in files[pol].items() if vv == v for x in r['waits'])
    return '%d / %d' % (w[len(w) // 2], w[int(.9 * (len(w) - 1))])
for v in fams: L.append('| %s | %s | %s |' % (v, wq('ours', v), wq('greedy', v)))
L.append('')
mx = max(r['max_call_seconds'] for r in files['ours'].values())
L.append('Slowest single policy call in the 600 final-config episodes (in-process, excludes interpreter start): **%.2f s** (limit 10 s).\n' % mx)

# ---- audit of invalid episodes across every result file
tot = bad = 0
for p in glob.glob(os.path.join(R, '**', '*.json'), recursive=True):
    try: d = json.load(open(p))
    except Exception: continue
    rows = d.get('rows') or d.get('episodes')
    if isinstance(rows, list) and rows and isinstance(rows[0], dict) and 'valid' in rows[0]:
        tot += len(rows); bad += sum(not r['valid'] for r in rows)
L.append('### C. Invalid-episode audit\n')
L.append('Across every result file in `results/` (all policies, ablations, seeds, official and in-process): **%d episodes, %d invalid**.\n' % (tot, bad))
open(os.path.join(R, 'final_tables.md'), 'w').write('\n'.join(L) + '\n')
json.dump({'paired_ours_minus': summ, 'episodes_audited': tot, 'invalid': bad}, open(os.path.join(R, 'final_summary.json'), 'w'), indent=2)
print('wrote results/final_tables.md', tot, bad)
