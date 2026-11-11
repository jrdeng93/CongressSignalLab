# Contributing

Start with [the audit](docs/AUDIT.md) and [methodology](docs/METHODOLOGY.md). Prefer a small reproducible finding over broad assurances. English is the primary language for code, documentation and issue reports.

Run the unit tests, synthetic CLI and public-tree audit described in [reproducibility](docs/REPRODUCIBILITY.md). For logic changes, add an adversarial regression demonstrating the bug before the fix. Keep fixtures synthetic and disclose skipped checks.

Before a new experiment, freeze the hypothesis, universe, observation timing, fees, portfolio rules, baselines and rejection criteria. Separate exploratory selection from untouched validation. A failed historical result must not be silently replaced by a tuned winner.

Do not commit raw vendor records, credentials, personal paths, local outputs or generated build products. Code and data licenses are separate. A PR should state the problem, resulting behavior, evidence, tests, and any affected historical claim. See [security](SECURITY.md) for sensitive reports.
