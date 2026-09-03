#!/bin/bash
# credential-guard — PreToolUse hook (Bash matcher).
# Blocks `git add` / `git stage` / `git commit` when a credential-shaped file
# would be staged or committed. Deterministic backing for the "never commit
# credentials" rule: a live client credential is already public from
# exactly this mistake once.
#
# Exit 2 = block (message goes to Claude). Exit 0 = allow. Any internal
# failure falls through to allow — this guard must never break git for
# unrelated reasons.
#
# Parsing lives in python3 (shlex): the command is split into segments at
# shell operators and EVERY git add/stage/commit in the chain is checked —
# `git add .env && git commit -m x` is caught at the add, not skipped for
# the commit. Directory operands are expanded via a scoped `git status`,
# quoted `-C` paths survive tokenization, and the full path (not just the
# basename) is lowercased before matching.

set -u
input=$(cat 2>/dev/null) || exit 0
[ -z "$input" ] && exit 0

# Fast path: only spawn the parser when the payload could contain a staging
# git call at all. Coarse on purpose — the python below is the real parser.
printf '%s' "$input" | grep -Eq 'git.*(add|stage|commit)' || exit 0

hits=$(CG_INPUT="$input" python3 <<'PY' 2>/dev/null
import fnmatch, json, os, shlex, subprocess, sys

def out(paths):
    for p in paths:
        print(p)
    sys.exit(0)

try:
    cmd = json.loads(os.environ.get("CG_INPUT", "")).get("tool_input", {}).get("command", "")
except Exception:
    out([])
if not isinstance(cmd, str) or not cmd.strip():
    out([])

ALLOW_BASENAMES = [".env.example", ".env.sample", ".env.template",
                   "*.example", "*.sample", "*.template"]
SECRET_BASENAMES = ["account.md", "accounts.md", "credentials.md",
                    "credentials.json", "credentials.yaml", "credentials.yml",
                    "secrets.json", "secrets.yaml", "secrets.yml",
                    ".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx",
                    "id_rsa", "id_ed25519", "*.keystore",
                    ".npmrc", ".pypirc", ".netrc"]
SECRET_PATHS = ["*/secrets/*", "secrets/*", "*/.ssh/*", ".ssh/*",
                "*/.aws/credentials"]

def is_secret(path):
    p = path.replace("\\", "/").lower().strip("/")
    b = os.path.basename(p)
    if any(fnmatch.fnmatch(b, pat) for pat in ALLOW_BASENAMES):
        return False
    if any(fnmatch.fnmatch(b, pat) for pat in SECRET_BASENAMES):
        return True
    return any(fnmatch.fnmatch(p, pat) for pat in SECRET_PATHS)

def tokenize(text):
    # A newline separates commands like ';' does. (Inside a quoted string this
    # rewrites the token's content, which detection never depends on.)
    text = text.replace("\n", " ; ")
    lex = shlex.shlex(text, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    return list(lex)

def segments(tokens):
    seg, res = [], []
    for t in tokens:
        if t and all(c in "();<>|&\n" for c in t):
            if seg:
                res.append(seg)
            seg = []
        else:
            seg.append(t)
    if seg:
        res.append(seg)
    return res

SKIP_PREFIX = {"command", "builtin", "nohup", "env", "sudo"}

def parse_git(seg):
    """Return (repo_dir, subcommand, rest) or None."""
    i = 0
    while i < len(seg) and ("=" in seg[i] and not seg[i].startswith("-")
                            and seg[i].split("=", 1)[0].replace("_", "").isalnum()
                            or seg[i] in SKIP_PREFIX):
        i += 1
    if i >= len(seg) or os.path.basename(seg[i]) != "git":
        return None
    i += 1
    repo = None
    while i < len(seg):
        t = seg[i]
        if t == "-C" and i + 1 < len(seg):
            repo = seg[i + 1]; i += 2
        elif t.startswith("-C") and len(t) > 2:
            repo = t[2:]; i += 1
        elif t == "-c" and i + 1 < len(seg):
            i += 2
        elif t.startswith("-"):
            i += 1
        else:
            return (repo, t, seg[i + 1:])
    return None

def git(repo, args):
    base = ["git"] + (["-C", repo] if repo else [])
    r = subprocess.run(base + args, capture_output=True, text=True, timeout=15)
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    return r.stdout

def status_paths(repo, pathspec=None):
    args = ["status", "--porcelain", "--untracked-files=all"]
    if pathspec:
        args += ["--"] + pathspec
    paths = []
    for line in git(repo, args).splitlines():
        p = line[3:]
        if " -> " in p:
            p = p.split(" -> ", 1)[1]
        paths.append(p.strip('"'))
    return paths

ALL_TOKENS = {"-A", "--all", "--no-ignore-removal", "-u", "--update", ".", "*"}

hits, seen = [], set()
try:
    for seg in segments(tokenize(cmd)):
        parsed = parse_git(seg)
        if not parsed:
            continue
        repo, sub, rest = parsed
        if sub not in ("add", "stage", "commit"):
            continue
        try:
            git(repo, ["rev-parse", "--is-inside-work-tree"])
        except Exception:
            continue  # not a repo here — nothing to guard
        candidates = []
        if sub in ("add", "stage"):
            flags = [t for t in rest if t.startswith("-") and t != "--"]
            ops = [t for t in rest if not t.startswith("-") or t == "-"]
            if any(t in ALL_TOKENS for t in flags) or any(o in (".", "*") for o in ops):
                candidates = status_paths(repo)
            else:
                for op in ops:
                    local = os.path.join(repo, op) if repo else op
                    if os.path.isdir(local):
                        try:
                            candidates += status_paths(repo, [op])
                        except Exception:
                            candidates += status_paths(repo)
                    else:
                        candidates.append(op)
        else:  # commit
            candidates = git(repo, ["diff", "--cached", "--name-only"]).splitlines()
            short = [t for t in rest if t.startswith("-") and not t.startswith("--")]
            if ("--all" in rest or "--include" in rest
                    or any("a" in t[1:] or "i" in t[1:] for t in short)):
                candidates += git(repo, ["diff", "--name-only"]).splitlines()
        for c in candidates:
            c = c.strip().strip('"')
            if c and c not in seen and is_secret(c):
                seen.add(c)
                hits.append(c)
except Exception:
    out([])  # fail open: never break git for unrelated reasons

out(hits)
PY
) || exit 0

if [ -n "$hits" ]; then
  {
    echo "credential-guard: BLOCKED — this would stage/commit credential-shaped files:"
    while IFS= read -r h; do [ -n "$h" ] && printf '  %s\n' "$h"; done <<< "$hits"
    echo "These must stay out of git. Add them to .gitignore (and 'git rm --cached' if already tracked),"
    echo "or stage only the files you mean. Examples/templates (*.example, *.sample) are allowed."
  } >&2
  exit 2
fi
exit 0
