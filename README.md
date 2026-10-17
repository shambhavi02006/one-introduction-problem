# The One Introduction Problem — Round 2 build

A reproducible, stdlib-only decision policy for the Vouchsafe sequential reciprocal matching simulator
(kit v1.0.0). One process per invocation, JSON on stdin/stdout, memory carried explicitly.

## What the policy does (one paragraph per layer, each its own module in `smp/`)

| Module | Role |
|---|---|
| `feasibility.py` | Hard rules. Fast port of the supplied `eligibility()` (property-tested against it) plus a verbatim copy used by the final **output validator**, which *drops* any ask/pair that could invalidate the episode. Never learned, never overridden. |
| `potential.py` | `q_ab`: probability a pair becomes feasible once both answer (product of pass-rates of the *unresolved* constraints, estimated from the members observed in the current state with generic 0.5 priors; the age-window pass rate is the empirical distribution of observed members' own windows). `q = 0` for known failures; declined members are never asked. |
| `model.py` | Outcome chain `P(respond)·P(accept)·P(date)·P(yes again, on time)`. Directional acceptance is a logistic model on goal/pace/lifestyle/conversation agreement, **MAP-fitted online** from matured responses with shrunk member effects, starting from a generic weakly-informative prior (all soft agreements help, wide sd); unknown soft fields are integrated out (not imputed); both directions share a pair-level shock (quadrature), so P(both accept) is not a product of independents. Response rate is a per-member Beta posterior; a missing response only updates that term and is never a "No". |
| `clarify.py` | Value-of-information asks: 3-unit constraint bundles go to the members whose answers unlock the most pair value (pair-aware: two unresolved mutual best partners are asked the same day). Spare units buy 1-unit soft asks only on contested edges. |
| `allocate.py` | Global maximum-weight matching on the feasible graph (general graph, not bipartite): exact bitmask DP on small components, Edmonds' blossom (`networkx`, optional) on large ones, greedy last resort. Small first-introduction bonus. |
| `policy.py`, `cli.py` | Orchestration, 6 s time guard (falls back to the supplied greedy), last-resort fallbacks (greedy, then an empty action — always valid). |

The policy is **stateless**: everything is recomputed from the request, so only information with
`observed_day <= today` can be used. Memory is a ~40-byte dict.

## Prior options (`prior` in `SMP_CONFIG`)

| value | meaning |
|---|---|
| `neutral_emp` (**submitted default**) | Generic priors only. Nothing is taken from the constants inside `kit.py`; everything starts weak and is learned from the observable state / the episode's own feedback. |
| `neutral` | As above, but flat 0.5 age-window pass rate. |
| `kit` | Priors equal to the public kit's documented mechanics (e.g. the 0.7 relationship-goal weight). Scored ~0.009 higher on the expected-MSMI diagnostic (about 2%, far below seed noise), but it starts from the simulator's own constants, which the problem statement says is "not an oracle for the policy". Kept only as a reported comparison row. |

## Run it

```bash
python -m unittest discover -s tests -v                  # 23 validity / robustness / provenance tests (stdlib only)

# official evaluator, trusted local mode (this is what the organisers run, in a container, on private seeds)
python evaluate.py --policy policy.py  --baseline greedy  --seeds 101,102,103 --variants all --output results/official_greedy.json
python evaluate.py --policy policy.py  --baseline no_asks --seeds 101,102,103 --variants all --output results/official_no_asks.json
python evaluate.py --policy policy.py  --baseline random  --seeds 101,102,103 --variants all --output results/official_random.json
python evaluate.py --policy run_ours.py                    --seeds 101,102,103 --variants all --output results/official_ours.json
#   (run_ours.py ignores evaluate.py's mandatory --baseline flag and always runs our policy)

# ablations through the official evaluator: set SMP_CONFIG
SMP_CONFIG='{"asks":"none"}' python evaluate.py --policy run_ours.py --seeds 101,102,103 --variants all --output results/official_abl_no_clarification.json

# fast in-process harness (identical loop, plus analysis-only diagnostics)
python experiments/harness.py --policy ours --seeds 3000-3019 --variants all --out results/test_ours.json
python experiments/make_tables.py test_                  # -> results/test_summary.{md,json}
```

Ablation switches (`SMP_CONFIG` / `--cfg`): `prior` = `neutral_emp|neutral|kit`, `asks` = `voi|list|none`, `alloc` = `blossom|greedy`, `adapt` (online model),
`soft_asks`, `eps_first`, `lam` (reservation values; off by default — see report), `soft_min_contest`.

## Container

```bash
docker build -t smp-policy .
python evaluate.py --image smp-policy --seeds 101,102,103 --variants all --output results/container.json
```
`--image` runs the container with the organisers' limits (no network, 2 CPUs, 1 GiB, read-only, uid 65534).
**Not verified in the authoring sandbox (it has the Docker CLI but no daemon) — run the two commands above once and keep the output. Everything else (23 tests, official `evaluate.py` in trusted-local mode, in-process harness) was run.**
Dockerfile pre-compiles bytecode because the evaluation container is read-only.

## Reproducibility declaration

* Training seeds: **none** — there are no trained assets. Model priors are fixed constants (documented in `smp/model.py`) and are updated online inside an episode from the episode's own feedback.
* Inference random seed: **none** — the policy uses no randomness; output is a pure function of the request (tested across `PYTHONHASHSEED` values). The `random` baseline seeds from `(day, #members)`.
* Seed hygiene: all tuning decisions (including the choice of `neutral_emp` as default) used validation seeds 2000–2019 only. Held-out batch A (seeds 3000–3019, `results/test_*`) was produced with the earlier `kit`-prior configuration. Held-out batch B (seeds 3020–3119, `results/test2_*`) was produced with the final configuration after it was frozen and is the evidence reported in `REPORT.md`. Public seeds 101–103 are used for the official-evaluator run.
* Dependencies: none required. `networkx==3.6.1` (BSD-3-Clause, licence text in `LICENSE-networkx.txt`) is optional and pinned in `requirements.txt`.
* Baselines: the starter `policy.py` was not available to us, so greedy / no_asks / random-feasible are re-implemented in `smp/baselines.py` from `kit.baseline_asks` / `kit.baseline_match` (random-feasible = greedy asks + random-order maximal feasible matching). If the organisers' random baseline differs, only that comparator changes.

## Attribution

`kit.py`, `evaluate.py` and the problem statement are the organisers' starter material (`docs/PROBLEM_STATEMENT.md`).
`smp/baselines.py` and `smp/feasibility.exact_eligibility` copy logic from `kit.py` to mirror the supplied behaviour.
Coding assistance: Claude (Anthropic) was used to write and test this code. No external datasets, pretrained models or paid services.
Add your own team licence before publishing; none is chosen here.

## Results and report

`REPORT.md` is the technical report (assumptions, experiments, ablations, failure analysis, limitations).
Machine-readable results: `results/final_summary.json`, `results/official_*.json`, `results/test2_*.json`; human-readable tables: `results/final_tables.md`.
Regenerate the tables with `python experiments/final_tables.py`.
