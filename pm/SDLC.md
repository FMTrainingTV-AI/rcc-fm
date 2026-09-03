# The agentic SDLC — the spec

**This is the doctrine layer — the *why*, with no tools named.** It is written to be portable: bind it to whatever stack without stopping to explain itself.

It is not a public standard and nothing is obliged to conform to it. It's the part of the thinking that stays true when the tools change — which is also, conveniently, the part the RCC course can render for an audience that has none of those tools.

---

## The premise

An agent can write more code than a human can read. So review by reading every line stops scaling, and the old proxy for trust — *"I know who wrote this and I know their work"* — stops being available at all.

Trust moves **from the author to the record.** What makes a change trustworthy is no longer whose hand you recognize in it; it's that a chain of artifacts shows who asked for what, what was produced, what was checked, and who approved it. Everything below exists to make that chain exist and to keep it honest.

Two failure modes this guards against, in both directions:

- **Ceremony without evidence** — stages performed, files written, nothing actually run. The record exists and is worthless.
- **Evidence without record** — the work was genuinely checked, but only in a session transcript that nobody will ever read again. The trust dies with the context window.

## The stages

A stage is defined by **which artifact exists** — never by a status someone updates. If the artifact isn't there, the stage hasn't happened, whatever anyone says.

| Stage | The artifact that marks it | Human's role |
|---|---|---|
| **Discover** | A committed intent: the problem, the outcome, who's affected, what's fixed, what's still open, how we'd know it worked | Owns it — the intent is the human's statement of what they want |
| **Chart** | A map of the unknowns, worked down to nothing | Answers the questions only they can answer |
| **Spec** | A specification the intent's outcome can be checked against | Accepts or corrects |
| **Ticket** | Work items with their blocking order | Accepts or corrects |
| **Build** | Diffs and tests | **Gate: approves the plan before code exists** |
| **Verify** | Fresh check output, read; review findings, triaged | **Gate: reads the findings and decides the tail** |
| **Ship** | Evidence the deployed thing works, recorded | **Gate: approves, and applies to production personally** |
| **Learn** | An incident or lesson written as a new intent | Owns it — closing the loop is a judgment call |

Small work collapses Chart → Ticket and runs Discover → Build → Verify → Ship. Trivial edits skip the whole thing; ceremony on a one-liner is how a process earns contempt.

**Learn feeds Discover.** The loop closes or it isn't a lifecycle — a production incident that doesn't re-enter as an intent is a lesson that will be re-learned.

## The artifact chain

Each stage commits a versioned, human-readable file that the next stage consumes. Human-readable and committed are both load-bearing: a chain in a database nobody opens is not a record, and a chain that isn't in version control can't be shown to have existed at the time.

The chain has to **terminate**. A chain that stops at "diffs" proves something was written, never that it worked. Ship's artifact is what makes the whole chain mean anything, and it is the one most often skipped.

## The gates

A gate is a point where the agent stops and a human decides. Three are non-negotiable:

1. **Before code exists.** The human corrects the plan. This is the cheapest correction available anywhere in the lifecycle, and the only one that costs nothing to act on.
2. **After the work goes green.** The agent demonstrates working output; the human reads the findings and decides what applies. Automated review ranks and filters — it does not approve.
3. **Before production.** The human approves, and **the human applies.** The agent never touches production. This one is a boundary, not a preference: it's what keeps an unreviewed action from becoming an irreversible one.

Gates run at stage **boundaries**, never inside a stage. A gate on half-formed work produces noise, and noise trains people to skip gates.

**What a gate must produce:** a written disposition for every finding — applied, held, refuted, or out of scope — with the reason. A finding that vanishes without a disposition is the single most common way a record becomes a lie.

## What must be proven, and when

The stage that gets skipped is Verify→Ship, so the spec is explicit about it.

- **The acceptance checks are written at Discover**, in the intent, in the human's own terms: *how would we know this worked?* Not tests — the outcome, stated so it can be checked.
- **They are run more than once**: against the local or staging article, and again against production after deploy. Same checks, both times. A check that only ever ran locally proves the code compiles somewhere.
- **The output is pasted into the record**, not summarized. Exit codes lie by omission and a summary is where a partial pass becomes a full one.
- **Where nothing runnable can prove it**, the record says so plainly — what would have verified it, and that it wasn't run. Unverifiable-but-labeled keeps trust; unverifiable-but-confident spends it.

## The three steering layers

Guidance and enforcement are different mechanisms and get confused constantly:

| Layer | Nature | Use for |
|---|---|---|
| Instructions and skills | **Advisory** — the agent may reason past it | Judgment, method, house style, when to do what |
| Hooks | **Deterministic** — the agent cannot reason past it | Non-negotiables. Credentials, protected paths, irreversible commands |
| Permissions | **Boundary** — what the agent can reach at all | Calibrating blast radius per project |

The rule: **anything that must never happen is a hook, not a sentence.** If it's written as advice, it will eventually be reasoned past — not from malice, from a plausible-looking exception.

## Shared record vs personal log

Two kinds of writing, and collapsing them corrupts both:

- **Shared record** — intent, decisions, specs, shipped evidence. Authoritative. Collaborators and clients read it. If it disagrees with reality, that's a bug to fix.
- **Personal log** — what I did, what I'm picking up, where I left off. Per-person, append-only, **never authoritative.** If it disagrees with the shared record, the shared record wins, silently and always.

A personal log that starts being treated as state is how two people end up confidently working from different truths.

## What a binding must supply

A binding is complete when it answers all of these. An unanswered row is a real gap, not a matter of style:

1. Which tool or ritual owns each stage, and what its artifact literally is (path and format).
2. Where the intent, the decisions, and the shipped evidence live.
3. Who or what performs the review at each gate, and how findings get their disposition.
4. What "run the acceptance checks" concretely means for this stack — locally and in production.
5. How production is applied, by whom.
6. Which non-negotiables are hooks rather than advice.
7. Where the personal log lives and how it's kept non-authoritative.

## Provenance

Derived from Anthropic's *AI-Native SDLC Playbook*, reviewed against a working consulting stack 2026-08-23, and split out as a portable layer 2026-09-03 (`sdlc/RIFF.md`). The RCC course's bonus-SDLC page is an independent rendering of the same six-stage shape for an audience without this stack.
