#!/usr/bin/env python3
"""sdlc-gate: deterministic gates for a repo that Claude Code works in.

Installed at <repo>/.claude/hooks/sdlc_gate.py and wired into the repo's
.claude/settings.json as a PreToolUse hook (Bash, Monitor, Edit, Write,
NotebookEdit) and a Stop hook. Rules live in .claude/sdlc/gates.json.

  production  a shell command matching a rule is denied or needs approval
  protected   an edit to a matching path is denied or needs approval
  test lock   files frozen by `lock` cannot be edited until `unlock`
  commit      a commit while protected paths have changes needs approval;
              a commit while the test lock is violated is blocked
  self        changes to the gate's own files need approval

The gate inspects those tools' calls; it is not a sandbox. It refuses the shell
writes it can read with certainty (a redirect, rm, mv, cp, tee, sed -i on the
path). Everything else in a shell line (a formatter, a script, git, find,
inline code) is let through: that change is caught when a commit is attempted,
and a changed locked file is also caught at Stop. MCP tools never reach it.
Config, lock state or an event the gate cannot read blocks.

CLI: sdlc_gate.py lock [--reason TEXT] [GLOB ...] | unlock | status | check
"""
import datetime
import glob
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve()
ROOT = HERE.parents[2]
CONFIG = ROOT / '.claude/sdlc/gates.json'
SCRIPT = '.claude/hooks/sdlc_gate.py'


def state_dir():
    """Lock and log live in the git directory, where `git clean -x` cannot reach them."""
    dot_git = ROOT / '.git'
    try:
        if dot_git.is_dir():
            return dot_git / 'sdlc-gate'
        if dot_git.is_file():  # a worktree or submodule keeps a pointer file here
            pointer = re.match(r'gitdir:\s*(.+)', dot_git.read_text().strip())
            if pointer:
                return Path(os.path.realpath(ROOT / pointer.group(1))) / 'sdlc-gate'
    except OSError:
        pass
    return ROOT / '.claude/sdlc/state'


STATE = state_dir()
LOCK = STATE / 'test-lock.json'
LOG = STATE / 'gate-log.jsonl'

COMMAND_TOOLS = ('Bash', 'Monitor')
EDIT_TOOLS = ('Edit', 'Write', 'NotebookEdit')
ACTIONS = ('deny', 'ask')
RULE_KEYS = {'production': {'name', 'match', 'action', 'reason', 'approval'},
             'protected': {'name', 'paths', 'action', 'reason', 'approval'}}
SELF_PATHS = (SCRIPT, '.claude/sdlc/**', '.claude/settings.json', '.claude/settings.local.json')
SELF_STATE = re.compile(r'^\.git/(?:worktrees/[^/]+/)?sdlc-gate(?:/|$)', re.I)
SELF_REASON = 'is part of the gate itself; changing it changes what the gate enforces.'
SELF_APPROVAL = 'The user approves this prompt, or makes the change by hand.'
UNLOCK_ROUTE = f'The user releases the lock with: python3 {SCRIPT} unlock'

# A file inside a nested worktree of this repo answers to the same rules as the file it mirrors.
WORKTREE = re.compile(r'^\.claude/worktrees/[^/]+/(.+)$', re.I)
WORKTREE_ROOT = re.compile(r'^(\.claude/worktrees/[^/]+)/', re.I)

# `git ... commit` inside one simple command. `.git`, `foo-git` and `legit` are not Git.
COMMIT = re.compile(r'(?<![.\w-])git\b(?:(?![;&|\n]).)*?\bcommit\b', re.I)
SELF_BASH = re.compile(r'''
    \.claude/sdlc(?![\w-])                                  # config
  | \.claude/settings(?:\.local)?\.json                     # where the hook is registered
  | sdlc_gate\.py                                           # the gate itself
  | \.git/\S*sdlc-gate                                      # lock and log
  | (?<![\w.-])\.claude(?:/hooks)?/?(?=$|[\s"';&|)])        # the directories that hold them
''', re.X | re.I)
# Exempt: one simple command with no chaining, substitution or redirection anywhere in it.
ARG = r'[^\s"\';&|<>`$()]'
TAIL = r'[^;&|<>`$\n]*$'
SELF_BASH_SAFE = (
    re.compile(r'^\s*python3?\s+["\']?(?:\$\{?CLAUDE_PROJECT_DIR\}?/)?' + ARG + r'*\.claude/hooks/sdlc_gate\.py["\']?'
               r'\s+(?:lock|status|check)\b' + TAIL, re.I),
    re.compile(r'^\s*git\s+(?:-C\s+' + ARG + r'+\s+)?(?:add|diff|status|log|show|blame|ls-files)\b'
               r'(?!.*--output)' + TAIL, re.I),
    re.compile(r'^\s*(?:ls|cat|head|tail|wc|stat)\s' + TAIL, re.I),
)

# Kept out of the log: the password in a URL, and the value after a secret-looking name.
SECRETS = re.compile(r'''(?ix)
    (?P<url>://[^/\s:@]+:)[^@\s]+(?=@)
  | (?P<name>(?:password|passwd|secret|token|api[_-]?key)\w*["']?\s*[=:\s]\s*)["']?[^\s"']+
''')


# The shell-write check reads only what it can read with certainty: a redirect, or one of these
# commands naming the path. Everything else (a formatter, a script file, git, find, inline code)
# is let through and left to the commit check and the Stop hook. It errs toward allowing.
REMOVERS = set('rm rmdir unlink shred'.split())
FILE_WRITERS = set('tee truncate'.split())
DESTINATION_WRITERS = set('cp install rsync ln'.split())  # only the last path is written
SHELLS = set('bash sh zsh dash ksh'.split())
KEYWORDS = set('if then else elif fi while until do done time ! { }'.split())
WRAPPERS = set('env sudo doas command builtin exec nohup nice timeout stdbuf caffeinate xargs'.split())
WRAPPER_VALUES = {  # options of each wrapper that take a value, so the value is not read as the command
    'sudo': {'-u', '-g', '-p', '-h', '-U', '-C', '-D', '-R', '-T'}, 'doas': {'-u', '-C'},
    'env': {'-u', '-C', '-S'}, 'nice': {'-n'}, 'timeout': {'-k', '-s'}, 'stdbuf': {'-i', '-o', '-e'},
    'xargs': {'-n', '-P', '-I', '-L', '-s', '-d', '-E', '-a'}, 'caffeinate': {'-t', '-w'}, 'exec': {'-a'}}
ASSIGNMENT = re.compile(r'^[A-Za-z_]\w*=')
WILDCARD = re.compile(r'[*?\[]')


class GateError(Exception):
    """Something the gate needs is missing or unreadable."""

    def __init__(self, message, gate='config'):
        super().__init__(message)
        self.gate = gate


def rel(path):
    try:
        return Path(path).relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def glob_regex(pattern):
    """`**` spans directories, `*` and `?` stay inside one; a trailing `/` means the tree."""
    pattern = pattern.strip()
    if pattern.startswith('./'):
        pattern = pattern[2:]
    if pattern.endswith('/'):
        pattern += '**'
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith('**/', i):
            out.append('(?:.*/)?')
            i += 3
        elif pattern.startswith('**', i):
            out.append('.*')
            i += 2
        elif pattern[i] == '*':
            out.append('[^/]*')
            i += 1
        elif pattern[i] == '?':
            out.append('[^/]')
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile(''.join(out), re.I)


def matches(path, patterns):
    return any(glob_regex(p).fullmatch(path) for p in patterns)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def globs(value, required=False):
    """A list of globs this matcher can honor: repo-relative, with *, ? and ** only."""
    if not isinstance(value, list) or (required and not value) or not all(map(text, value)):
        return False
    return not any(p.strip().startswith('/') or set(p) & set('{}[]') for p in value)


def validate(data):
    if not isinstance(data, dict):
        return ['the top level must be an object']
    problems = [f'unknown key "{key}"' for key in sorted(set(data) - {'version', 'production', 'protected', 'tests'})]
    if data.get('version') != 1:
        problems.append('"version" must be 1')
    for section, keys in RULE_KEYS.items():
        rules = data.get(section, [])
        if not isinstance(rules, list):
            problems.append(f'"{section}" must be a list')
            continue
        for index, rule in enumerate(rules):
            label = f'{section} rule {index + 1}'
            if not isinstance(rule, dict):
                problems.append(f'{label} must be an object')
                continue
            if text(rule.get('name')):
                label = f'{section} rule "{rule["name"]}"'
            if set(rule) != keys:
                problems.append(f'{label} must have exactly: {", ".join(sorted(keys))}')
                continue
            if rule['action'] not in ACTIONS:
                problems.append(f'{label}: "action" must be deny or ask')
            for key in ('name', 'reason', 'approval'):
                if not text(rule[key]):
                    problems.append(f'{label}: "{key}" must be a non-empty string')
            if section == 'production':
                try:
                    re.compile(rule['match'], re.I | re.S)
                except Exception as error:  # re.error, a non-string, or an overflowing repeat count
                    problems.append(f'{label}: "match" is not a valid regular expression ({error})')
            elif not globs(rule['paths'], required=True):
                problems.append(f'{label}: "paths" must be a non-empty list of repo-relative globs '
                                'using only *, ? and **')
    if not globs(data.get('tests', [])):
        problems.append('"tests" must be a list of repo-relative globs using only *, ? and **')
    return problems


def load_config():
    name = rel(CONFIG)
    try:
        data = json.loads(CONFIG.read_text())
    except OSError as error:
        raise GateError(f'{name} is missing or unreadable ({error.strerror}).')
    except ValueError as error:
        raise GateError(f'{name} is not valid JSON ({error}).')
    problems = validate(data)
    if problems:
        raise GateError(f'{name} is invalid: ' + '; '.join(problems) + '.')
    for section in ('production', 'protected', 'tests'):
        data.setdefault(section, [])
    return data


def read_lock():
    if not LOCK.exists():
        return None
    try:
        lock = json.loads(LOCK.read_text())
        baseline = lock['baseline']
        if not (isinstance(baseline, dict) and all(text(k) and text(v) for k, v in baseline.items())):
            raise ValueError('bad baseline')
        return lock
    except (OSError, ValueError, KeyError, TypeError):
        raise GateError(f'the test-lock state ({rel(LOCK)}) is unreadable.', 'test-lock')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lock_violations(lock):
    changed = []
    for name, expected in lock['baseline'].items():
        try:
            if digest(ROOT / name) != expected:
                changed.append(name)
        except OSError:
            changed.append(f'{name} (missing)')
    return changed


def ensure_state():
    STATE.mkdir(parents=True, exist_ok=True)
    if '.git' not in STATE.parts and not (STATE / '.gitignore').exists():
        (STATE / '.gitignore').write_text('*\n')


def log(decision, gate, tool='', target='', session=''):
    try:
        ensure_state()
        target = SECRETS.sub(lambda m: (m.group('url') or m.group('name')) + '***', str(target))
        entry = {'at': datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
                 'decision': decision, 'gate': gate, 'tool': tool,
                 'target': target[:200], 'session': session}
        with LOG.open('a') as handle:
            handle.write(json.dumps(entry) + '\n')
    except OSError:
        pass


class Call:
    """One tool call under inspection: collects findings, then decides once."""

    def __init__(self, payload):
        self.tool = payload.get('tool_name') or ''
        self.session = payload.get('session_id') or ''
        self.cwd = payload.get('cwd') or str(ROOT)
        self.input = payload.get('tool_input') if isinstance(payload.get('tool_input'), dict) else {}
        self.target = ''
        self.findings = []

    def find(self, action, gate, reason, approval):
        self.findings.append((action, gate, reason, approval))

    def decide(self):
        if not self.findings:
            sys.exit(0)
        self.findings.sort(key=lambda finding: finding[0] != 'deny')
        action, gate, reason, approval = self.findings[0]
        log(action, gate, self.tool, self.target, self.session)
        if action == 'deny':
            print(f'sdlc-gate: BLOCKED [{gate}] {reason}\nApproval route: {approval}', file=sys.stderr)
            sys.exit(2)
        print(json.dumps({'hookSpecificOutput': {
            'hookEventName': 'PreToolUse', 'permissionDecision': 'ask',
            'permissionDecisionReason': f'sdlc-gate [{gate}]: {reason} Approval route: {approval}'}}))
        sys.exit(0)


def real_path(raw, cwd):
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path(cwd) / path
    return os.path.realpath(path)


def within(real, folder):
    # Case-insensitive so a differently-cased spelling cannot step around a rule.
    return (real.lower() + os.sep).startswith(str(folder).lower() + os.sep)


def repo_relative(real):
    if within(real, ROOT) and len(real) > len(str(ROOT)):
        return Path(real[len(str(ROOT)) + 1:]).as_posix()
    return None


def logical(path):
    inner = WORKTREE.match(path)
    return inner.group(1) if inner else path


def is_user_settings(real):
    for name in ('settings.json', 'settings.local.json'):
        candidate = Path.home() / '.claude' / name
        if real.lower() in (str(candidate).lower(), os.path.realpath(candidate).lower()):
            return True
    return False


def lock_reason(lock):
    return f'{lock.get("reason") or "no reason recorded"}; locked {lock.get("locked_at", "earlier")}'


def gate_edit(call, config):
    raw = call.input.get('file_path') or call.input.get('notebook_path')
    if not text(raw):
        raise GateError(f'the {call.tool} event carries no file path.', 'event')
    real = real_path(raw, call.cwd)
    call.target = raw
    if is_user_settings(real):
        call.find('ask', 'self', 'user settings can switch every hook off, including this gate.', SELF_APPROVAL)
    path = repo_relative(real)
    if path is None:
        if within(real, STATE):
            call.find('ask', 'self', f'{real} {SELF_REASON}', SELF_APPROVAL)
        return
    call.target = path
    name = logical(path)
    lock = read_lock()
    if lock and name.lower() in (locked.lower() for locked in lock['baseline']):
        call.find('deny', 'test-lock',
                  f'{name} is frozen by the test lock ({lock_reason(lock)}). Fix the code, not the test.',
                  UNLOCK_ROUTE)
    for rule in config['protected']:
        if matches(name, rule['paths']):
            call.find(rule['action'], f'protected:{rule["name"]}', f'{name}: {rule["reason"]}', rule['approval'])
    if matches(name, SELF_PATHS) or SELF_STATE.match(path):
        call.find('ask', 'self', f'{path} {SELF_REASON}', SELF_APPROVAL)


def git(folder, *args):
    # Well inside the hook's own timeout: a timed-out hook renders no decision at all.
    return subprocess.run(['git', '-C', str(folder), *args], capture_output=True, text=True, timeout=8)


def status_paths(folder):
    """Paths with staged, unstaged or untracked changes under `folder`, relative to it."""
    try:
        prefix = git(folder, 'rev-parse', '--show-prefix')
        if prefix.returncode != 0:
            return []
        status = git(folder, 'status', '--porcelain=v1', '-z', '--untracked-files=all')
    except FileNotFoundError:
        return []
    except (subprocess.TimeoutExpired, OSError):
        raise GateError('git status did not finish in time, so this commit could not be inspected.', 'commit')
    if status.returncode != 0:
        raise GateError('git status failed, so this commit could not be inspected.', 'commit')
    entries, paths, i = status.stdout.split('\0'), [], 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if len(entry) < 4:
            continue
        paths.append(entry[3:])
        if entry[0] in 'RC' and i < len(entries):
            paths.append(entries[i])
            i += 1
    inside = prefix.stdout.strip()
    return [p[len(inside):] for p in paths if p.startswith(inside)]


def changed_paths(cwd):
    """Changes in this checkout, and in the nested worktree the command runs in, if any."""
    found = set(status_paths(ROOT))
    nested = repo_relative(os.path.realpath(cwd))
    tree = WORKTREE_ROOT.match(nested + '/') if nested else None
    if tree:
        found.update(status_paths(ROOT / tree.group(1)))
    return sorted(found)


def gate_commit(call, config):
    lock = read_lock()
    if lock:
        changed = lock_violations(lock)
        if changed:
            call.find('deny', 'test-lock',
                      f'files frozen by the test lock have changed: {", ".join(changed)} ({lock_reason(lock)}). '
                      'If you changed them, put them back and fix the code. If you did not change them, '
                      'leave them alone and tell the user.', UNLOCK_ROUTE)
    try:
        changed = changed_paths(call.cwd)
    except GateError as error:  # a commit the gate cannot inspect goes to the user, not through
        call.find('ask', 'commit', str(error), 'The user approves this prompt, or commits by hand.')
        return
    hits = []
    for path in changed:
        names = [rule['name'] for rule in config['protected'] if matches(path, rule['paths'])]
        if matches(path, SELF_PATHS):
            names.append('gate files')
        if names:
            hits.append(f'{path} [{", ".join(names)}]')
    if hits:
        more = len(hits) - 15
        listing = '; '.join(hits[:15]) + (f'; and {more} more' if more > 0 else '')
        call.find('ask', 'commit',
                  f'protected paths have uncommitted changes this commit may include: {listing}.',
                  'The user approves this prompt after reading the diff, or commits by hand.')


def static_prefix(pattern):
    pattern = pattern.strip()
    return re.split(r'[*?]', pattern[2:] if pattern.startswith('./') else pattern, maxsplit=1)[0]


def inside(name, patterns):
    """True when `name` matches or lies inside a matching tree."""
    return bool(name) and (matches(name, patterns) or matches(name + '/x', patterns))


def scan(command):
    """Simple commands of a shell line, in order, each (words, redirect targets), with '(' and ')'
    where a subshell or a command substitution opens and closes.

    Quotes are honored, so a quoted `>` or `;` is text. Comments and here-document bodies are
    skipped. Raises ValueError on an unclosed quote."""
    items, words, targets, waiting = [], [], [], []
    word, role = None, 'word'  # role of the word being read: word, target, input or heredoc
    i, n = 0, len(command)

    def end_word():
        nonlocal word, role
        if word is not None:  # a role set by `>` waits through the spaces before its word
            {'word': words, 'target': targets, 'heredoc': waiting}.get(role, []).append(word)
            word, role = None, 'word'

    def end_command():
        nonlocal words, targets, role
        end_word()
        items.append((words, targets))
        words, targets, role = [], [], 'word'

    while i < n:
        char = command[i]
        if char == '\\':
            if command[i + 1:i + 2] != '\n':  # a backslash-newline joins two lines
                word = (word or '') + command[i + 1:i + 2]
            i += 2
        elif char == "'":
            close = command.find("'", i + 1)
            if close < 0:
                raise ValueError('unclosed quote')
            word, i = (word or '') + command[i + 1:close], close + 1
        elif char == '"':
            j, piece = i + 1, []
            while j < n and command[j] != '"':
                if command[j] == '\\' and command[j + 1:j + 2] in ('"', '\\', '$', '`'):
                    j += 1
                piece.append(command[j])
                j += 1
            if j >= n:
                raise ValueError('unclosed quote')
            word, i = (word or '') + ''.join(piece), j + 1
        elif char in ' \t\r':
            end_word()
            i += 1
        elif char == '\n':
            end_command()
            i += 1
            while waiting:  # the bodies of the here-documents opened on that line
                delimiter = waiting.pop(0)
                while i < n:
                    stop = command.find('\n', i)
                    stop = n if stop < 0 else stop
                    line, i = command[i:stop], min(stop + 1, n)
                    if line.strip() == delimiter:
                        break
        elif char == '#' and word is None:
            stop = command.find('\n', i)
            i = n if stop < 0 else stop
        elif char == '&' and command[i + 1:i + 2] == '>':  # &> file, &>> file
            end_word()
            role, i = 'target', i + (3 if command[i + 2:i + 3] == '>' else 2)
        elif char in ';|&`':
            end_command()
            i += 1
        elif char in '()':
            end_command()
            items.append(char)
            i += 1
        elif char in '<>':
            if word is not None and word.isdigit():  # the descriptor number of `2>`
                word = None
            end_word()
            j = i
            while j < n and command[j] == char:
                j += 1
            run, i = command[i:j], j
            if command[i:i + 1] == '|':  # >| file
                i += 1
            if command[i:i + 1] == '&':  # >&2 and <&3 name a descriptor, not a file
                j = i + 1
                while j < n and (command[j].isdigit() or command[j] == '-'):
                    j += 1
                if j > i + 1:
                    i = j
                    continue
                i += 1
            if command[i:i + 1] == '-' and run == '<<':
                i += 1
            role = 'target' if char == '>' else 'heredoc' if run == '<<' else 'input'
        else:
            word = (word or '') + char
            i += 1
    end_command()
    return items


def unwrap(words):
    """The command a simple command really runs: past shell keywords, VAR=value prefixes and wrappers."""
    words = list(words)
    while words:
        first = os.path.basename(words[0]).lower()
        if words[0] in KEYWORDS or ASSIGNMENT.match(words[0]):
            words = words[1:]
        elif first in WRAPPERS:
            takes = WRAPPER_VALUES.get(first, ())
            words = words[1:]
            while words and (words[0].startswith('-') or ASSIGNMENT.match(words[0])
                             or (first == 'timeout' and re.fullmatch(r'[\d.]+[smhd]?', words[0]))):
                words = words[2 if words[0] in takes else 1:]
        else:
            break
    return words


def plain_writes(verb, args):
    """(argument, kind) for each path a command plainly writes.

    `gone`: the path is removed, so a folder stands for everything under it. `file`: the path is
    written or replaced. `edit`: written in place, which only an existing file can be."""
    plain = [arg for arg in args if arg and not arg.startswith('-')]
    if verb in REMOVERS:
        return [(arg, 'gone') for arg in plain]
    if verb in FILE_WRITERS:
        return [(arg, 'file') for arg in plain]
    if verb == 'mv' and len(plain) > 1:
        return [(arg, 'gone') for arg in plain[:-1]] + [(plain[-1], 'file')]
    if verb in DESTINATION_WRITERS and len(plain) > 1:
        return [(plain[-1], 'file')]
    if verb in ('sed', 'perl') and any(
            arg.startswith('--in-place') or (re.match(r'-[a-zA-Z]*i', arg) and not arg.startswith(('-M', '-m', '-I')))
            for arg in args):
        return [(arg, 'edit') for arg in plain]
    return []


def resolve(arg, cwd, kind):
    """Repo-relative names an argument refers to; nothing when that cannot be known."""
    arg = os.path.expandvars(os.path.expanduser(arg))
    if not arg or '$' in arg or '`' in arg or (cwd is None and not os.path.isabs(arg)):
        return []
    path = arg if os.path.isabs(arg) else os.path.join(cwd, arg)
    paths = [path]
    if WILDCARD.search(path) and not os.path.lexists(path):
        try:
            paths = glob.glob(path)[:2000]
        except re.error:  # Python 3.9 chokes on some bracket ranges
            paths = []
    names = []
    for item in paths:
        if kind == 'edit' and not os.path.isfile(item):
            continue  # the expression of `sed -i 's/a/b/'` is not a file
        real = os.path.realpath(item)
        if real.lower() == str(ROOT).lower():
            names.append('')
        elif repo_relative(real) is not None:
            names.append(logical(repo_relative(real)))
    return names


def shell_findings(call, config, lock, name, kind):
    label = name or 'the repo root'
    below = name.lower() + '/' if name else ''
    if lock:
        frozen = [path.lower() for path in lock['baseline']]
        if name.lower() in frozen or (kind == 'gone' and any(path.startswith(below) for path in frozen)):
            call.find('deny', 'test-lock',
                      f'{label} is frozen by the test lock ({lock_reason(lock)}). Fix the code, not the test.',
                      UNLOCK_ROUTE)
    for rule in config['protected']:
        above = kind == 'gone' and any(
            static_prefix(p) and static_prefix(p).lower().startswith(below) for p in rule['paths'])
        if above or inside(name, rule['paths']):
            call.find(rule['action'], f'protected:{rule["name"]}', f'{label}: {rule["reason"]}', rule['approval'])
    if name and (matches(name, SELF_PATHS) or SELF_STATE.match(name)):
        call.find('ask', 'self', f'{name} {SELF_REASON}', SELF_APPROVAL)


def gate_shell_writes(call, config, lock, command, cwd, depth=0):
    subshells, previous = [], cwd
    for item in scan(command):
        if item == '(':
            subshells.append(cwd)
            continue
        if item == ')':
            cwd = subshells.pop() if subshells else cwd
            continue
        words, targets = item
        core = unwrap(words)
        verb, args = (os.path.basename(core[0]).lower(), core[1:]) if core else ('', [])
        if verb in ('cd', 'pushd', 'popd'):
            target = '-' if verb == 'popd' else args[0] if args else '~'
            if target == '-':
                cwd, previous = previous, cwd
            elif '$' in target or '`' in target or cwd is None and not os.path.isabs(os.path.expanduser(target)):
                cwd, previous = None, cwd  # somewhere the gate cannot follow
            else:
                cwd, previous = os.path.normpath(os.path.join(cwd or '', os.path.expanduser(target))), cwd
        if (verb in SHELLS or verb == 'eval') and depth < 3:  # bash -c "...", eval "..."
            scripts = [' '.join(args)] if verb == 'eval' else [
                args[i + 1] for i, arg in enumerate(args[:-1]) if re.fullmatch(r'-\w*c', arg)]
            for script in scripts:
                gate_shell_writes(call, config, lock, script, cwd, depth + 1)
        for arg, kind in [(target, 'file') for target in targets] + plain_writes(verb, args):
            for name in resolve(arg, cwd, kind):
                shell_findings(call, config, lock, name, kind)


def gate_command(call, config):
    command = call.input.get('command')
    if not isinstance(command, str):
        if call.tool == 'Monitor':  # a websocket monitor runs no command
            return
        raise GateError(f'the {call.tool} event carries no command.', 'event')
    if not command.strip():
        return
    call.target = command
    # A backslash-newline continues a command; read it as the one line the shell will run.
    flat = re.sub(r'\\\r?\n\s*', ' ', command)
    lock = read_lock()
    try:
        gate_shell_writes(call, config, lock, command, call.cwd)
    except Exception as error:
        # This check is an extra layer with the commit check and the Stop hook behind it. A line it
        # cannot parse, or a fault of its own, lets the command through and never blocks ordinary work.
        if not isinstance(error, ValueError):
            log('error', 'shell-check', call.tool, f'{type(error).__name__}: {error}', call.session)
    for rule in config['production']:
        if re.search(rule['match'], flat, re.I | re.S):
            call.find(rule['action'], f'production:{rule["name"]}', rule['reason'], rule['approval'])
    if SELF_BASH.search(flat) and not any(safe.match(flat) for safe in SELF_BASH_SAFE):
        call.find('ask', 'self', 'this command touches the gate files; changing them changes what the gate enforces.',
                  SELF_APPROVAL)
    if COMMIT.search(flat):
        gate_commit(call, config)


def hook_stop(payload):
    try:
        lock = read_lock()
        changed = lock_violations(lock) if lock else []
        message = (f'files frozen by the test lock no longer match the lock baseline: {", ".join(changed)}.'
                   if changed else '')
    except GateError as error:
        message = str(error)
    if not message:
        sys.exit(0)
    if payload.get('stop_hook_active'):
        # Already continued once on this. Stop looping and put it in front of the user.
        print(json.dumps({'systemMessage': f'sdlc-gate: the session ended with the test lock violated: {message}'}))
        sys.exit(0)
    log('block-stop', 'test-lock', 'Stop', message, payload.get('session_id') or '')
    print(f'sdlc-gate: BLOCKED [test-lock] {message}\n'
          'If you changed them, put them back and fix the code instead. If you did not change them, '
          'leave them alone and tell the user: they may have edited the test by hand.\n'
          f'{UNLOCK_ROUTE}', file=sys.stderr)
    sys.exit(2)


def run_hook():
    try:
        payload = json.loads(sys.stdin.read())
        if not isinstance(payload, dict):
            raise ValueError('not an object')
    except ValueError:
        print('sdlc-gate: BLOCKED [event] the hook event could not be read.', file=sys.stderr)
        sys.exit(2)
    if payload.get('hook_event_name') == 'Stop':
        hook_stop(payload)
    call = Call(payload)
    if call.tool not in COMMAND_TOOLS and call.tool not in EDIT_TOOLS:
        sys.exit(0)
    try:
        config = load_config()
        if call.tool in COMMAND_TOOLS:
            gate_command(call, config)
        else:
            gate_edit(call, config)
    except GateError as error:
        log('deny', error.gate, call.tool, call.target, call.session)
        repair = ('' if error.gate == 'event' else '\nGated tools stay blocked until the user repairs it by hand '
                  f'(check with: python3 {SCRIPT} check).')
        print(f'sdlc-gate: BLOCKED [{error.gate}] {error}{repair}', file=sys.stderr)
        sys.exit(2)
    call.decide()


def tracked_and_new_files():
    try:
        listing = git(ROOT, 'ls-files', '-z', '--cached', '--others', '--exclude-standard')
        if listing.returncode == 0:
            return [name for name in listing.stdout.split('\0') if name]
    except FileNotFoundError:
        pass
    return [rel(path) for path in ROOT.rglob('*')
            if path.is_file() and '.git' not in path.parts and 'node_modules' not in path.parts]


def cmd_lock(args):
    reason = ''
    if '--reason' in args:
        at = args.index('--reason')
        if at + 1 >= len(args):
            print('lock: --reason needs a value', file=sys.stderr)
            return 1
        reason = args[at + 1]
        args = args[:at] + args[at + 2:]
    if LOCK.exists():
        print(f'lock: a test lock is already set ({rel(LOCK)}); unlock first.', file=sys.stderr)
        return 1
    patterns = args or load_config()['tests']
    files = sorted(name for name in tracked_and_new_files()
                   if matches(name, patterns) and (ROOT / name).is_file())
    if not files:
        print(f'lock: nothing to lock; no file matches {", ".join(patterns) or "(no patterns)"}.', file=sys.stderr)
        return 1
    ensure_state()
    lock = {'version': 1, 'reason': reason, 'patterns': patterns,
            'locked_at': datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
            'baseline': {name: digest(ROOT / name) for name in files}}
    LOCK.write_text(json.dumps(lock, indent=2) + '\n')
    log('lock', 'test-lock', 'cli', ', '.join(files))
    print(f'locked {len(files)} file(s): {", ".join(files)}')
    return 0


def cmd_unlock(_args):
    if not LOCK.exists():
        print('no test lock is set.')
        return 0
    LOCK.unlink()
    log('unlock', 'test-lock', 'cli')
    print('test lock released.')
    return 0


def cmd_check(_args):
    config = load_config()
    print(f'ok: {len(config["production"])} production rule(s), {len(config["protected"])} protected rule(s), '
          f'{len(config["tests"])} test glob(s).')
    return 0


def cmd_status(_args):
    try:
        config = load_config()
        for section in ('production', 'protected'):
            for rule in config[section]:
                what = rule['match'] if section == 'production' else ', '.join(rule['paths'])
                print(f'{section:<10} {rule["action"]:<4} {rule["name"]}: {what}')
        if not (config['production'] or config['protected']):
            print('no production or protected rules; only the built-in gates are active.')
    except GateError as error:
        print(f'config: {error}')
    try:
        lock = read_lock()
        if lock:
            changed = lock_violations(lock)
            print(f'test lock: {len(lock["baseline"])} file(s), {lock_reason(lock)}'
                  + (f'; VIOLATED: {", ".join(changed)}' if changed else '; intact'))
        else:
            print('test lock: none')
    except GateError as error:
        print(f'test lock: {error}')
    if LOG.exists():
        print(f'recent decisions ({rel(LOG)}):')
        for line in LOG.read_text().splitlines()[-10:]:
            print(f'  {line}')
    return 0


COMMANDS = {'lock': cmd_lock, 'unlock': cmd_unlock, 'status': cmd_status, 'check': cmd_check}


def main():
    installed = HERE.parent.name == 'hooks' and HERE.parents[1].name == '.claude'
    if len(sys.argv) > 1:
        if not installed or sys.argv[1] not in COMMANDS:
            print(f'usage: python3 {SCRIPT} lock [--reason TEXT] [GLOB ...] | unlock | status | check\n'
                  '(run the copy installed in a repo, not the kit source)', file=sys.stderr)
            sys.exit(1)
        try:
            sys.exit(COMMANDS[sys.argv[1]](sys.argv[2:]))
        except GateError as error:
            print(f'sdlc-gate: {error}', file=sys.stderr)
            sys.exit(1)
    try:
        if not installed:
            raise RuntimeError('not installed under .claude/hooks')
        run_hook()
    except SystemExit:
        raise
    except Exception as error:  # a crashed gate must block, never wave the call through
        print(f'sdlc-gate: BLOCKED [internal] the gate failed ({type(error).__name__}: {error}).', file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()
