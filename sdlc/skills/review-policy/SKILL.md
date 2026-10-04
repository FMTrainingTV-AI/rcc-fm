---
name: review-policy
description: Use when a repo has no written review policy, or when reviews of it disagree about what matters, bury real findings under style nits, or never check the change against its intent, spec or plan. Also when the user says "set up REVIEW.md", "tune the review", "review this against our policy", or wants a diff reviewed by something that did not write it.
---

# Review policy

`REVIEW.md` at the repo root is the standing policy every review of the repo reads: which passes to run, what counts as Important, how many nits to report, what to leave alone. It says how to review, never when. Whether a change gets a review is the project workflow's call.

Claude Code's managed Code Review reads `REVIEW.md` on GitHub pull requests. The local `/code-review` command does not. The reviewer in this plugin does, so the same policy applies before a pull request exists.

## Set up or tune REVIEW.md

1. Copy `${CLAUDE_PLUGIN_ROOT}/templates/REVIEW.md` to the repo root. If the repo has one, edit it in place.
2. Fill it in with the user:
   - **Compliance sources.** Where this repo keeps the accepted intent, spec and plan. Without them a review cannot say whether the change did what was asked.
   - **Important.** What breaks behavior, leaks data or breaches a rule written in this repo. Everything else is a nit.
   - **Do not report.** Generated paths, and anything a linter, a CI check or a gate hook already enforces.
3. Keep it under a page. A long policy dilutes the rules that matter.
4. Commit it. A change to it is reviewed like code.

Tune it when a finding keeps being dismissed (move it to Do not report, or down to a nit) or keeps being missed (add a repo-specific check). Record the change in the file's tuning log.

## Run a policy review

The reviewer is never the session that wrote the change.

1. Fix the scope: the base and head revisions, and the intent, spec or plan files the change answers to.
2. Write the diff to a file outside the tracked tree, for example `git diff <base>...<head> > <scratch>/review.diff`. Use plain `git diff` for uncommitted work.
3. Dispatch the `sdlc:policy-reviewer` agent with the diff path, the repo root and the artifact paths, and nothing else. Give it no summary of what the change is meant to do and no account of how it was built. It judges what is on the page. Name every path it will need: on macOS and Linux the reviewer can read files but has no tool to search or list them.
4. Give every finding a disposition: fix, decline with a reason, or ask the user. Record the findings and dispositions where this repo keeps its review record, which is the pull request thread or the ticket.
5. A finding that turns up for the second time goes into `CLAUDE.md` as a correction in the same pass, so the next session does not repeat it.

Findings inform. They do not approve or block. A person approves.

The reviewer is a same-model pass with a fresh context, the tier of `/code-review`. It is not a second vendor's opinion. For a risky change, pm's `adversary-review` skill runs a hostile pass with its own subagent, and that reviewer reads this same `REVIEW.md`.
