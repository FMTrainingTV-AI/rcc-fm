---
name: verify-before-done
description: Evidence before claims — run the actual verification and read its output before saying anything is done, fixed, passing, or working. Use whenever about to claim completion or success in any form: "done", "fixed", "that should work now", "tests pass", marking a task completed, writing a checkpoint or stepping-away entry, or committing. Also use when the user asks "is it working?" or "did that fix it?". The claim and its evidence travel together or the claim doesn't ship.
---

# Verify Before Done

A false "done" costs more than a slow one: the user builds on work that isn't there, and discovering the gap later costs the trust that makes delegation work at all. The fix is mechanical, not moral — never claim what wasn't verified against the *current* state of the work.

## The rule

Verification is proportionate to the change: choose checks that could expose the
actual failure and satisfy project requirements. Reuse current evidence when
the verified artifact has not changed; don't repeat broad suites or add review
rounds without a new risk, change or requirement. A worker's isolated checks do
not replace verification after integration. Keep detailed output in the evidence
record and bring concise results and links into the orchestrator's context.

Before any completion claim, in order:

1. **Name the verification.** What command or check would prove this claim to a skeptic? Tests, build, lint, running the thing, loading the page, calling the endpoint — the check that would catch the failure you'd most plausibly have caused.
2. **Run it fresh** — *after* the last change. A green run from before the latest edit proves nothing about the current state; edits invalidate old evidence, however recent.
3. **Read the output.** Actually read it — exit codes lie by omission (warnings, skipped tests, partial suites). The claim you're allowed to make is exactly what the output supports, no more.
4. **Report claim + evidence together.** "Done — `pytest` 14/14 green, and the new endpoint returns the payload in a manual curl." Not "done, should be good."

## When verification fails or doesn't exist

- **Red result → report it verbatim**, with the output. Never smooth a failure into "mostly working" — a named failure is useful; a hidden one is a trap.
- **Partially done → say which parts.** "The parser works (test output attached); the CLI flag isn't wired yet" beats a rounded-up "done".
- **Nothing runnable proves it** (prose, config for a system you can't reach, a design doc)? Say what *would* verify it and that it wasn't run — "this deploys correctly" becomes "the config matches the docs; I couldn't exercise a real deploy from here." Unverifiable-but-labeled keeps trust; unverifiable-but-confident spends it.

## The excuses, named

| The thought | The reality |
|---|---|
| "Tests passed earlier" | Earlier isn't now. The last edit is exactly the one that breaks things. |
| "The change is too simple to break anything" | Simple changes cause outsized breakage *because* nobody checks them. |
| "It should work" | "Should" is a prediction, not a verification. Run it or say it's a prediction. |
| "Running the suite takes too long" | Then run the relevant subset and say that's what you ran. Scope the claim to the evidence. |

## The CLAUDE.md block

This skill only fires in sessions with the plugin installed. So the rule also ships as a short `## Verifying your work` block — [claude-md-block.md](./claude-md-block.md) — that `pm-scaffold` stamps into a new project's `CLAUDE.md`, and that any existing project can paste in. The block is the floor (it holds without the plugin); this skill is the trigger (it fires on the *claim*, which a CLAUDE.md line can't).

## The ceiling of this skill

This is a **self-report discipline, and self-report is a floor.** It makes the working agent's claims markedly better; it does not make them adjudicative. The reason is structural, not moral: "done" judged from inside the context that produced the work reads intention as if it were the artifact. That misreading is sincere, and running the check yourself doesn't remove it — you still chose which check to run, and you chose it knowing what you meant to build.

So: use this for every completion claim, and don't mistake a passed one for a verdict. **A verdict comes from a party that wasn't there**, executing acceptance criteria written before the work started. See `SDLC.md` § Who adjudicates. This skill's job is to stop the cheap failures — stale evidence, unread output, rounded-up partials — so the adjudicator's time is spent on real questions.

## Where it lands in the pm flow

`checkpoint` and `stepping-away` entries record what shipped — a "shipped" line in a session entry is a completion claim and carries evidence like any other. Tasks move to completed only on verified work; blocked or partial stays honestly in progress with the failure named.
