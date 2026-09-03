---
name: discovery
description: Pre-planning discovery — a loose, conversational riff to find the SHAPE and INTENT of a piece of work before any planning pipeline runs; ends with a committed docs/intent/<slug>.md and a size call (build it now, or chart it with /wayfinder). Use at the very start of anything non-trivial — "I've been thinking about X", "let's talk through Y", "I want to do something with Z", "what would it take to…", "let's discover/riff/think out loud" — and whenever the user is describing a problem rather than requesting a change. This is the stage BEFORE /wayfinder or plan mode, not a replacement for them; it exists because wayfinder's opening grill is heavy and goes far better when fed a shaped intent. Do NOT use for trivial edits (just do them), for work that already has an intent or spec (go to the next stage), or once the user has said "let's build" (hand off).
---

# Discovery

The stage before planning. A conversation, not an interview: the user thinks out loud, you think with them, and the two of you find the shape of the thing — what problem, what outcome, who's affected, what's fixed, what's still open. When the shape holds still, you write it down as an **intent** and make a **size call**. That's the whole job. You don't design, you don't plan, you don't build.

Why it exists: Matt Pocock's `/wayfinder` opens with a breadth-first grill because it assumes it starts from nothing. Its grilling is the heaviest part of the stack. Feed it an intent you've already riffed into shape and it has far less to ask. Discovery is the on-ramp; wayfinder and plan mode are the road.

## Posture

- **Riff, don't interrogate.** No one-question-at-a-time, no multiple-choice menus, no five-question budget. Respond to what was said, push back where it's soft, offer a reframe when one is visible, ask the thing you'd actually want to know next. The user leads the pace.
- **Chase shape, not detail.** The failure mode is nailing down implementation before the outcome is agreed. If the conversation drifts into "which table / which library / which endpoint", pull it back up: "that's a planning question — park it under open questions."
- **Say what you think.** Discovery is where a wrong premise is cheapest to kill. If the problem as stated isn't the real problem, or the outcome doesn't fix it, say so in a sentence and keep going.
- **Read before riffing.** If the project has `docs/intent/`, `docs/adr/`, `CONTEXT.md`, or `_pm/skeleton.md`, read them first — the user shouldn't have to re-explain what the repo already records. Check whether an intent for this already exists; if so, you're updating it, not starting over.
- **Don't fake convergence.** "Are we clean on the shape?" is a real question. If the user is still circling, keep riffing. If they've said "let's move on" or the last two exchanges added nothing, it's time to write.

## When the shape holds still — write the intent

One file, committed, in the shared record:

- `docs/intent/<slug>.md` — this is **shared** engineering record (the next stage reads it; a collaborator or client can read it), so it lives in `docs/`, never in `_pm/`.
- Template: [intent-template.md](./intent-template.md). Sections: Problem · Proposed outcome · Affected users and systems · Constraints · Open questions · Size call. Header carries author, status, date, and a source line (what prompted this — a conversation, an article, an incident).
- Write it in the user's terms. Open questions are the fog — things you can tell are coming but can't phrase sharply yet. Don't resolve them here; that's what the next stage is for.
- Show it before committing. The user corrects misunderstandings; you commit the intent **on its own** as the first artifact in the chain. (Never batch it with code.)

## The size call — last section of the intent, and the handoff

Count unknowns, not files. Two answers:

- **Fits one session** → no map. Hand off directly: Claude Code plan mode, or `/implement` / `/tdd` for disciplined execution, with the intent as the brief. Record "Size: one session" in the intent.
- **Multi-session / foggy** → `/wayfinder`, with the intent attached and the destination taken from the intent's *Proposed outcome*. Record "Size: multi-session → wayfinder" plus the destination sentence. `/wayfinder` is user-invoked — tell the user the command, don't try to run it.

A third case: if the riff reveals the work is trivial (rename, config flip, one-liner), say so and don't write an intent at all. Discovery shouldn't ceremonialize small things any more than it should rush big ones.

## Terminal state

Intent committed, size call made, next stage named. Discovery stops here. If the user keeps talking design, that's fine — but it's the next stage's conversation now, and the appropriate skill owns it. See the plugin's `WORKFLOW.md` for the full stage chain.
