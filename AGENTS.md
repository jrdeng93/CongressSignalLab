# Guidance for independent reviewers

Read README.md, docs/AUDIT.md, docs/METHODOLOGY.md and docs/INPUT_SCHEMA.md before changes. English is the primary documentation language.

This is an offline research library. Do not place orders, add account credentials, download or publish raw vendor datasets, change repository visibility, or publish a release without explicit maintainer instruction.

Keep historical experiments and shipped-core behavior distinct. Never transfer a legacy return to a corrected algorithm without rerunning it. Preserve unfavorable results and label parameter selection. Do not retune a benchmark while presenting a change as a bug fix.

Use synthetic regression fixtures. Check timestamps, amendments, distinct dates, missing prices, fees and output overwrite protection. Run python3 -m unittest discover -s tests -v and python3 scripts/audit_public_tree.py. Check the documented CLI in a clean directory and installed package when packaging changes.

Report findings with stable IDs, severity, affected files/claims, a minimal reproducer, evidence and remaining uncertainty. Update docs/AUDIT.md only after verification. Passing tests do not certify historical source quality, legal permissions or future returns. Keep raw evidence local; share a sanitized reproducible case.
