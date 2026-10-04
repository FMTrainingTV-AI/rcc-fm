#!/usr/bin/env python3
"""Allocate and append to one explicitly bound personal session record."""
import argparse
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import re
import sys
import uuid


def now():
    return datetime.now().astimezone().isoformat(timespec='seconds')


def allocate(root, name, intent):
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]*', name):
        raise ValueError('name must be a short handle without paths')
    directory = root / '_pm/sessions'
    directory.mkdir(parents=True, exist_ok=True)
    if not directory.resolve().is_relative_to(root):
        raise ValueError('session directory escapes the project')
    day, session_id = now()[:10], str(uuid.uuid4())
    # O_EXCL handles competing processes on this filesystem. It does not claim
    # a distributed lock across two offline synced-folder replicas.
    for ordinal in range(1, 100000):
        stem = f'{day}-{name}' + (f'-{ordinal}' if ordinal > 1 else '')
        path = directory / (stem + '.md')
        try:
            with path.open('x') as f:
                f.write(f'# {day} — {name} — session {ordinal}\n\nSession-ID: {session_id}\nStarted: {now()}\n\n## Intent\n\n{intent.strip()}\n')
                f.flush(); os.fsync(f.fileno())
            return {'path': str(path.relative_to(root)), 'id': session_id, 'status': 'open'}
        except FileExistsError:
            continue
    raise ValueError('no free session filename')


def append(root, relative, session_id, entry, close=False):
    path = (root / relative).resolve()
    directory = (root / '_pm/sessions').resolve()
    if not directory.is_relative_to(root) or path.parent != directory or path.suffix != '.md':
        raise ValueError('session must be a file directly under _pm/sessions/')
    with path.open('r+') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        text = f.read()
        ids = re.findall(r'^Session-ID: (.+)$', text, re.M)
        if ids != [session_id]:
            raise ValueError('session identity mismatch; recover the bound path, never select the newest file')
        closed = re.search(r'^Closed: (.+)$', text, re.M)
        if closed:
            if not close: raise ValueError('cannot re-aim a closed session')
            return {'path': relative, 'id': session_id, 'status': 'already-closed', 'closed': closed[1]}
        # Quoting blocks keeps user content from impersonating metadata markers.
        if re.search(r'^(Session-ID|Closed|Started):', entry, re.M):
            raise ValueError('entry must not contain reserved session metadata')
        stamp = now()
        content = ('\n\n## Session close\n\n' + entry.strip() + f'\n\nClosed: {stamp}\n') if close else (
            f'\n\n## Re-aimed {stamp}\n\n' + entry.strip() + '\n')
        f.seek(0, os.SEEK_END); f.write(content); f.flush(); os.fsync(f.fileno())
        return {'path': relative, 'id': session_id, 'status': 'closed' if close else 'reaimed'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', default='.')
    sub = ap.add_subparsers(dest='command', required=True)
    opening = sub.add_parser('open')
    opening.add_argument('--name', required=True)
    opening.add_argument('--intent', required=True)
    for cmd in ('reaim', 'close'):
        parser = sub.add_parser(cmd)
        parser.add_argument('--session', required=True)
        parser.add_argument('--id', required=True)
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--entry')
        group.add_argument('--entry-file')
    args = ap.parse_args()
    try:
        root = Path(args.root).resolve()
        if args.command == 'open': result = allocate(root, args.name, args.intent)
        else:
            entry = Path(args.entry_file).read_text() if args.entry_file else args.entry
            result = append(root, args.session, args.id, entry, args.command == 'close')
        print(json.dumps(result))
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr); return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
