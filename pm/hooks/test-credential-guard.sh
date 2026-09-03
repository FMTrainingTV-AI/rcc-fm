#!/bin/bash
# Regression tests for credential-guard.sh. Run from anywhere:
#   bash pm/hooks/test-credential-guard.sh
# Each case simulates the PreToolUse Bash payload. block = exit 2, allow = exit 0.
# Cases 2, 3, 4, 5, 6 are the bypasses found in the 2026-08-28 review panel.
set -u
HOOK="$(cd "$(dirname "$0")" && pwd)/credential-guard.sh"
pass=0; fail=0

run_hook() { # $1 = command string; runs in current dir
  python3 -c 'import json,sys; print(json.dumps({"tool_input":{"command":sys.argv[1]}}))' "$1" \
    | bash "$HOOK" >/dev/null 2>&1
}

check() { # $1 = desc, $2 = block|allow, $3 = command
  run_hook "$3"
  local rc=$?
  local want=0; [ "$2" = block ] && want=2
  if [ "$rc" -eq "$want" ]; then
    pass=$((pass+1)); echo "  ok   [$2] $1"
  else
    fail=$((fail+1)); echo "  FAIL [$2, got rc=$rc] $1 :: $3"
  fi
}

tmp=$(mktemp -d) && cd "$tmp" || exit 1
git init -q
git config user.email t@example.com; git config user.name t

# Fixtures
echo secret > .env
echo readme > README.md
echo example > .env.example
mkdir somedir Secrets cleandir "sub repo"
echo secret > somedir/.env
echo token > Secrets/token.txt
echo clean > cleandir/notes.md
echo secret > "sub repo/.env"
echo '{}' > credentials.json
git add README.md credentials.json 2>/dev/null; git commit -qm init
echo changed > credentials.json   # modified tracked credential for -am case

echo "— blocks (each was a bypass or core case) —"
check "plain add of .env"                       block "git add .env"
check "add-then-commit chain"                   block "git add .env && git commit -m test"
check "git stage synonym"                       block "git stage .env"
check "directory operand hides nested .env"     block "git add somedir"
check "case-variant secrets dir"                block "git add Secrets/token.txt"
check "quoted -C path with spaces"              block "git -C \"$tmp/sub repo\" add .env"
check "add -A sweeps untracked .env"            block "git add -A"
check "add . sweeps untracked .env"             block "git add ."
check "commit -am picks up modified credential" block "git commit -am wip"
check "multi-line command"                      block "echo hi
git add .env"

git add .env 2>/dev/null || git add -f .env
check "commit with staged .env"                 block "git commit -m x"
git reset -q .env

echo "— allows —"
check "plain safe add"                          allow "git add README.md"
check "example file allowed"                    allow "git add .env.example"
check "clean directory operand"                 allow "git add cleandir"
check "commit with nothing secret staged"       allow "git commit -m x"
check "non-git command"                         allow "echo hello"
check "git without add/commit"                  allow "git status && git log --oneline"

cd /
notrepo=$(mktemp -d) && cd "$notrepo"
touch .env
check "outside a git repo (fail-open)"          allow "git add .env"

cd /; rm -rf "$tmp" "$notrepo"
echo
echo "passed: $pass  failed: $fail"
[ "$fail" -eq 0 ]
