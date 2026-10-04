"""Portable filename policy; JSON is the canonical distributable policy snapshot."""
import fnmatch
import json
import posixpath
from pathlib import Path

POLICY = json.loads(Path(__file__).with_name('credential-policy.json').read_text())


def is_secret(path):
    name = posixpath.normpath(str(path).replace('\\', '/')).lower().strip('/')
    base = name.rsplit('/', 1)[-1]
    if any(fnmatch.fnmatchcase(base, p) for p in POLICY['allow_basenames']):
        return False
    return (any(fnmatch.fnmatchcase(base, p) for p in POLICY['secret_basenames'])
            or any(fnmatch.fnmatchcase(name, p) for p in POLICY['secret_paths']))
