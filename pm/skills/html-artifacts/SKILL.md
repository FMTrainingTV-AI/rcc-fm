---
name: html-artifacts
description: Produce rich, editorial-style HTML artifacts instead of long markdown documents. Use for plans, brainstorms with side-by-side comparison of multiple options, design explorations, weekly/status reports with diagrams, code-review writeups with annotated diffs and severity color-coding, throwaway editing UIs for structured data (with export-to-markdown buttons), design-system snapshots, and verification artifacts comparing intent vs. shipped. Triggers on requests like "brainstorm N approaches to X", "make me a plan for X", "compare these options", "give me a status update on X", "explain this code as an artifact", "help me edit/tune/curate this list/table/config", "prototype this animation", "design this onboarding/checkout/cancellation/OAuth flow" (walk a multi-step user flow step-by-step before building), or any moment where the user would benefit from inline mockups, scannable per-item cards, SVG diagrams, or comparable side-by-side options. DO NOT use for CLAUDE.md instructions, code comments, ADRs, PR descriptions, anything reviewed in PR diffs, or anything grepped/parsed programmatically — markdown is right for those. The skill captures Joe's distilled conventions from Thariq Shihipar's HTML-artifacts approach.
---

# HTML Artifacts

Produce rich HTML artifacts that humans actually engage with — instead of thousand-line markdown documents that get skimmed and rewritten by Claude back to itself.

## Core principle

When agents take on more, the human's job shifts from writing code to deciding what's worth spending compute on. That decision lives in the planning artifact. HTML is the medium that pulls the human back into the loop — they actually look at it, which means they actually argue with it, which means the output gets better. HTML also expresses things markdown can't: tables, design data via CSS, SVG diagrams, inline mockups, interactive elements via JS, spatial layouts. **Say what you mean — don't compress it to ASCII.**

## When to use this

Six recurring shapes:

1. **Specs, planning, brainstorms** — multiple ideas judged against a rubric; implementation plans with mockups; type-interface sketches.
2. **Code review and understanding** — render the actual diff with margin annotations, flowcharts of module interactions, color-coded findings by severity.
3. **Design and prototypes** — live mockups, sliders for tuning animations, component variations side-by-side.
4. **Reports, explainers, status updates** — synthesized writeups with SVG diagrams, annotated code, "gotchas" sections.
5. **Throwaway editing UIs** — purpose-built single-file UIs for editing structured data (see *Escape hatch* below).
6. **Flow walkthroughs** — a single clickable file that walks every step of a multi-step user flow, with mock UI and implementation notes per step (see *Flow walkthroughs* below).

Also useful: design-system snapshots (a living `design-system.html` referenced across projects), verification artifacts ("what I intended vs. what shipped").

## When NOT to use

CLAUDE.md instructions, code comments, ADRs, PR descriptions, anything reviewed in PR diffs, anything grepped or parsed programmatically. Markdown is still the right medium.

## Structural conventions (the part that does the real work)

1. **Framing block at the top.** Before any content, surface constraints and success criteria. *What is this for? What does good look like? What is it NOT?* This is the layer markdown plans almost always skip. Without it, the reader judges ideas in a vacuum.

2. **Per-item cards with a fixed mini-template.** Pick the schema before writing — every item uses the same fields. Examples:
   - Brainstorm card: `WHY THIS` · `VISUAL/EXAMPLE` · `RISK`
   - Plan card: `WHAT YOU GET` · `DEPENDENCIES` · `VERIFICATION`
   - Status card: `WHAT CHANGED` · `WHY IT MATTERS` · `WHAT'S NEXT`

   Consistency across cards is what makes the document scannable. Don't let yourself improvise a different shape for each item.

3. **Inline mockups where visual beats prose.** Wireframe screenshots, before/after snippets, ASCII transitions (`napkin.png → shipped.tsx`). Don't describe an interface — show it.

4. **Code excerpts where types matter.** Type interfaces, function signatures, schema fragments. Not full implementations — the *boundary*.

5. **Tight prose.** Two or three sentences per block. Declarative, voice-y, no throat-clearing. If a paragraph is over four lines, compress it. The visual constraint should pressure the writing to tighten.

## Visual language

The look should feel **editorial, not app-like**. Closer to Stripe Press than Tailwind UI.

**Default palette** (warm family — adjust per artifact but stay warm):
```
--bg:     #F4ECE0   /* warm cream background */
--ink:    #2D241B   /* dark warm brown text — not pure black */
--muted:  #8B7B68   /* muted brown for labels and metadata */
--accent: #C04D2E   /* terracotta for tags, links, highlights */
--rule:   #D9CFC0   /* hairline divider between cards */
```

**Typography:**
- Headlines: serif (Charter, Georgia, system serif), 2–2.5rem, line-height ~1.15
- Body: sans-serif (system-ui, Inter), 16px, line-height ~1.6
- Section labels: small caps, 0.7rem, letter-spacing 0.1em, muted color
- Italics for emphasis. Bold sparingly.

**Layout:**
- Single column, max-width ~65ch
- Generous margins (3–4rem top/bottom)
- Cards separated by hairline rules, NOT boxes or shadows
- Em-dash arrows (`→`) for transitions, not images of arrows
- No chrome, no nav, no dark-mode toggle. It's a document.

## Prompting heuristics

- **Interview before drafting.** If the request is non-trivial, ask the user 5–8 questions first. Surfaces unknown unknowns.
- **Treat the schema as a floor, not a ceiling.** Add fields/sections when content demands it.
- **Don't over-engineer personas.** No "you are an expert planner with 20 years…" framing. Let the structural conventions carry the load.
- **Trust statements work.** "I trust your judgment here" produces better output than "make no mistakes."

## Workflow — a web of artifacts, not one document

Planning is usually multiple HTML files across stages, each kept around as reference:

1. **Explore** — brainstorm 6–8 distinct approaches as one HTML grid, label each with its tradeoff.
2. **Expand** — pick one, deeper HTML showing mockups, type interfaces, data flow.
3. **Plan** — implementation plan in a new HTML file with relevant code excerpts.
4. **Implement** — new session, pass all three files in, build it.
5. **Verify** — point a verification agent at the same files; it has the full intent plus the shipped code to compare.

Keep these files. They become the spec history. Six months later, the *exploration* file tells you what was considered and rejected.

## Flow walkthroughs — planning a multi-step flow before you build it

When the thing being planned is a **multi-step user flow** (onboarding, checkout, cancellation-with-retention, an OAuth handshake), a reading-document falls short — nobody can visualize a flow from prose, and standing up the conditional state to click through it in the real app is most of the work. Build the flow *as* an artifact: one self-contained HTML file you navigate step by step. Reach for this when the flow has 3+ distinct states, has branches (logged-in/out, role-based, error paths), or is hard to reach in the running app.

**This is the one shape where the mock UI should be rough, not editorial.** The per-step mock exists to show *what the user sees and in what order* — not to design the final visuals. Spend the polish budget on the notes, not the pixels; a beautiful mock here invites bikeshedding the wrong layer. Keep your editorial voice for the framing block and the notes; let the mock stay plain.

Structure per step:
- **Step navigation** — next/back plus a "Step N of M" indicator.
- **Two columns** — rough mock UI on the left, technical notes on the right.
- **Technical notes** — the URL, what triggers this step, what state changes, what the backend writes, what events fire. These notes *are* the implementation checklist; a mock without them is just a wireframe.
- **Branch toggles** — when a step has variants, make the branching visible and let the viewer flip between paths.
- **Out-of-band notes** — anything invisible to the user but load-bearing: cron jobs, webhook handlers, a redirect that flashes briefly.

Iterate on the file, never the codebase — don't even open the codebase yet. "Step 3 should come before step 2", "what if they already have an account", "drop the redirect, keep them on the page" are all cheap HTML edits. When the user stops finding things to change, the artifact is the spec: hand it to a **fresh implementation session** with just the file, no planning history. (Same handoff discipline as the *Workflow* web above — rejected variants and dead ends are noise during implementation.) If the user is unsure, offer 2–4 variants of a step — different UX pattern (inline vs. modal vs. dedicated page), different branching strategy, or MVP vs. full scope — so the choice is explicit instead of surfacing as rework later.

## Escape hatch — throwaway editing UIs

When a section of an artifact is annoying to edit in prose (a table of rules, a weighting scheme, a taxonomy, structured choices), don't edit markdown by hand. Build a custom HTML editing UI for *just that section*. Not a product, not a reusable tool — a single purpose-built file.

**Always end with an export button.** "Copy as JSON" / "Copy as markdown" / "Copy as prompt" / "Copy diff." Without the export, the loop doesn't close — the user can't get their edits back into Claude Code or into a file.

Use throwaway editors for: reordering/triaging/bucketing (drag-and-drop kanban); editing structured config (feature flags, env vars, JSON/YAML with constraints); tuning prompts or templates with live preview; curating datasets (approve/reject rows, tag, export selection); annotating documents/transcripts/diffs; picking values painful in text (colors, easing curves, crop regions, cron, regex).

The motto: **edit through the UI, export the result, discard the UI.** Micro software on top of micro software.

## Minimal skeleton

Adapt liberally — every artifact should feel designed for its content, not copied verbatim.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Plan title</title>
<style>
  :root {
    --bg: #F4ECE0; --ink: #2D241B; --muted: #8B7B68;
    --accent: #C04D2E; --rule: #D9CFC0;
  }
  body {
    background: var(--bg); color: var(--ink);
    font: 16px/1.6 ui-sans-serif, system-ui, sans-serif;
    max-width: 65ch; margin: 4rem auto; padding: 0 2rem;
  }
  h1 {
    font-family: Charter, Georgia, serif;
    font-size: 2.5rem; line-height: 1.15; margin: 0 0 1rem;
  }
  .eyebrow {
    font-size: 0.75rem; letter-spacing: 0.15em;
    text-transform: uppercase; color: var(--muted);
    margin-bottom: 0.5rem;
  }
  .meta { font-size: 0.95rem; color: var(--muted); margin-bottom: 3rem; }
  .meta b { color: var(--ink); }
  .card { border-top: 1px solid var(--rule); padding: 2rem 0; }
  .card h2 {
    font-family: Charter, Georgia, serif;
    font-size: 1.4rem; margin: 0 0 0.5rem;
  }
  .tags {
    font-size: 0.75rem; letter-spacing: 0.1em;
    text-transform: uppercase; color: var(--accent);
    margin-bottom: 1rem;
  }
  .row {
    display: grid; grid-template-columns: 8rem 1fr;
    gap: 1rem; font-size: 0.9rem; margin-top: 0.5rem;
  }
  .label {
    text-transform: uppercase; letter-spacing: 0.1em;
    font-size: 0.7rem; color: var(--muted); padding-top: 0.2rem;
  }
</style>
</head>
<body>

<div class="eyebrow">Plan — Project name</div>
<h1>One sharp sentence about what this is.</h1>
<p class="meta">
  <b>Constraints:</b> What we're working with.<br>
  <b>Success looks like:</b> What we want at the end.
</p>

<section class="card">
  <h2>1. Card title.</h2>
  <div class="tags">tag · tag · tag</div>
  <p>Tight prose. Declarative. Two or three sentences.</p>
  <div class="row"><div class="label">Why</div><div>Reason this matters.</div></div>
  <div class="row"><div class="label">How</div><div>Approach in one line.</div></div>
  <div class="row"><div class="label">Risk</div><div>What could go wrong.</div></div>
</section>

</body>
</html>
```

## Output

Write the HTML file to the project (typical locations: `docs/`, `plans/`, or project root). Name it descriptively: `2026-05-20-onboarding-brainstorm.html`, `payments-plan.html`, `weekly-status.html`. Tell the user the path; offer to open it.

For throwaway editing UIs, write to a scratch location and remind the user the file is meant to be discarded after export.

## Deeper reference

The fuller treatment — FAQ, sources, additional patterns — lives in Joe's wiki at `~/Library/Mobile Documents/com~apple~CloudDocs/Obsidian/claude-wiki/claude-wiki/wiki/concepts/html-artifacts-guide.md`. Original source: [Thariq Shihipar's Anthropic blog post](https://claude.com/blog/using-claude-code-the-unreasonable-effectiveness-of-html) + the [live template gallery](https://thariqs.github.io/html-effectiveness/).
