---
name: design-handoff
description: Produce a lean handoff document for pasting into Claude Design (claude.ai/design). Auto-detects between two modes — (1) data-driven, when the project has a data model (FileMaker DDR, SQL schema, Prisma, API spec, JSON models) and is moving from backend/data work into UI exploration; (2) concept-driven, when the user has a written concept, framework, talk, presentation, methodology pitch, transcript, article, or video they want to riff on, but no data model. Triggers on "hand off to Claude Design", "design handoff", "prepare a Claude Design brief", "ready for Claude Design", "presentation handoff", "concept handoff", "riff on this transcript/article/video", new product/SaaS kickoffs, or moving from concept refinement into visual exploration. The skill extracts what Claude Design cannot guess (entities/fields/rules in data mode; concepts/arc/vocabulary in concept mode) and writes a handoff markdown file. IMPORTANT: deliberately leaves visual direction, palette, typography, imagery, copy tone, and layout decisions to Claude Design — do not specify them in either mode.
---

# Design Handoff

Prepare a lean handoff document for Claude Design (claude.ai/design). Give Claude Design the **structural context it cannot guess** and explicitly delegate **every visual decision** back to it.

## Core principle (universal, both modes)

Claude Design is strong at visual taste. Given even a sparse brief it will invent palettes, typography, hero treatments, imagery, tone, and layout — tastefully. What it *cannot* guess is your structural context — your data model, your concepts, your narrative arc, your vocabulary, your business rules.

**Specify the unguessable. Delegate everything else.**

If you find yourself writing "use a warm palette" or "the hero should feel cozy" — stop. That's Claude Design's job. Delete it. This rule applies in both modes.

## Mode selection

This skill operates in one of two modes:

- **Data mode** — the project has a data model (schema, DDR, ORM, API spec, JSON models). The handoff extracts entities, fields, relationships, and UI-affecting business rules.
- **Concept mode** — the user has a written concept, talk, framework, methodology pitch, transcript, article, or video they want to riff on — but no data model. The handoff extracts concepts, narrative arc, vocabulary, and framing constraints.

**Auto-detect.** Inventory the project. If any data source from the data-mode list below is present and looks like the intended subject of the handoff, default to **data mode**. If only conversation context, transcripts, articles, videos, or written concepts are present, default to **concept mode**. If both are present and it's ambiguous which the user wants to hand off, ask **one** clarifying question and proceed.

Briefly tell the user which mode you picked and why before writing the handoff.

## Inputs to gather

### Data-mode inputs
1. `CLAUDE.md` — product intent, audience, constraints
2. FileMaker DDR exports — `*.xml`, `*_DDR.*`, or anything under `ddr/`, `schema/`
3. Database schema — `schema.sql`, `schema.prisma`, `prisma/schema.prisma`, `models/`, `*.schema.json`, `drizzle/*`
4. API specs — `openapi.yaml`, `swagger.json`, Postman collections
5. ORM models — `models/*.ts`, `src/db/*`
6. Recent context — current Claude Code conversation, recent commits, docs in `docs/`, notes in `.claude/reports/`

### Concept-mode inputs
1. The current Claude Code conversation — concept refinement, decisions made, framing language the user has already settled on
2. Transcripts, source videos, articles, blog posts, or papers in the project directory the user wants to riff on or respond to
3. Existing concept docs, drafts, briefs, outlines, or notes
4. Reference frameworks the user is anchoring on (with attribution to the original author)
5. Sketches, screenshots, or earlier handoff drafts in the project root
6. `CLAUDE.md` if present — audience and constraints

If neither data sources nor a concept can be located, **stop and ask** the user what to hand off. Do not invent either a data model or a concept.

## Workflow

1. **Inventory sources.** List what you found. Pick mode and announce it. Ask one clarifying question only if mode is genuinely ambiguous.
2. **Extract structural context** (mode-dependent — see step 2 sub-steps).
3. **Extract vocabulary.** The exact terms used. Consistency matters for the eventual Code handoff and for audience tracking.
4. **Surface constraints / business rules.** What should the deliverable show, block, warn about, attribute, include, or order?
5. **Identify out-of-scope.** What should Claude Design *not* produce this pass?
6. **Flag tweak candidates.** Features or moves you're unsure about — list them so Claude Design builds them as Tweak variants rather than committing to v1.
7. **Write the handoff** to `DESIGN-HANDOFF.md` in the project root, using the appropriate template.
8. **Tell the user the file path and the paste-in message.** See "Handoff message to user" at the bottom.

### Step 2 — Data mode
- For each major table/model: name, 3–7 key fields, relationships. Skip timestamps, UUIDs, housekeeping fields unless they drive UI.
- Identify 3–5 core user flows as *sequences*, not screen lists. Example: "User creates event → imports guest list → assigns guests to tables → sends save-the-dates."

### Step 2 — Concept mode
- Extract the concepts the audience or end user must hold by the end of the deliverable. Each concept gets: name, 2–5 defining bullets, and relationships to other concepts (e.g., "contrasts with X", "explains why Y", "parallel to Z").
- Identify the narrative arc — the order in which concepts must be introduced for the deliverable to land. Arc steps describe purpose ("establish the old world", "reveal the structural problem"), not screen layouts.

## Output template

Use whichever block applies. Keep sections tight.

### Data-mode template

```markdown
# Design Handoff — [Product Name]

## One-liner
[2–3 sentences. Who it's for, what it does, why it matters. No adjectives about visual style.]

## Data model
### [Entity 1]
- `field_name` — short description
- relationships: [Entity 2] (1:N via X), [Entity 3] (M:N via Y)

### [Entity 2]
...

## Core flows
1. **[Flow name]**: step → step → step
2. ...

## Vocabulary
- **Guest** (not Invitee, not Attendee) — a person invited to the event
- ...

## UI-affecting rules
- [Rule that changes what the UI shows, blocks, or warns about]
- ...

## Out of scope for this handoff
- ...

## Flag as Tweaks (unsure features)
- ...

## Delegation
Claude Design decides: visual direction, palette, typography, imagery, copy tone, layout, hero treatment, tweak affordances, mobile patterns, and all micro-interactions. Use your taste.
```

### Concept-mode template

```markdown
# Design Handoff — [Concept / Talk / Deliverable Name]

## One-liner
[2–3 sentences. What the deliverable argues or demonstrates, who it's for, why it matters. No adjectives about visual style.]

## Conceptual model
### [Concept 1]
- defining bullet
- defining bullet
- relationships: contrasts with [Concept 2], explains [Concept 3]

### [Concept 2]
...

## Narrative arc
1. **[Step purpose]**: what this part of the deliverable establishes
2. **[Step purpose]**: what this part reveals or transitions to
3. ...

## Vocabulary
- **[Term]** — exact meaning, and what it is *not* (if there are common confusions)
- ...

## Constraints (rules that affect the deliverable, not visual style)
- [Required content, ordering, attribution, tonal constraint]
- ...

## Out of scope for this handoff
- ...

## Flag as Tweaks (unsure features)
- ...

## Open inputs still needed
- [Audience / venue / format / length / co-credit decisions only the user can answer]

## Delegation
Claude Design decides: visual direction, palette, typography, imagery, copy tone, layout, hero treatment, slide rhythm, diagram rendering, mobile patterns, and all micro-interactions. Use your taste.
```

## What NOT to include (both modes)

Do not write any of the following into the handoff. They're Claude Design's job:

- Color palette suggestions ("warm", "cozy", "earth tones")
- Typography preferences
- "It should feel [adjective]" sentences
- Hero or imagery direction
- Voice or tone direction beyond constraint-level statements (a tonal constraint like "practitioner-to-practitioner, not breathless hype" is OK; "use friendly copy" is not)
- Layout preferences (sidebar vs topnav, grid vs list)
- Component choices (cards vs table rows)
- Mobile vs desktop patterns beyond form-factor scope
- Micro-copy
- How to render specific diagrams (specify that the diagram exists and what structural facts it must show; don't specify nodes, arrows, looping, or visual emphasis)

If it's not structurally necessary, leave it out. Sparser briefs produce better Claude Design output because the tool has room to design.

## Tiny examples

### Data mode — entity + flow

```markdown
### Event
- `name` — couple names, display in hero
- `date` — drives countdown, RSVP deadlines
- relationships: Guests (1:N), Vendors (1:N), Tasks (1:N)

### Guest
- `rsvp_status` — pending / yes / no — gates table assignment
- `table_number` — nullable until assigned
- relationships: Event (N:1)

## Core flows
1. **Guest onboarding**: Couple creates event → imports guests from CSV → tracks RSVPs → assigns yes-RSVPs to tables
```

### Concept mode — concept + arc

```markdown
### The Old Workflow
- mockup as rationing mechanism for expensive designer time
- two mediums: Figma proprietary primitives vs. shipped code
- relationships: contrasted directly with The New Workflow

### The Compressed Framework
- Define / Research stay; Visualize + Build merge; Test goes continuous
- relationships: parallel to the original 5-step framework

## Narrative arc
1. **Establish the old world**: present the framework intact, with respect
2. **Reveal the structural problem**: translation loss wasn't accidental
3. **Introduce the compressed framework**: same shape, different economics
```

Notice what's *not* there in either example: no colors, no "should feel cozy", no hero treatment, no copy tone, no diagram visual direction.

## Handoff message to user

After writing the file, reply with this shape (fill in the name; use the seed prompt that matches the chosen mode):

> Handoff written to `DESIGN-HANDOFF.md`. Mode: **[data | concept]**.
>
> In Claude Design:
> 1. Open claude.ai/design → new Prototype project
> 2. Import → upload `DESIGN-HANDOFF.md` (or paste its contents into the chat)
> 3. Seed prompt:
>    - Data mode: *"Build [product name]. Core screens only. Use the attached handoff for data model, flows, vocabulary, and constraints. All visual direction is yours — explore freely."*
>    - Concept mode: *"Build [deliverable type, e.g. presentation deck / interactive page] on [topic]. Use the attached handoff for the conceptual model, narrative arc, vocabulary, and constraints. All visual direction is yours — explore freely."*
> 4. When it asks clarifying questions, default to "Decide for me" on anything visual.
