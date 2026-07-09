# Skeleton — <Project Name>

> The default planning artifact. Wei Hao's 5-step structure (Direct Impact Solutions, Elevate FM 2026). For a change-request job this might be a paragraph. For a six-month engagement it's a longer doc. **One artifact that scales with content** — there is no small-vs-big template.
>
> Replace this blockquote with real content. Or delete the blockquote and write a one-paragraph version for tiny jobs.

## Outcome

_One sentence._ After this release, **\<user/role\>** can **\<do X\>**.

## The one user journey that must stay intact

_The critical path — end to end. This is the proof of value. If this journey breaks, the project has failed regardless of what else shipped._

1. Step one.
2. Step two.
3. Step three.

## Minimum capabilities

_Only what, if removed, would break the journey above. Nothing aspirational. Nothing flashy._

- Capability A
- Capability B

## Fundamental enablers

_Minimum data, roles, permissions, basic status visibility, safety, compliance basics. These are the unglamorous things that make the release **usable, testable, and releasable.** Don't defer security to phase two — it doesn't work._

- Enabler A
- Enabler B

## Non-negotiables

_The fixed walls. Budget, timeline, capacity, regulatory constraints. Things that are fixed whether we like it or not._

- Constraint A
- Constraint B

---

## Quick test for any candidate story

A story belongs in the skeleton **only if** it makes at least one of these true:

- Without it, the core journey cannot be completed.
- Without it, the release is not usable or safe for intended users.
- Without it, the release is not testable or releasable.

If none of the three are true, the story is not part of the skeleton. It may still have value — but it goes to the backlog, not the skeleton.

---

## How this artifact is used

- **Day one:** write the skeleton, even if it's a paragraph. Use the 5-step structure for anything beyond a quick fix.
- **Ongoing:** the `whats-next` skill reads this when proposing what to pick up. New requests get compared to it in conversation (Wei Hao's "if this comes in, what comes out?"). Every month or so, re-read the skeleton and compare to what's actively being built (Wei Hao's flavor-check) — if they've drifted apart, either reshape the backlog or rewrite the skeleton.
- **When the goal genuinely changes:** rewrite the skeleton. Don't paper over a goal change by stretching the old skeleton.

The skeleton is **not** a deliverable — it's an alignment artifact. Customers usually don't see it directly; they see user stories and prototypes generated from it.
