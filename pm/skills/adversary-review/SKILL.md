---
name: adversary-review
description: Use when a change needs someone trying to break it before it is trusted - before an intent is delivered, when a change touches live data, permissions, money or production, when a doubt remains after the checks pass, or when the user says "adversary review", "second opinion", "try to break this", "red-team this change". Dispatches a fresh, read-only subagent that did not write the change and reports where it fails its acceptance lines.
---

# Adversary review

The session that wrote a change reads its own intention into it. This skill hands the change to a subagent that was not there, with nothing but the diff, the acceptance lines and the proof, and asks it to find the failure.

It is one bounded review for a named risk. It is not a step after every change.

## When to run it

Run it when one of these is true:

- An intent is about to be delivered (`ship-acceptance` calls this skill).
- The change migrates or deletes live data, touches authentication or permissions, moves money, or runs against production.
- The checks pass and a concrete doubt remains. Say the doubt in one sentence before you dispatch.
- The user asks for it.

Skip it for routine work whose own checks cover the risk. `verify-before-done` still applies to everything.

## Run it

The reviewer is never the session that wrote the change.

1. **Freeze the scope.** The base and head revisions, and where the acceptance lines live: `docs/intent/<slug>.md`, or the item on the task list.
2. **Write the inputs to files** outside the tracked tree:
   - the diff: `git diff <base>...<head> > <scratch>/review.diff` (plain `git diff` for uncommitted work);
   - the evidence: run the checks fresh, after the last edit, and save their full output.
3. **Dispatch the `pm:adversary-reviewer` agent** with the diff path, the repo root, the acceptance path, the evidence path, and `REVIEW.md` if the repo has one. Give it nothing else: no summary of what the change is meant to do, no account of how it was built, no opinion on whether it works. Name every source path it will need, because the reviewer may not be able to search.
4. **Pick the reviewer's model on purpose.** When the host lets you choose a model for a subagent, choose a different Claude model from the one this session runs on, and say which one ran. A different model misses different things. When there is no choice, run it on the same model; the fresh context is still most of the value.
5. **Give every finding a disposition:** fix, decline with a reason, or ask the user. A BROKEN line is fixed and its check re-run, or it stays open. An UNPROVEN line gets real evidence, or it is reported as unproven. Record the findings and dispositions on the task-list item or in the session entry.
6. **A finding that turns up for the second time** goes into `CLAUDE.md` as a correction, so the next session does not repeat it.

## Rounds

One round is the default. A second round needs a material change to the code since the first. After two rounds, what is still open goes to the user with both positions. Do not run rounds until the report comes back clean.

## What it is and is not

- It is a same-vendor review. A subagent shares this session's blind spots more than a person or another vendor's model would. The fresh context, the read-only tools and the withheld summary are what make it worth running.
- It does not approve. Findings inform; a person approves.
- It does not fix. The working session applies the accepted findings and re-runs the checks.
- It is not the policy review. Where the `sdlc` plugin is installed, `sdlc:policy-reviewer` reads a diff against `REVIEW.md` on ordinary changes. This skill is the hostile pass for the risky ones, and it reads `REVIEW.md` too when the repo has it.
