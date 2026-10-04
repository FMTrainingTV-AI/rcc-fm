#!/usr/bin/env python3
"""Bounded shell/Git candidate inspection. Never evaluate shell substitutions.

Unrelated commands and known non-repositories are allowed. Ambiguous candidate
selection or inspection failure for a relevant Git operation blocks. This is a
filename guard for tool calls, not a content scanner or subprocess sandbox.
"""
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

from credential_policy import is_secret

# The word `git` as a command, not the `.git` directory or a `foo.git` remote
# (`grep --exclude-dir=.git … | head` is not a Git pipeline). A leading `/`,
# quote or backslash still counts: `/usr/bin/git`, `"git"` and `\git` run Git.
GIT_WORD = re.compile(r'(?<![.\-])\bgit\b')
RELEVANT = re.compile(GIT_WORD.pattern + r'[\s\S]*?\b(?:add|stage|commit)\b')
SUB = re.compile(r'__CG_SUB_(\d+)__')
# Subcommands that neither stage nor commit. Read-only ones cannot change what a
# later add/commit in the same command would select, so inspection continues
# past them; the rest (index or working-tree changes, remotes, history) end the
# resolvable prefix. Aliases and unknown subcommands are unresolved; use their
# literal expansion.
READ_ONLY_GIT = set('status log diff show branch rev-parse ls-files ls-tree cat-file help version describe blame grep rev-list diff-tree diff-index diff-files check-ignore check-attr for-each-ref ls-remote merge-base count-objects shortlog range-diff name-rev show-ref show-branch check-mailmap check-ref-format whatchanged stripspace var cherry patch-id verify-commit verify-tag verify-pack merge-tree'.split())
OTHER_GIT = READ_ONLY_GIT | set('config init clone fetch pull push remote worktree tag reflog symbolic-ref fsck gc maintenance prune rm mv reset restore checkout switch clean stash merge rebase revert cherry-pick bisect archive apply am format-patch bundle notes submodule sparse-checkout update-index'.split())


class Unresolved(ValueError):
    pass


def literal(value):
    if any(c in value for c in '$`~') or SUB.search(value):
        raise Unresolved('dynamic repository or path argument')
    return value


def mask_heredocs(command):
    """Opaque here-doc bodies are data; their trailing shell commands still count."""
    lines, result, i = command.splitlines(keepends=True), [], 0
    pattern = re.compile(r"<<(-?)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")
    while i < len(lines):
        line = lines[i]; i += 1
        match = pattern.search(line)
        if not match:
            result.append(line); continue
        quote, escaped = '', False
        for c in line[:match.start()]:
            if escaped: escaped = False; continue
            if c == '\\' and quote != "'": escaped = True; continue
            if c in "\"'":
                if not quote: quote = c
                elif quote == c: quote = ''
        if quote:
            result.append(line); continue
        if pattern.search(line, match.end()): raise Unresolved('multiple heredocs require separate commands')
        result.append(line[:match.start()] + line[match.end():])
        body = []
        while i < len(lines):
            value = lines[i].rstrip('\r\n'); i += 1
            if match[1]: value = value.lstrip('\t')
            if value == match[3]: break
            body.append(value)
        else: raise Unresolved('unclosed heredoc')
        if not match[2] and any('$(' in v or '`' in v for v in body):
            raise Unresolved('unquoted heredoc executes substitutions; quote the delimiter or split commands')
    return ''.join(result)


def shell_tokens(command):
    """Extract nested command substitutions; preserve their position and quoted newlines."""
    subs, result, quote, i = [], [], '', 0
    while i < len(command):
        c = command[i]
        if c == '\\' and quote != "'" and i + 1 < len(command):
            if command[i+1] != '\n': result.append(command[i:i+2])
            i += 2; continue
        if quote != "'" and (command.startswith('$(', i) or c == '`'):
            backtick = c == '`'
            start = i + (1 if backtick else 2)
            j, depth, inner_quote = start, 1, ''
            while j < len(command):
                d = command[j]
                if d == '\\' and inner_quote != "'":
                    j += 2; continue
                if d in "\"'":
                    if not inner_quote: inner_quote = d
                    elif inner_quote == d: inner_quote = ''
                if backtick and d == '`': break
                if not backtick and not inner_quote:
                    if d == '(': depth += 1
                    elif d == ')':
                        depth -= 1
                        if depth == 0: break
                j += 1
            if j >= len(command): raise Unresolved('unclosed command substitution')
            subs.append(command[start:j])
            if not quote: result.append('__CG_WORDS__')
            result.append(f'__CG_SUB_{len(subs)-1}__'); i = j + 1; continue
        if c == '$' and not quote:
            result.append('__CG_WORDS__')
        if c in "\"'":
            if not quote: quote = c
            elif quote == c: quote = ''
        result.append(' ; ' if c == '\n' and not quote else c)
        i += 1
    lex = shlex.shlex(''.join(result), posix=True, punctuation_chars='();&|<>')
    lex.whitespace_split = True
    tokens = []
    for token in lex:
        if re.fullmatch(r'[();&|<>]+', token):
            tokens.extend(re.findall(r'&&|\|\||[();&|<>]', token))
        else: tokens.append(token)
    return tokens, subs


def git(cwd, *args, allow_nonrepo=False):
    if cwd is None or not Path(cwd).is_dir():
        raise Unresolved('repository directory cannot be resolved')
    p = subprocess.run(['git', '-C', str(cwd), *args], capture_output=True,
                       timeout=15)
    if p.returncode:
        if allow_nonrepo and b'not a git repository' in p.stderr:
            return None
        raise Unresolved('Git candidate inspection failed')
    return os.fsdecode(p.stdout)


def paths(cwd, *args):
    return [p for p in git(cwd, *args).split('\0') if p]


def candidates(cwd, sub, args):
    """Interpret selection flags separately from message options and operands."""
    operands, flags = [], set()
    i, only_paths = 0, False
    takes_value = {'-m', '--message', '-F', '--file', '-C', '--reuse-message',
                   '-c', '--reedit-message', '--author', '--date', '--cleanup',
                   '--trailer', '--fixup', '--squash', '-t', '--template'}
    allowed_long = {'--all', '--update', '--force', '--intent-to-add', '--no-ignore-removal',
                    '--ignore-errors', '--ignore-missing', '--refresh', '--renormalize',
                    '--verbose', '--quiet', '--dry-run', '--no-verify', '--amend',
                    '--no-edit', '--allow-empty', '--allow-empty-message', '--signoff',
                    '--no-gpg-sign', '--include', '--only', '--no-status', '--status'}
    while i < len(args):
        value = args[i]; i += 1
        if only_paths:
            operands.append(literal(value)); continue
        if value == '--': only_paths = True; continue
        if value.startswith('--pathspec-from-file') or value == '--pathspec-file-nul':
            raise Unresolved('pathspec files require a literal pathspec command')
        if value in takes_value:
            if i == len(args): raise Unresolved('missing option argument')
            i += 1; continue
        if '=' in value and value.split('=', 1)[0] in takes_value:
            continue
        if value.startswith('--'):
            if value not in allowed_long: raise Unresolved('unsupported Git selection option')
            flags.add(value); continue
        if value.startswith('-') and value != '-':
            # Parse short bundles in order: -amMSG has -a plus an attached message.
            for n, flag in enumerate(value[1:], 1):
                if flag in 'mF':
                    if n == len(value)-1:
                        if i == len(args): raise Unresolved('missing message argument')
                        i += 1
                    break
                if flag not in 'AaunfivqoseS':
                    raise Unresolved('unsupported Git short option')
                flags.add('-'+flag)
            continue
        operands.append(literal(value))
    root = git(cwd, 'rev-parse', '--show-toplevel').strip()
    def absolute(base, names):
        return [str(Path(base)/p) for p in names]
    selection = operands or ['.']
    if sub in ('add', 'stage'):
        repo_wide = not operands and bool(flags & {'-A', '--all', '-u', '--update'})
        base = root if repo_wide else cwd
        if not operands and not repo_wide: return []
        modified = paths(base, 'diff', '--relative', '--name-only', '-z', '--diff-filter=ACMRTUXB', '--', *selection)
        if '-u' in flags or '--update' in flags:
            return absolute(base, modified)
        opts = [] if '-f' in flags or '--force' in flags else ['--exclude-standard']
        found = modified + paths(base, 'ls-files', '--others', *opts, '-z', '--', *selection)
        return absolute(base, [p for p in found if os.path.lexists(Path(base)/p)])
    staged = absolute(root, paths(root, 'diff', '--cached', '--name-only', '-z', '--diff-filter=ACMRTUXB'))
    if operands:
        selected = absolute(cwd, [p for p in paths(cwd, 'ls-files', '--cached', '-z', '--', *operands)
                                 if os.path.lexists(Path(cwd)/p)])
        return staged + selected if '-i' in flags or '--include' in flags else selected
    if '-a' in flags or '--all' in flags:
        return staged + absolute(root, paths(root, 'diff', '--name-only', '-z', '--diff-filter=ACMRTUXB'))
    return staged


def inspect_segment(segment, cwd):
    if not segment: return cwd
    args = list(segment)
    env_sensitive = False
    while args and (args[0] in ('command', 'builtin', 'env', 'sudo', 'nohup')
                    or re.match(r'^\w+=', args[0])):
        env_sensitive |= args[0].startswith(('GIT_', 'CDPATH='))
        args.pop(0)
    if not args: return cwd
    if any(marker in args[0] for marker in ('$', '`', '__CG_')):
        raise Unresolved('dynamic command name could invoke Git; use the literal executable')
    if args[0] in ('source', '.', 'eval', 'popd', 'alias', 'unalias'):
        return None
    if args[0] in ('cd', 'pushd'):
        if len(args) == 3 and args[1] == '--': args.pop(1)
        if len(args) != 2: return None
        try: return str(Path(cwd, literal(args[1])).resolve()) if cwd else None
        except Unresolved: return None
    if args[0] in ('echo', 'printf', 'pwd', 'true', 'false', 'test', '[', 'cat', 'head', 'tail'):
        return cwd
    if Path(args[0]).name != 'git':
        if args[0] not in ('echo', 'printf') and (any(Path(a).name == 'git' for a in args[1:])
                or (args[0] in ('sh', 'bash', 'zsh') and GIT_WORD.search(' '.join(args)))):
            raise Unresolved('wrapped Git command; use an explicit literal git -C command')
        return None
    if env_sensitive: raise Unresolved('Git environment changes candidate selection')
    if any('__CG_WORDS__' in arg for arg in args):
        raise Unresolved('unquoted expansion can change Git operands; quote message arguments')
    work = cwd; i = 1
    while i < len(args):
        value = args[i]; i += 1
        if value == '-C':
            if i == len(args): raise Unresolved('missing -C directory')
            work = str(Path(work, literal(args[i])).resolve()) if work else None
            i += 1
        elif value.startswith('-C'):
            work = str(Path(work, literal(value[2:])).resolve()) if work else None
        elif value == '-c':
            if i == len(args): raise Unresolved('missing Git config')
            config = args[i]; i += 1
            if not config.startswith(('user.', 'commit.gpgsign=', 'tag.gpgsign=', 'core.hooksPath=', 'core.quotepath=')):
                raise Unresolved('Git config may change repository selection')
        elif value.startswith('-'):
            raise Unresolved('unsupported global Git option')
        else:
            if value not in ('add', 'stage', 'commit'):
                if value in OTHER_GIT:
                    return cwd if value in READ_ONLY_GIT else None
                raise Unresolved('Git alias or unknown subcommand; use its literal expansion')
            if git(work, 'rev-parse', '--is-inside-work-tree', allow_nonrepo=True) is None:
                return cwd
            found = candidates(work, value, args[i:])
            hits = sorted({p for p in found if is_secret(str(Path(work)/p))})
            if hits: raise Unresolved('credential-shaped files: '+', '.join(repr(p) for p in hits))
            break
    return cwd


def inspect(command, cwd):
    command = mask_heredocs(command)
    tokens, subs = shell_tokens(command)
    stack, segment = [], []
    def finish():
        nonlocal cwd, segment
        for token in segment:
            for match in SUB.finditer(token):
                index = int(match[1])
                if index >= len(subs): raise Unresolved('reserved parser marker in an argument')
                inspect(subs[index], cwd)
        cwd = inspect_segment(segment, cwd)
        segment = []
    for token in tokens:
        if token == '(':
            finish(); stack.append(cwd)
        elif token == ')':
            finish()
            if not stack: raise Unresolved('unbalanced shell group')
            cwd = stack.pop()
        elif token in (';', '&&', '||', '|', '&'):
            if token in ('|', '&') and GIT_WORD.search(command):
                raise Unresolved('pipeline or background Git command; use separate literal commands')
            finish()
        elif token in ('<', '>'):
            # Redirection can supply pathspec input; literal supported commands are clearer.
            if RELEVANT.search(command): raise Unresolved('Git command with redirection is unresolved')
        else: segment.append(token)
    finish()
    if stack: raise Unresolved('unbalanced shell group')


def main():
    try:
        payload = json.load(sys.stdin)
        command = payload.get('tool_input', {}).get('command', '')
    except (ValueError, AttributeError): return 0
    if not isinstance(command, str) or not command.strip(): return 0
    try:
        inspect(command, payload.get('cwd') or os.getcwd())
    except (Unresolved, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f'credential-guard: BLOCKED — {exc}. Use a literal git -C path and explicit safe paths. '
              'Credential deletions and example files are allowed.', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
