#!/usr/bin/env python3
"""Heuristic publication hygiene checks; not a security or licensing certification."""
from pathlib import Path
import json
import re
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {'.git', '.venv', 'venv', '__pycache__', '.pytest_cache', 'output', 'build', 'dist', 'htmlcov'}
FORBIDDEN = {'.parquet', '.arrow', '.feather', '.csv', '.tsv', '.db', '.sqlite', '.sqlite3', '.pem', '.key', '.p12'}
PATTERNS = {
    'private-key marker': re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
    'GitHub credential pattern': re.compile(r'\bgh[pousr]_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{30,}\b'),
    'AWS access-key pattern': re.compile(r'\bAKIA[A-Z0-9]{16}\b'),
    'personal absolute path': re.compile(r'/(?:Users|home)/[^/\s]+|/private[/]tmp/'),
}

def audit(root):
    findings = []
    count = 0
    links = 0
    for path in sorted(root.rglob('*')):
        rel = path.relative_to(root)
        if any(part in IGNORED or part.endswith('.egg-info') for part in rel.parts):
            continue
        if path.is_symlink():
            findings.append(f'{rel}: symlinks require manual review')
            continue
        if not path.is_file():
            continue
        count += 1
        if path.suffix.lower() in FORBIDDEN or path.name == '.env' or path.name.startswith('.env.'):
            findings.append(f'{rel}: forbidden data/credential filename')
        try:
            text = path.read_text(encoding='utf-8')
        except UnicodeError:
            continue
        for label, pattern in PATTERNS.items():
            if pattern.search(text):
                findings.append(f'{rel}: {label}')
        if path.suffix == '.md':
            targets = re.findall(r'!?\[[^\]]*\]\(([^\s)]+)(?:\s+"[^\"]*")?\)', text)
            targets += re.findall(r'(?:src|href)="([^\"]+)"', text)
            for target in targets:
                if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
                    continue
                link = unquote(target.split('#')[0].split('?')[0])
                if not link:
                    continue
                links += 1
                resolved = (path.parent / link).resolve()
                if not resolved.is_relative_to(root.resolve()) or not resolved.exists():
                    findings.append(f'{rel}: missing or out-of-tree local reference {target}')
    return {'files_checked': count, 'local_links_checked': links, 'findings': findings,
            'scope': 'Working-tree heuristic; excluded build/runtime directories and Git history are not scanned. No absence-of-secrets or rights certification.'}

if __name__ == '__main__':
    result = audit(ROOT)
    print(json.dumps(result, indent=2))
    sys.exit(bool(result['findings']))
