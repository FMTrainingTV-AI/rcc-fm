# Review instructions

How to review changes in this repo. Claude Code's managed Code Review reads this
file, and so does the `sdlc:policy-reviewer` agent. It says how to review, not
when. Keep it under a page.

## Passes

Run each pass and tag every finding with its pass.

- **Bugs**: logic errors, broken edge cases, regressions in behavior the change touches.
- **Security**: injection, missing authentication or authorization, secrets or personal data in code, logs or error messages.
- **Compliance**: the change does what was accepted, no less and no more. Check it against:
  - intent: `<docs/intent/<slug>.md, or where this repo keeps it>`
  - spec and plan: `<path, or "none in this repo">`
  - standing rules: `CLAUDE.md`

## Severity

- **Important**: would break behavior, leak data, or breach a rule written in this repo. `<Name what is always Important here.>`
- **Nit**: style, naming, taste, anything a formatter could settle.

## Nit cap

Report at most five nits. Give the rest as a count.

## Do not report

- Generated files: `<paths>`
- Anything a linter, a CI check or a gate hook already enforces: `<list>`
- Accepted debt that is not this change's job: `<list it>`

## Evidence

Every finding names a file and a line and says what on the page shows it. A
finding that cannot be pointed to is left out.

## Repo-specific checks

- `<A rule to flag every time, for example "a new endpoint has an integration test".>`

## Tuning log

| Date | Change | Why |
|---|---|---|
