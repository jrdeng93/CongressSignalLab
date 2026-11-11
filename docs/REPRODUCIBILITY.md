# Reproducibility

## Runs from this repository

```bash
python3 -m unittest discover -s tests -v
python3 -m congress_signal_lab --input examples/synthetic.json --output output/demo.json --horizon 2
python3 scripts/audit_public_tree.py
```

No vendor credentials or network requests are needed for these commands. Use a fresh output filename for every CLI run. The demo is synthetic and returns event-level outcomes, not a funded portfolio.

Optional chart rendering requires matplotlib and numpy:

```bash
python3 -m pip install '.[plots]'
MPLBACKEND=Agg python3 scripts/render_year_figures.py assets/research/year-data.json output/year-figures
```

The initial review used matplotlib 3.11.2 and numpy 2.5.4. Rendering across other versions may produce different file bytes. Numerical summaries are frozen; the renderer does not fetch prices or rerun a trading strategy.

To build an installable distribution:

```bash
python3 -m pip install build
python3 -m build
```

## Does not run from this repository

The +32.26% annual legacy portfolio, corrected-specification historical returns, raw-source authenticity checks across all filings, and live execution/capacity estimates. Required raw inputs and the annual funded simulator are absent. Do not infer historical replication from passing unit tests or regenerated plots.

## Independent review recipe

Read [AUDIT.md](AUDIT.md), [methodology](METHODOLOGY.md) and [input contract](INPUT_SCHEMA.md). Record the commit you reviewed, Python version, exact commands and observed outputs. Recompute the derived NAV totals, drawdowns and monthly factors independently. Then inspect time boundaries, full-date TF history, amendment conflicts, and non-finite/malformed inputs using synthetic counterexamples. Keep source validity, calculation correctness and execution assumptions as separate findings.

No snapshot files or private history are required to run the portable tests. Reports and manifests produced from real adapter inputs are local artifacts and may contain sensitive paths or licensed data; do not commit them automatically.
