---
name: ship-acceptance
description: Verify a deliverable against its accepted intent and record the delivery evidence. Use after implementation is verified, when preparing a release, after a person deploys, or when deciding whether an intent is complete. Covers deployed systems and delivered documents or tools. Never deploys production.
---

# Ship acceptance

The last handoff: accepted intent → acceptance checked by someone who did not build it → delivery record. A task-list item can close on its own checks. This procedure decides whether the intent's outcome was delivered.

## 1. Pin what will be checked

Read the accepted `docs/intent/<slug>.md` and the candidate's exact revision (a commit, or a SHA-256 for a file). Copy the Acceptance lines word for word with their IDs (A1, A2, …; number them in the record if the intent did not). If a line needs to change, that goes back to whoever wrote the intent. A line is never weakened to fit what was built.

Create `docs/shipped/` on first write. Use [record-template.md](./record-template.md) for `docs/shipped/<slug>.md`. A retry or a new candidate adds a dated section. A failed result is never overwritten with a pass.

## 2. Check the candidate before release

The evaluator is not the session that built it.

- **Lines a model can check from the code and the check output:** run the `adversary-review` skill on the candidate. Its HOLDS / BROKEN / UNPROVEN verdict per line goes into the record with the evidence it cites.
- **Lines that need the running thing** (a screen, a saved record, a file that arrives): a person performs the check as written, or a session other than the builder performs it and captures what it saw. A screenshot shows what was on screen. It does not show that the data was saved; read the saved state through another route.

Record for each line: ID, pass / fail / not-run, the exact revision, where it ran, who checked, when, and the real output or observation. A missing tool or missing access is **not-run** with the reason, never an assumed pass. An opinion that the code looks right is not a check.

Any required line failed or not run → **blocked**. All pass → **ready-for-release**.

## 3. A person releases

A person applies production. This skill never does. Do not send files or messages to recipients without explicit authorization.

After the person confirms the release and the target is known, confirm the revision that is live and repeat the same lines against it. A different revision from the one checked in step 2 needs step 2 again.

For a delivered document or tool, identify the exact file that was handed over and where it went, and check that file.

## 4. Write the record

Status is one of:

- **blocked**: a required line failed or was not run.
- **ready-for-release**: every line passed before release; not yet released.
- **shipped**: every line passed against what was released.
- **released-with-exceptions**: a person chose to release with a line unmet. The record names the line, who decided, when and why, and the follow-up work. An exception never becomes an unqualified shipped.

For `shipped`, set the intent's `Completion:` line to `shipped · <link to the record>`. For `released-with-exceptions`, set it to `released-with-exceptions · <link>`; `whats-next` keeps showing it until the open tail is accepted. `blocked` and `ready-for-release` leave Completion pending.

Done means the record says what was asked for, what was delivered, what was checked by someone other than the builder, and what remains unproven.
