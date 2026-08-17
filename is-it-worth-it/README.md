# Is It Worth It? — Calculator 4b, "Drive There or MRT?"

A per-trip cost comparison for Singapore car owners deciding how to get to one
specific place: drive, take the MRT, or book a Grab. Not a commute tool and
not a monthly budget — the user is at the door, deciding now.

The point of the thing is parking. Three hours at a public hospital costs more
in parking than the entire petrol bill for the round trip, and almost nobody
checks before leaving.

> **This directory is not yet in its own repository.** Creating
> `withJia-tech/is-it-worth-it` failed — the GitHub App this session
> authenticates as cannot create repositories (`403 Resource not accessible by
> integration`). The repository has to be created by hand, once, in the
> browser. Everything here is written to move across unchanged: no path
> reaches above this directory, and the Pages workflow is parked as
> `deploy.workflow.yml` so it stays inert until it is somewhere it should run.
> See "Moving this out".

## No agent, deliberately

There is no LLM call, no pipeline, no agent anywhere in this build, and there
should not be. The whole calculator is ten arithmetic rules over numbers the
user types. Learning a user's driving habits — the "agentic" tier in the
handoff — would be a large amount of machinery to answer a question that
`parkRate × parkHours` already answers exactly.

The honest verdict for a decision this small is that the deterministic layer
*is* the product, and the useful upgrade path is better data (real HDB and URA
carpark rates), not more inference.

## Running it

ES modules will not load over `file://` — Chromium blocks the import as a CORS
violation and the page renders inert. Serve the directory:

```bash
cd is-it-worth-it
python3 -m http.server 8099
# http://127.0.0.1:8099/
```

## Tests

```bash
node --test        # 44 tests, no dependencies, no install
```

`test/calc.test.js` covers rules D1–D10, the layer where a wrong answer is a
defect rather than a disagreement. `test/data-drift.test.js` guards the
assumption files against their inline mirror and fails if they diverge.

There are deliberately no tests on the heuristics. You cannot unit-test a
guess. They are labelled in the UI instead, which is the honest alternative.

## Layout

```
is-it-worth-it/
├── index.html              # root — redirects to the one live calculator
├── calculators/drive-or-mrt/
│   ├── index.html          # the calculator: markup, styles, wiring
│   ├── calc.js             # D1-D10, pure functions, no DOM
│   └── defaults.js         # fallback mirror + assumption loader
├── data/
│   ├── parking-defaults.json   # H1 — destination type to hourly rate
│   └── fare-defaults.json      # H2-H7 — every other assumed constant
├── shared/tokens.css       # design tokens, values only
├── docs/DECISIONS.md       # answers to the architect's open questions
├── test/
└── deploy.workflow.yml     # → .github/workflows/deploy.yml once extracted
```

## Where the judgment sits

Every assumed constant lives in `data/*.json`, never inline in the calculator.
That is the decision the handoff asked to close, and the reasoning is in
`docs/DECISIONS.md`. In short: a PM can change the petrol price in GitHub's
web editor and the change is a reviewable diff, which is what "auditable" has
to mean to be worth anything.

`calc.js` knows arithmetic. It does not know any of the guesses — they arrive
as arguments. That separation is what makes the deterministic layer testable
and the heuristic layer swappable.

The highest-leverage improvement available is still H1. Parking rates are a
heuristic only because the data is not loaded; HDB and URA publish them. That
is a CSV, not an API, and it costs nothing. It converts the single number the
product exists to surface from a guess into a fact.

## Moving this out

1. Create an empty public repository `withJia-tech/is-it-worth-it` (no README,
   no `.gitignore` — this directory supplies both).
2. Copy the contents of this directory to the new repository root.
3. `mkdir -p .github/workflows && git mv deploy.workflow.yml .github/workflows/deploy.yml`
4. Repository settings → Pages → Source: **GitHub Actions**.

The workflow runs `node --test` and only deploys if it passes.

## Status

Prototype, P1. Accuracy is bounded by section 5.2 of the handoff: no live ERP,
no live fares, no real carpark rates, no traffic model. Every one of those is
stated in the assumptions panel and in the share string, which carries the
assumptions version so a result read months later flags its own age.
