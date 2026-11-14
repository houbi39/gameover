#!/usr/bin/env python3
"""Keep legacy PS4 AppCache manifests valid and versioned from their contents."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path
from urllib.parse import unquote

MANIFEST_HEADER = 'CACHE MANIFEST'
VERSION_PREFIX = '# GAMEOVER-CACHE-VERSION: '


def parse_cache_entries(text: str) -> list[str]:
    entries: list[str] = []
    section = ''
    for line in text.splitlines():
        value = line.strip()
        if not value or value.startswith('#'):
            continue
        upper = value.upper()
        if upper in {'CACHE:', 'NETWORK:', 'FALLBACK:'}:
            section = upper
            continue
        if upper == MANIFEST_HEADER:
            continue
        if section == 'CACHE:':
            entries.append(value)
    return entries


def _asset_path(root: Path, manifest: Path, entry: str) -> Path:
    # AppCache entries may carry a query string (used by this host as a URL
    # version token). The query is not part of the on-disk filename.
    path_part = entry.split('?', 1)[0].split('#', 1)[0]
    path_part = unquote(path_part.replace('\\', '/'))
    if not path_part or path_part.startswith(('http://', 'https://', '//')):
        raise ValueError(f'Unsupported non-local CACHE entry in {manifest}: {entry}')
    target = (manifest.parent / path_part).resolve()
    base = root.resolve()
    if target != base and base not in target.parents:
        raise ValueError(f'CACHE entry escapes repository root in {manifest}: {entry}')
    if not target.is_file():
        raise FileNotFoundError(f'Missing CACHE entry in {manifest}: {entry} -> {target}')
    return target


def manifest_digest(root: Path, manifest: Path, text: str) -> str:
    digest = hashlib.sha256()
    for entry in parse_cache_entries(text):
        asset = _asset_path(root, manifest, entry)
        relative = asset.relative_to(root.resolve()).as_posix()
        digest.update(relative.encode('utf-8'))
        digest.update(b'\0')
        digest.update(asset.read_bytes())
        digest.update(b'\0')
    return digest.hexdigest()


def update_manifest_text(text: str, version: str) -> str:
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    header_index = next((i for i, line in enumerate(lines) if line.strip() == MANIFEST_HEADER), None)
    if header_index is None:
        raise ValueError('Manifest is missing the required CACHE MANIFEST header')

    # The header must be the very first line. Preserve all other content,
    # including existing explanatory comments, after the generated version.
    body = [line for i, line in enumerate(lines) if i != header_index]
    body = [line for line in body if not line.startswith(VERSION_PREFIX)]
    while body and body[-1] == '':
        body.pop()
    return '\n'.join([MANIFEST_HEADER, VERSION_PREFIX + version, *body, ''])


def update_manifests(root: Path, check: bool = False) -> list[Path]:
    changed: list[Path] = []
    for manifest in sorted(root.rglob('*.manifest')):
        if '.git' in manifest.parts:
            continue
        text = manifest.read_text(encoding='utf-8')
        version = manifest_digest(root, manifest, text)
        updated = update_manifest_text(text, version)
        if updated != text:
            if check:
                changed.append(manifest)
            else:
                manifest.write_text(updated, encoding='utf-8', newline='\n')
                changed.append(manifest)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--check', action='store_true', help='fail if any manifest needs updating')
    args = parser.parse_args()
    try:
        changed = update_manifests(args.root.resolve(), check=args.check)
    except (OSError, ValueError) as exc:
        print(f'AppCache manifest error: {exc}', file=sys.stderr)
        return 1
    if args.check:
        if changed:
            print('Stale AppCache manifests:')
            for path in changed:
                print(f'  {path.relative_to(args.root.resolve())}')
            return 1
        print('All AppCache manifests are valid and up to date.')
        return 0
    print(f'Updated {len(changed)} AppCache manifest(s).')
    for path in changed:
        print(f'  {path.relative_to(args.root.resolve())}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
