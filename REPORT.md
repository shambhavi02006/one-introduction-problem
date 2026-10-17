# The One Introduction Problem — Round 2 Technical Report

Sequential reciprocal matching under uncertainty · spec 1.0.0 · kit 1.0.0 · 17 October 2026
Team: _(fill in team name and members)_ · Repository / commit: _(fill in 40-character SHA)_

All numbers below are produced by scripts in `experiments/` from the files in `results/` (see §8). Nothing in
this report is hand-estimated. The simulator is synthetic; none of these numbers say anything about real people.

---

## 1. Summary

We built a stdlib-only decision policy (`policy.py` + `smp/`) that implements the two-phase JSON protocol. It never
emits an invalid action by construction: a validator that mirrors the supplied `eligibility()` drops, never repairs,
anything that could invalidate an episode.

What the evidence supports, and what it does not:

1. **Validity.** 0 invalid episodes out of 7,842 run across every policy, ablation, seed and variant in this
   project (official evaluator and in-process harness). 23 unit tests pass. Slowest policy call over the 600 final-config
   episodes: 0.12 s in-process; in a separate spot check of fresh processes (including interpreter start-up) the
   worst sampled call took 0.09 s with 17 MB peak memory (limits: 10 s, 1 GiB).
2. **Clarification is the only large effect.** Removing it cuts MSMI from 0.376 to 0.100 per 100 arrived members
   (paired difference +0.276, 95% CI +0.241 to +0.310) and cuts assignments from 74.9 to 21.3 per episode.
3. **We cannot show a significant primary-score advantage over the supplied greedy baseline.** On 600 paired
   held-out episodes the difference is +0.010 (95% CI −0.031 to +0.052). A lower-noise analysis diagnostic
   (expected MSMI computed from simulator latent values; not available to a policy) shows a small edge of
   +0.014 (CI +0.009 to +0.018), about 3.9%. First introductions arrive sooner: median wait 2 days against 4.
4. **Our main Round 1 hypothesis (H1, hub utilisation) was not supported.** Edge utilisation is 0.833 for our policy
   and 0.828 for greedy, not the predicted 90% against 78%. Untried feasible pairs are blocked by hub capacity,
   not by idle time (§6.4).
5. **The score is dominated by chance.** With about 0.4 qualifying pairs per 100 members, one episode usually has
   0–2 qualifying pairs. The same policy scored 0.444 and 0.306 on the 18 public-seed episodes under two settings
   that are equivalent in expectation (§5.1).
6. **Priors are generic.** Our model's starting priors do **not** use constants copied from `kit.py` (§3.3).
7. **Not verified here:** container mode. The authoring sandbox has the Docker CLI but no daemon. See §8.

---

## 2. System

Each layer is a separate module, as Section 15 of the problem statement asks.

| Module | Role |
|---|---|
| `smp/feasibility.py` | Hard rules, never learned. Fast port of the supplied `eligibility()` (property-tested against it) and a verbatim copy used by the final output validator. Validators drop any ask or pair that is invalid, unavailable, repeated, overlapping or over budget. |
| `smp/potential.py` | `q_ab`: probability a pair becomes feasible once both people answer, as a product of pass rates of the unresolved constraints, estimated from the members observed in the current state. Known failures give `q = 0`. |
| `smp/model.py` | Outcome chain `P(respond) · P(accept) · P(date) · P(yes again, on time)`. Directional acceptance is a logistic model on goal, pace, lifestyle and conversation agreement, MAP-fitted online from matured responses with shrunk member effects. Unknown soft fields are integrated out, not imputed. A pair-level shared shock (3-point quadrature) means P(both accept) is not a product of independent directions. A missing response updates only the response-rate term and is never read as a "No". |
| `smp/clarify.py` | Value-of-information asks: 3-unit constraint bundles go to members whose answers unlock the most pair value soonest (pair-aware). Declined members and members with no possible partner are never asked. Spare units buy 1-unit soft asks only on contested edges. |
| `smp/allocate.py` | Maximum-weight matching on the feasible graph (general graph): exact DP on small components, Edmonds' blossom (`networkx`, optional) on large ones, greedy last resort; small first-introduction bonus. |
| `smp/policy.py`, `smp/cli.py` | Orchestration, 6 s time guard falling back to the supplied greedy, last-resort fallbacks (greedy, then an empty action). |
| `smp/baselines.py` | The three supplied baselines (greedy, no clarification, random feasible), re-implemented from `kit.baseline_asks` / `kit.baseline_match`; `policy.py --baseline X` runs them so `evaluate.py` can compare identical seeds. |

The policy is stateless: everything is recomputed from the request, so only information with `observed_day <= today`
is ever used. Memory is a ~40-byte dictionary.

### Deviations from the Round 1 plan

The Round 1 note proposed more than was built. These parts were **not** implemented:
Thompson-sampling exploration; the hub-criticality term κ; the rolling shift detector and forgetting factor; the
bivariate copula (replaced by the 3-point shared-shock quadrature, tested as H4); the gradient-boosted scorer ablation.
Reservation values λ are implemented but **off** by default (ablation in §5.5). Online adaptation is a periodic MAP refit
and nothing more.

---

## 3. Assumptions and data semantics

### 3.1 Semantics we enforce
- `null` means unknown, never "No" or zero. A declined hard field is never imputed or bypassed; that member is
  structurally unservable and is reported separately (§6.2).
- A missing response means the event did not happen by its deadline, not dislike. Unresolved introductions are
  right-censored, not failures.
- Only `who_to_meet` expresses preference; age and gender imply nothing. Zones are opaque labels; `relocate` never
  overrides `acceptable_zones`.
- Only information with `observed_day <= decision day` is used.

### 3.2 Simulator knowledge we rely on
The Round 1 note and the structure of the policy rely on the public kit's documented mechanics for *design*: which
fields matter, that responses are per-member, that feedback is delayed. The policy reads only the observable JSON.
It does not read hidden simulator objects or reconstruct anything from seeds or identifiers.

### 3.3 Prior provenance (please read)
An earlier version of our model started from coefficients equal to the kit's own hidden-outcome mechanics (for
example a 0.7 weight on relationship-goal agreement, a 0.45 shock sd and a 0.78 date rate), and the clarification
model hard-coded the generator's structure (age windows of ±3–10, 15% with children, 90% monogamous). The
problem statement says the public simulator is "an experimental tool, not an oracle for the policy". We therefore
replaced those with generic priors. The submitted default (`prior = neutral_emp`) starts from 0.5 priors with weak
strength and wide variance, and estimates the age-window pass rate from the observed members' own stated windows.
We chose it on **validation** seeds 2000–2019 only, where it was equivalent in expected MSMI to the simulator-derived
priors (−0.004, 95% CI −0.010 to +0.002). The older setting remains available as `prior = kit` and is reported as a
comparison row. On held-out batch B it is ahead by 0.005 on the diagnostic (§5.4), about 1.3% and far below seed noise.
A few multiplicative constants (date rate 0.78, on-time rate 0.6) remain in `model.py` and do come from the kit.
They scale every pair's value equally, so they cancel in every ranking and in the matching weights (which are
normalised by the mean). The only place their absolute scale matters is one small stopping threshold for asks in
`clarify.py` (`MIN_GAIN`).

---

## 4. Experimental protocol

- **Seed hygiene.** Tuning and every configuration decision used validation seeds 2000–2019 only. Held-out batch A
  (seeds 3000–3019, `results/test_*`) was run with the earlier `kit`-prior configuration; it also holds the older
  ablations. Held-out batch B (seeds 3020–3119, `results/test2_*`) was run once with the frozen final configuration and
  is the primary evidence. Public seeds 101–103 are used for the official evaluator run.
- **Comparisons.** Every policy runs on identical seeds and variants. Differences are paired by (variant, seed).
  Confidence intervals bootstrap seeds within each variant (3,000 resamples), then average the six variant means.
- **Score.** Organiser rule: mean over seeds within each family, then mean of the six families.
- **Diagnostic.** Because raw MSMI is a coin-flip count, the harness also computes *expected MSMI* from the simulator's
  latent values (conditional probability that each attempted introduction qualifies). It is an analysis tool and is
  labelled as such everywhere; a policy never sees it.
- **No inverse-propensity claims** are made; policies are compared only by full end-to-end runs on identical seeds.

---

## 5. Results

Full tables: `results/final_tables.md` (generated by `experiments/final_tables.py`).

### 5.1 Official `evaluate.py`, public seeds 101–103 (18 episodes per policy)

| policy | invalid | primary score | coverage | mutual acc/100 | ask cost |
|---|---|---|---|---|---|
| ours (final) | 0/18 | 0.306 | 0.375 | 5.92 | 218 |
| greedy | 0/18 | 0.389 | 0.372 | 5.50 | 207 |
| random feasible | 0/18 | 0.389 | 0.376 | 6.08 | 207 |
| no clarification | 0/18 | 0.139 | 0.143 | 1.75 | 0 |

**Read this table with care.** 18 episodes hold roughly 10 qualifying pairs in total, so one pair moves the score
by about 0.03. An earlier run of our policy with the simulator-derived priors scored 0.444 on the same 18 episodes
(`results/old_kit_prior/`); the two settings are equivalent in expectation (§3.3). We report both and treat neither as a
ranking of policies.

### 5.2 Held-out batch B (seeds 3020–3119; 100 per family, 600 episodes per policy)

| policy | invalid | **MSMI/100** | expected MSMI/100 (diag.) | coverage | mutual acc/100 | assignments | edge utilisation | ask cost |
|---|---|---|---|---|---|---|---|---|
| **ours (final)** | 0 | **0.376** | 0.377 | 0.335 | 5.32 | 74.9 | 0.833 | 221 |
| greedy (supplied) | 0 | 0.366 | 0.363 | 0.334 | 5.08 | 74.3 | 0.828 | 199 |
| random feasible | 0 | 0.370 | 0.361 | 0.335 | 5.02 | 74.5 | 0.831 | 199 |
| no clarification | 0 | 0.100 | 0.103 | 0.121 | 1.50 | 21.3 | 0.231 | 0 |
| abl: list-order asks | 0 | 0.383 | 0.370 | 0.336 | 5.09 | 74.4 | 0.829 | 199 |
| abl: greedy allocation | 0 | 0.383 | 0.382 | 0.335 | 5.29 | 74.8 | 0.832 | 222 |
| comparison: `kit` prior | 0 | 0.384 | 0.382 | 0.336 | 5.32 | 75.1 | 0.834 | 222 |
| comparison: `neutral` prior | 0 | 0.370 | 0.373 | 0.333 | 5.17 | 74.5 | 0.823 | 211 |

### 5.3 Scenario-level MSMI per 100 arrived members (diagnostic expected MSMI in parentheses)

| policy | standard | sparse | cold start | delayed | shifted weights | changing conditions |
|---|---|---|---|---|---|---|
| ours | 0.51 (0.46) | 0.09 (0.11) | 0.34 (0.39) | 0.41 (0.44) | 0.42 (0.41) | 0.48 (0.44) |
| greedy | 0.47 (0.45) | 0.10 (0.11) | 0.39 (0.37) | 0.38 (0.43) | 0.38 (0.39) | 0.47 (0.42) |
| random feasible | 0.46 (0.44) | 0.10 (0.11) | 0.36 (0.37) | 0.42 (0.42) | 0.43 (0.39) | 0.45 (0.42) |
| no clarification | 0.15 (0.14) | 0.01 (0.03) | 0.07 (0.05) | 0.10 (0.14) | 0.14 (0.13) | 0.14 (0.14) |

Within a family, differences between ours, greedy and random are inside noise. The one pattern that survives
is the diagnostic in cold start (0.39 against 0.37) and in shifted weights (0.41 against 0.39), consistent with earlier
asks, but the effects are about 0.02 and the confidence intervals per family are not tight enough to claim them.

### 5.4 Paired differences, ours minus comparator (95% bootstrap CI over seeds)

| comparator | MSMI/100 | expected MSMI/100 (diag.) |
|---|---|---|
| greedy | +0.010 [−0.031, +0.052] | +0.014 [+0.009, +0.018] |
| random feasible | +0.006 [−0.037, +0.048] | +0.016 [+0.012, +0.020] |
| no clarification | +0.276 [+0.241, +0.310] | +0.273 [+0.267, +0.280] |
| list-order asks (abl.) | −0.007 [−0.048, +0.036] | +0.007 [+0.003, +0.011] |
| greedy allocation (abl.) | −0.007 [−0.039, +0.027] | −0.005 [−0.008, −0.002] |
| `kit` prior | −0.008 [−0.036, +0.019] | −0.005 [−0.008, −0.002] |
| `neutral` prior | +0.006 [−0.030, +0.040] | +0.004 [+0.000, +0.007] |

### 5.5 Ablations

Required: at least one hypothesis-driven ablation. We ran six; two use held-out batch B, four use the older batch A
(seeds 3000–3019, run with the earlier `kit`-prior configuration; see `results/test_summary.md`).

| ablation | what it removes | batch | result |
|---|---|---|---|
| No clarification | all asks | B | Large loss: MSMI −0.276 [−0.310, −0.241]; assignments 74.9 → 21.3 |
| List-order asks | VOI ranking (asks in list order) | B | Raw MSMI −0.007 (noise); diagnostic −0.007 for the ablation, a ~2% benefit of VOI; median first-introduction wait 2 d vs 4 d |
| Greedy allocation | blossom / exact matching | B | No benefit from global matching: the ablation is 0.005 *higher* on the diagnostic (CI −0.008 to −0.002 for ours minus ablation) |
| Static model | online weight and member updates | A | Diagnostic +0.001 (no effect) |
| No soft asks | 1-unit soft-field asks | A | Diagnostic +0.002 (no effect) |
| Reservation values λ = 0.25 | waiting for better partners | A | Diagnostic +0.000 (no effect) |

### 5.6 Round 1 hypotheses: verdicts

| hypothesis | verdict | evidence |
|---|---|---|
| H1: time-aware allocation reaches ≥90% edge utilisation (greedy 78%) | **Not supported** | Utilisation 0.833 (ours) vs 0.828 (greedy). Greedy-allocation ablation is as good as blossom. |
| H2: VOI-ordered asks shorten the first-introduction wait | **Supported** | Median wait 2 d vs 4 d in the five families with full information, 5 d vs 7 d in cold start; list-order ablation diagnostic is 0.007 lower. |
| H3: online adaptation improves calibration under shift | **Not supported** | Held-out log-loss, shift family: static 0.684, adapted 0.705 (worse). An earlier rollout of the same test gave the opposite sign (0.690 → 0.673), so the effect is not stable. In the standard family adaptation is also slightly worse (0.664 → 0.673). No MSMI effect (static-model ablation). |
| H4: a shared-shock joint model is better calibrated than the product of directional probabilities | **Not supported** | 530 introductions with both responses: log-loss 0.5178 (joint) vs 0.5207 (product); Brier 0.1689 vs 0.1693. The shock is small, so the two are nearly identical. |

---

## 6. Failure analysis

### 6.1 Sparse supply
In the sparse-geography family there are about 23 feasible pairs per world and about half of all members have no
feasible partner at all. Mean members served per episode: 33.4 of 200. Of the 166.6 unserved, 66.3 declined a hard
field and 99.9 have no feasible partner; only 0.3 are explained by policy or capacity. Expected MSMI is 0.11 for every
policy; the score is bounded by supply, not by method.

### 6.2 Withheld answers
About 65 of 200 members in every family but cold start (81 in cold start) declined at least one hard question.
They can never be matched, so they are excluded from the asks (spending 3 units on them buys nothing) and reported
separately. Coverage (0.335) is therefore structurally capped near 0.35–0.40; policy or capacity explains 0.3–1.6
unserved members per episode, depending on the family.

### 6.3 Delayed feedback
Dates in the delayed family are pushed 5–12 days later, so more of them fall outside the 30-day qualifying window.
Expected MSMI is 0.44 against 0.46 in the standard family. The policy cannot influence date timing. It does not use unresolved
introductions as failures: a pair awaiting an answer is censored, and a missing response only changes the
member's response-rate estimate. We did not test any delay-specific tactic.

### 6.4 Competition for the same candidate
The feasible graph has hubs (endpoint degree about 10–12 among contested pairs). Over 8 validation episodes, 115 pairs
were untried while both endpoints were free on the same day at some point; **every one** was blocked because one
endpoint was already taken by another partner each such day, 82% earlier in the episode and 18% close to the
horizon. None came from both people idling. A member can take at most about 7–8 introductions in 60 days (each blocks
for at least 8 days), so a degree-10 hub cannot finish all of its pairs. That is the real ceiling, and it is why neither
greedy nor global matching moves utilisation. Choosing *which* edges a hub uses could still matter, but the
Round 1 oracle pilot and our ablations indicate that ordering gains are small in this simulator.

### 6.5 Cold start, shift and drift
Cold start has the fewest fully known members at arrival (34 of 200), so more of the budget goes to constraint bundles
and first introductions come later (median 5 days, p90 16). We saw no robust MSMI difference between policies in the
shifted-weights or changing-conditions families; we do not claim adaptation helped (H3).

### 6.6 Members leaving and arriving late
About 12% of members leave between days 22 and 60 without notice and about 30% arrive on days 1–20. We did not model
departure risk; reservation values that would have used it are off. We report no result specific to leavers.

---

## 7. Uncertainty and limitations

- **Noise.** The standard deviation of one episode's score is about 0.5; with 20 private seeds per family the
  six-family mean has a standard error near 0.05, larger than any between-policy difference we measured on the
  diagnostic (≤0.016). Rankings among reasonable policies will largely reflect chance.
- **Diagnostic is not the score.** Expected MSMI removes coin-flip noise but uses simulator latent values; it validates
  our analysis, not a deployable estimate.
- **Held-out reuse.** Batch A was used for the earlier ablations; the final config choice used validation seeds only.
  Batch B was run once for the final configuration. Batch B includes the `kit`-prior and `neutral`-prior rows for
  transparency; none of these rows fed back into a decision.
- **Calibration targets.** H3/H4 calibration use post-hoc final-state features and a small number of responses (about
  400–500 per variant); treat the verdicts as weak evidence.
- **Synthetic only.** Probabilities are simulator quantities. Nothing here is evidence about real members. Prioritising
  high-response members could under-serve quieter people in a real product; we mitigate with a first-introduction
  bonus and report waiting times, but do not claim fairness.
- **Container.** Not run here (§8).

---

## 8. Reproducibility declaration

| item | value |
|---|---|
| Training seeds | **none**: no trained assets; priors are fixed generic constants (`smp/model.py`, `smp/potential.py`) updated online inside an episode |
| Inference random seed | **none**: the policy uses no randomness; output is a pure function of the request (tested under different `PYTHONHASHSEED`) |
| Tuning seeds | 2000–2019 (validation) |
| Held-out seeds | 3000–3019 (batch A), 3020–3119 (batch B); public seeds 101–103 for the official evaluator |
| Dependencies | none required; `networkx==3.6.1` (BSD-3-Clause, `LICENSE-networkx.txt`) optional, pinned |
| External data / models / services | none |
| Compute | CPU only; training none |
| Per-call resources | 0.12 s slowest in-process call; 0.09 s worst including interpreter start; 17 MB peak RSS; request ≈ 0.4 MB; memory 37 bytes |

Commands:

```bash
python -m unittest discover -s tests                                   # 23 tests
python evaluate.py --policy run_ours.py --seeds 101,102,103 --variants all --output results/official_ours.json
python evaluate.py --policy policy.py --baseline greedy  --seeds 101,102,103 --variants all --output results/official_greedy.json
python evaluate.py --policy policy.py --baseline no_asks --seeds 101,102,103 --variants all --output results/official_no_asks.json
python evaluate.py --policy policy.py --baseline random  --seeds 101,102,103 --variants all --output results/official_random.json
python experiments/harness.py --policy ours --seeds 3020-3119 --variants all --out results/test2_ours.json   # and greedy/random/no_asks
python experiments/final_tables.py                                      # rebuilds results/final_tables.md
docker build -t smp-policy . && python evaluate.py --image smp-policy --seeds 101,102,103 --variants all --output results/container.json
```

**Container mode was not verified.** The authoring sandbox has no Docker daemon, so the last command above has not been
run by us. The Dockerfile pre-compiles bytecode (the evaluation container is read-only), uses an unprivileged user and
needs no network at inference. Run the last command once before submitting and keep its output.

---

## 9. Attribution

`kit.py`, `evaluate.py` and the problem statement are the organisers' starter material. `smp/baselines.py` and
`smp/feasibility.exact_eligibility` copy logic from `kit.py` to mirror the supplied behaviour. Coding and analysis
assistance: Claude (Anthropic) was used to write and test the code and to run the experiments; the team reviews and
owns the submission. No external datasets, pretrained models or paid services were used.
