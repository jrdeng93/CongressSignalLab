# Release audit and independent-review entry point

Reviewed 2026-11-11. **Share with caveats as an offline research-library candidate.** Keep repository visibility private while maintainers and independent tools review it. The historical trading experiment remains **Needs revision**. Software preparation is not certification of profitable trading, data rights or executable fills.

The candidate starts a fresh Git history from reviewed files in research snapshot 97a3f9557a0b948c5b2cb44ddcb92229a65f0de7. Private Git history, raw datasets, vendor caches, post drafts and personal runtime configuration were not imported.

## Software findings resolved in this candidate

| ID | Severity | Finding / correction | Verification |
|---|---|---|---|
| CODE-001 | P1 | Invalid identifiers and truthy string policy flags could enter scoring. Require typed, trimmed identifiers and an actual boolean policy flag. | Release regressions reject whitespace/boolean/placeholder IDs and string false policy flags. |
| CODE-002 | P1 | Direct APIs accepted boolean/noninteger configuration; direct score history could include stale events unlike selection. Validate numeric types and apply the 45-day history eligibility gate. | Regression tests cover horizon/top-k/cost types and stale direct history. |
| CODE-003 | P1 | Adapter shape/time/version/amount validation was inconsistent; malformed rows and conflicting revision chains could bypass assumptions or abort processing. Validate direct APIs, quarantine invalid Austin records/chains, preserve valid JSON. | Existing amendment/amount tests plus new malformed-row, version, JSON and boundary regressions. |
| CODE-004 | P1 | Committee CLI time gate contradicted its direct API. Allow a known snapshot at or before enrichment time. | Dated committee CLI regression. |
| CODE-005 | P1 | A malformed bracketed source URL raised an exception instead of quarantining the row. Catch URL parse failure. | Reproduced failure before fix; invalid-URL batch regression now passes. |
| DOC-001 | P1 | Historical headline and portable core could be conflated; figure exports lacked the later defect warning. | README/spec/reproducibility separate engines. All three figure groups now carry legacy/known-defect/corrected-rerun-pending text; numeric payload unchanged. |

The 42-test suite includes 15 additional independent regression methods. A passing suite covers the stated cases, not every possible upstream schema. The synthetic CLI runs without vendor inputs. Packaging and GitHub CI results for the final commit are recorded in repository history and Actions; do not infer CI success from this document alone.

## Open research findings

[HIST-001 through HIST-006](AUDIT_365.md) remain OPEN: full-date annual TF repair, historical security/fill filters, point-in-time provenance, execution capacity, untouched validation, and an end-to-end annual runner. None was closed by input-validation work. The +32.26% number is explicitly retained as a legacy result with known defects.

Additional current boundaries:

- **DATA-001 (P1, OPEN):** Stock-label checks are heuristics. Provide a dated security master and test truncated/mislabeled ETFs before claiming equity-only selection.
- **DATA-002 (P1, OPEN):** Prices and session calendars are caller-supplied. No complete-calendar, currency, corporate-action, volume or fill verification is built in.
- **DATA-003 (P1, OPEN):** Adapter revision-chain validation uses the supplied snapshot, including its correction metadata. A historical as-of slice is not certified historical replay; first_seen_at remains the real observation time.
- **RIGHTS-001 (OPEN):** MIT covers code, not third-party data. No legal or redistribution clearance has been completed. Consult [source notices](DATA_SOURCES.md).

## What was checked

Independent arithmetic reconciled all four packaged NAV series: 251 values each, total returns, maximum drawdowns and all 13 monthly factors to a 1e-12 tolerance. This is consistency of derived outputs, not independent raw-data replication. The prior research audit is reused only for its frozen historical inputs and scope.

The initial tracked-file scan found no common credential markers or personal absolute paths. The generated banner had no Exif/GPS/XMP markers. Original SVGs had no scripts, event handlers or external resource references; the heatmap's embedded raster images are PNGs. These bounded checks are not exhaustive forensic or legal assessments.

Coverage below uses explicit review units, not an overall accuracy percentage. 0/N means no remaining defect observed in that scoped category, not comprehensive certification.

| Repository presentation quality | Observed defects | Assessment |
|---|---:|---|
| Usefulness/completeness | 1 / 2 | Portable toolkit supplied; complete annual experiment replication remains absent. |
| Analytical clarity | 0 / 5 | README, method, input, reproduction and source documents distinguish the two specifications. |
| Visual consistency | 0 / 3 | Three figure groups preserve the derived values and carry the revised warning. |

| Analytical correctness and robustness | Observed defects | Assessment |
|---|---:|---|
| Historical source fitness | 1 / 1 | Legacy chain contains known TF/security/fill issues; complete source authentication not performed here. |
| Derived-value accuracy | 0 / 4 | Four packaged NAV series reconcile; original raw-data engine was not rerun. |
| Within-chart agreement | 0 / 3 | Figure values agree with the same frozen derived summaries. |
| Complete reproduction chain | 1 / 1 | Annual engine/raw inputs not distributed; explicit open finding HIST-006. |
| Cross-artifact consistency | 0 / 2 | Shipped-core behavior and legacy-result scope treated separately throughout. |
| Data-quality controls | 1 / 2 | Runtime validation strengthened; historical universe/execution controls remain incomplete. |
| Conclusion support | 0 / 2 | Claims are limited to a runnable research library and a qualified legacy result; no stable-alpha claim. |

## Reproduce and extend the review

```bash
python3 -m unittest discover -s tests -v
python3 -m congress_signal_lab --input examples/synthetic.json --output output/review-demo.json --horizon 2
python3 scripts/audit_public_tree.py
```

The scanner checks the working tree for common credential patterns, forbidden raw-data filenames and broken local links. It excludes Git history, local outputs and build directories. Inspect the exact Git objects intended for publication separately. An empty finding list is not a security certificate.

For every new finding, record the reviewed commit, stable ID, severity, affected claim or API, minimal synthetic reproduction, observed output, proposed correction and evidence needed to close it. Do not replace the research question, retune rules, remove unfavorable outcomes, or mark source/execution questions resolved because tests pass. Use the audit issue template and keep private inputs out of reports.

## Before a later visibility change

- Recheck the exact latest commit, all Git history, Actions, package installation and public-tree scan.
- Confirm no raw data, credentials or personal paths were introduced by later tools.
- Preserve the legacy warnings and open findings, or replace them only with independently verified corrected research.
- Revisit data-use notices for the intended distribution and use.
- Change visibility only on explicit maintainer instruction. This preparation does not publish the repository.
