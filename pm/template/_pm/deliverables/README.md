# Deliverables

What you hand to the client. Reports, dashboards, formal documents.

## Layout

- **`reports/`** — written deliverables. Status reports, technical specs the customer asked for, analysis documents.
- **`dashboards/`** — live or static dashboards the customer can look at. Charlie's pattern: a small HTML dashboard pulling from milestones / Jira / Asana, dropped into the customer's existing system (e.g. into a FM web viewer) so they see real-time status without ever needing to enter your project repo.

## What makes something a "deliverable"

Two tests:

1. **The customer sees it directly** — not just internal artifacts they might glance at.
2. **It's formally handed over** — emailed, presented, or installed in their system.

If it's an internal working doc, it goes elsewhere (`docs/`, `requirements/`). If it's a working prototype mid-iteration, it's in `prototypes/`. Once a prototype is delivered as the final, it can be copied here or referenced from here.

## Naming

`reports/YYYY-MM-DD-<topic>.md` (or `.pdf`) — dated, scoped.
`dashboards/<feature-or-purpose>.html` — usually undated since the dashboard is a living artifact.
