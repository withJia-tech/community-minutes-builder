# Is It Worth It? — Calculator 4b, "Drive there, or MRT?"

A per-trip cost comparison for Singapore car owners deciding how to get to one
specific place: drive, take the MRT, or book a Grab. Not a commute tool and
not a monthly budget — the user is at the door, deciding now.

The point of the thing is parking. A three-hour hospital visit can cost more
in parking than the entire petrol bill for the round trip, and almost nobody
checks before leaving.

> **This directory is in the wrong repository.** It was built on a branch of
> `community-minutes-builder` because that is where the build session was
> scoped. It belongs in its own `is-it-worth-it` repository and is written to
> move there unchanged — nothing outside this directory was touched, and no
> path reaches above it. See "Moving this out" below.

## Running it

ES modules will not load over `file://` — Chromium blocks the import as a CORS
violation and the page renders inert. Serve the directory:

```bash
cd is-it-worth-it
python3 -m http.server 8099
# http://127.0.0.1:8099/calculators/drive-or-mrt/index.html
```

## Tests

```bash
node --test        # 40 tests, no dependencies, no install
```

Two suites. `test/calc.test.js` covers rules D1–D10 — the deterministic layer,
where a wrong answer is a defect rather than a disagreement.
`test/data-drift.test.js` guards the assumption files against their inline
mirror and fails if they diverge.

There are deliberately no tests on the heuristics. You cannot unit-test a
guess. They are labelled in the UI instead, which is the honest alternative.

## Layout

```
is-it-worth-it/
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
└── deploy.workflow.yml     # ready for .github/workflows/ once extracted
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

```bash
# from the repository root, once is-it-worth-it exists on GitHub
git mv is-it-worth-it/deploy.workflow.yml is-it-worth-it/.github/workflows/deploy.yml
# then move the directory contents to the new repository root
```

No file in here refers to anything above this directory, so the move is a copy
and a commit. The workflow is parked as `deploy.workflow.yml` rather than
under `.github/workflows/` on purpose — dropping a Pages deploy into the
minutes-builder repository would try to publish the wrong project.

## Status

Prototype, P1. Accuracy is bounded by section 5.2 of the handoff: no live ERP,
no live fares, no real carpark rates, no traffic model. Every one of those is
stated in the assumptions panel and in the share string, which carries the
assumptions version so a result read months later flags its own age.
