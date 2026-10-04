#!/usr/bin/env python3
"""Install or refresh the sdlc gate kit in a repo.

Copies kit/sdlc_gate.py to <repo>/.claude/hooks/, creates .claude/sdlc/gates.json
from the starter when the repo has none, and adds the PreToolUse and Stop hook
entries to .claude/settings.json. Everything it replaces is copied to
.claude/sdlc/state/backups/ first. An existing gates.json is never touched.
Safe to run again: a second run changes nothing.
"""
import argparse
import datetime
import json
from pathlib import Path
import sys

KIT = Path(__file__).resolve().parents[1] / 'kit'
MARKER = '.claude/hooks/sdlc_gate.py'
MATCHER = 'Bash|Monitor|Edit|Write|NotebookEdit'
GATE = 'g="$CLAUDE_PROJECT_DIR/' + MARKER + '"; '
# Claude Code blocks a tool call only on exit 2. A missing python3 (127), a broken shim or a
# half-written script (1) would all read as "proceed", so every other failure becomes a 2 here.
GUARD = (GATE + 'python3 "$g"; s=$?; case "$s" in 0|2) exit "$s" ;; *) '
         'echo "sdlc-gate: BLOCKED [runtime] the gate could not run (python3 exit $s), so this call was not checked." >&2; '
         'exit 2 ;; esac')
# Stop is the opposite: only the gate's own verdict may hold a session open, never a broken runtime.
STOP = GATE + '[ -f "$g" ] && command -v python3 >/dev/null 2>&1 || exit 0; python3 "$g"'


def hook(command):
    return {'type': 'command', 'command': command, 'timeout': 60}


def ours(group):
    return any(MARKER in str(hook.get('command', '')) for hook in group.get('hooks', []) if isinstance(hook, dict))


def merge_hooks(settings):
    hooks = settings.setdefault('hooks', {})
    if not isinstance(hooks, dict):
        raise ValueError('"hooks" is not an object')
    for event, group in (('PreToolUse', {'matcher': MATCHER, 'hooks': [hook(GUARD)]}),
                         ('Stop', {'hooks': [hook(STOP)]})):
        groups = hooks.setdefault(event, [])
        if not isinstance(groups, list) or not all(isinstance(g, dict) for g in groups):
            raise ValueError(f'"hooks.{event}" is not a list of objects')
        kept = [g for g in groups if not ours(g)]
        at = next((i for i, g in enumerate(groups) if ours(g)), len(kept))
        hooks[event] = kept[:at] + [group] + kept[at:]
    return settings


def lock_home(repo):
    """Where the installed gate keeps its lock and log; mirrors state_dir() in the kit."""
    dot_git = repo / '.git'
    if dot_git.is_dir():
        return '.git/sdlc-gate/'
    if dot_git.is_file():  # a worktree or submodule keeps a pointer file here
        return "this checkout's own git directory"
    return None  # no git: the state folder holds them


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--repo', required=True, help='root of the repo to install into')
    parser.add_argument('--dry-run', action='store_true', help='say what would change; write nothing')
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    if not repo.is_dir():
        print(f'install_gates: {args.repo} is not a directory.', file=sys.stderr)
        return 1
    # `--repo .` from the wrong directory installs gates into the wrong repo; say where this is going.
    print(f'target: {repo}')

    settings_path = repo / '.claude/settings.json'
    gate_path = repo / MARKER
    config_path = repo / '.claude/sdlc/gates.json'
    state = repo / '.claude/sdlc/state'
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')

    # Read and merge before writing anything, so a bad settings file leaves the repo untouched.
    old_settings = settings_path.read_text() if settings_path.exists() else None
    try:
        settings = json.loads(old_settings) if old_settings is not None else {}
        if not isinstance(settings, dict):
            raise ValueError('the top level is not an object')
        new_settings = json.dumps(merge_hooks(settings), indent=2) + '\n'
    except ValueError as error:
        print(f'install_gates: {settings_path} could not be merged ({error}); nothing was written.', file=sys.stderr)
        return 1

    kit_gate = (KIT / 'sdlc_gate.py').read_bytes()
    old_gate = gate_path.read_bytes() if gate_path.exists() else None
    plan = []
    if old_gate != kit_gate:
        plan.append(('gate', f'{"update" if old_gate is not None else "install"} {MARKER}'))
    if not config_path.exists():
        plan.append(('config', 'create .claude/sdlc/gates.json from the starter (no rules yet)'))
    if old_settings != new_settings:
        plan.append(('settings', 'add the sdlc-gate PreToolUse and Stop hooks to .claude/settings.json'))
    if not (state / '.gitignore').exists():
        home = lock_home(repo)
        where = (f'for backups (ignored by git); the lock and log are kept in {home}' if home
                 else '(lock, log and backups; ignored by git)')
        plan.append(('state', f'create .claude/sdlc/state/ {where}'))

    if not plan:
        print('install_gates: unchanged; the kit is already installed and current.')
        return 0
    for _, line in plan:
        print(('would ' if args.dry_run else '') + line)
    if args.dry_run:
        return 0

    def backup(name, content):
        target = state / 'backups' / f'{name}.{stamp}'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        print(f'backed up the previous {name} to {target.relative_to(repo)}')

    steps = dict(plan)
    state.mkdir(parents=True, exist_ok=True)
    if 'state' in steps:
        (state / '.gitignore').write_text('*\n')
    if 'gate' in steps:
        if old_gate is not None:
            backup('sdlc_gate.py', old_gate)
        gate_path.parent.mkdir(parents=True, exist_ok=True)
        gate_path.write_bytes(kit_gate)
    if 'config' in steps:
        config_path.write_bytes((KIT / 'gates.starter.json').read_bytes())
    if 'settings' in steps:
        if old_settings is not None:
            backup('settings.json', old_settings.encode())
        settings_path.write_text(new_settings)
    print('done. Start a new Claude Code session in this repo before relying on the gates, then prove one.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
