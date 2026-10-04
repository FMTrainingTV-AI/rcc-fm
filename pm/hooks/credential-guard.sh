#!/bin/bash
# PreToolUse adapter: relevant inspection/runtime failures must block (exit 2).
# Read with builtins so a broken PATH cannot silently disable the guard.
set -u
input=''
line=''
while IFS= read -r line || [ -n "$line" ]; do
  input+="$line"$'\n'
done
[ -z "$input" ] && exit 0
if ! command -v python3 >/dev/null 2>&1; then
  case "$input" in
    *git*|*'$'*|*'`'*) echo 'credential-guard: BLOCKED — python3 unavailable; repair the hook runtime.' >&2; exit 2 ;;
    *) exit 0 ;;
  esac
fi
script_dir="$(cd -- "${BASH_SOURCE[0]%/*}/../scripts" && pwd)" || exit 2
if [ ! -f "$script_dir/credential_guard.py" ]; then
  echo 'credential-guard: BLOCKED — helper missing; repair the plugin installation.' >&2
  exit 2
fi
printf '%s' "$input" | python3 "$script_dir/credential_guard.py"
result=$?
case "$result" in
  0|2) exit "$result" ;;
  *) echo 'credential-guard: BLOCKED — inspection failed; repair the hook runtime.' >&2; exit 2 ;;
esac
