# The agentic SDLC — the principles

These principles name no tools; bind them to your own stack. The purpose is finished work
with evidence and little supervision. The process earns its place by reducing
mistakes, repeated explanations and recovery effort.

## The useful core

- **Meaningful outcomes.** A ticket names a useful result and how to verify it.
  Implementation steps and worker assignments stay within that ticket. Small
  direct requests need no manufactured ticket hierarchy.
- **One accountable orchestrator.** It owns shared setup, work allocation,
  integration, the record and the user's conversation. Independent workers do
  bounded work; they return evidence and blockers to the orchestrator.
- **A work graph.** Prepare shared dependencies, run independent branches in
  parallel where resources permit, and release downstream work only when its
  inputs are ready. More agents are useful only if they improve net throughput.
- **Proportionate verification.** Run checks that could expose the actual
  failure, including required project checks. Verify the integrated outcome;
  isolated worker success is not enough. Scope claims to what was observed.
- **Concise continuity.** Keep decisions, evidence and next work recoverable
  from the project record. Full worker transcripts do not belong in the
  orchestrator's context or the next session's handoff.

Two failures remain worth guarding against: ceremony with no evidence, and real
verification lost in an unreadable conversation. The answer is a usable record,
not a document for every action.

## Stages are tools, not a compulsory route

| Need | Useful artifact |
|---|---|
| Clarify the outcome | Intent |
| Resolve interdependent unknowns | Decision map |
| State an interface or behavior precisely | Spec |
| Track a useful outcome independently | Ticket |
| Implement it | Code or other deliverable |
| Establish what works | Executed checks and evidence |
| Confirm delivery | Acceptance record for the delivered artifact |
| Prevent a repeated mistake | A concise durable lesson |

Use the artifacts the work needs; reuse existing ones. A well-specified ticket
can go straight to execution. A job spanning several sessions does not itself
need a decision map. Additional planning, review rounds or parallel workers
must address a concrete uncertainty or an explicit project requirement.

## Human decisions and authorization

The human owns intent, scope and permissions. Existing authorization persists
through skills, workers and sessions. Routine authorized work does not need a
new approval because it reached another stage. Ask only for an answer that
changes the work or an action that lacks authorization. Keep genuine questions
in one place and continue independent work while they wait.

Explicit scoped agreements can make grants and budgets machine-readable. They
record actual permission, never create it. Unknown, ambiguous or malformed
agreements grant nothing; host boundaries and the user's instructions outrank
them. Releases, production changes and client communication retain their own
authorization requirements. A local bookkeeping entry is not a release.

## Who adjudicates

Workers provide artifacts and evidence, not an unquestionable "done" verdict.
The orchestrator checks their work against the outcome and tests the integrated
result. A separate reviewer is useful when an unresolved risk needs another
perspective; it is not a required extra conversation after every successful task.
Once a review is chosen, findings receive explicit dispositions. Another round
needs a new reason: changed work, a remaining finding or a required check.

Delivery acceptance remains distinct from ticket completion. When an accepted
intent declares independent evidence channels, prove each at the candidate or
delivered revision as required. A screenshot cannot establish persistence; a
unit test cannot establish that the live user flow worked. Missing checks remain
visible, and an exception is never described as an unqualified pass.

## The three steering layers

User intent and project constraints set the outcome and authority. Skills guide
repeatable work. Deterministic tools enforce checkable properties such as
identity, allowed transitions and evidence completeness. Use the smallest layer
that reliably handles the problem; none can manufacture consent or observed
success. A checklist performed is not proof of a product working.

## Sessions

Manual close, fresh session and a short next-work handoff are the default.
Session count and agent activity are not success metrics; completed outcomes
and user effort are.

## Provenance

The original doctrine was derived from Anthropic's AI-Native SDLC Playbook and
a working consulting stack (2026-08-23 / 2026-09-03). The operating direction
was revised on 2026-09-14 after multi-session pilots: preserve outcomes,
subagents, evidence and handoffs; remove compulsory ceremony and tiny-task
tickets; make extra process conditional. Earlier versions remain in Git.
