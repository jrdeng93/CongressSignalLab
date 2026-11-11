# Security

The toolkit has no broker connection, account integration, remote execution endpoint or order execution. It reads local inputs and writes new local outputs. Only process files from sources you are authorized to use; input validation is not a sandbox for hostile files.

Do not put credentials, personal records, raw vendor data or sensitive logs in a public issue. If private vulnerability reporting is enabled in the repository's Security tab, use it. Otherwise contact the maintainer through an existing private channel; do not disclose exploit details publicly while arranging one. No private-reporting feature is assumed enabled.

The publication scanner is a heuristic for common accidental disclosures, forbidden data files and broken local links. It does not prove the absence of secrets, vulnerabilities or license restrictions. Review new files and Git history before publication.
