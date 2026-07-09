# Requirements

Generated outputs from `artifacts/` — distilled into shapes that drive the build and the customer conversation. Where `artifacts/` is raw input, `requirements/` is curated structure.

## Layout

- **`user-stories.md`** — generated from conversations and customer docs. Standard "as a … I want … so that …" form.
- **`personas.md`** — the stakeholders. Who they are, what they care about, what "done" means to them.
- **`parrot-back/`** — bundles you've sent the customer for validation. Each bundle is a dated subfolder containing the user stories / mockups / acceptance criteria you asked them to confirm, plus their reply if you got one in writing.

## Workflow

1. **Artifacts arrive** in `artifacts/transcripts/`, `artifacts/customer-docs/`, etc.
2. **Distill** with Claude — user stories from transcripts, personas from conversations, acceptance criteria from customer documents.
3. **Parrot back to the customer** for validation before going technical. Drop the validation bundle in `parrot-back/YYYY-MM-DD-<topic>/`.
4. **Iterate** — customer corrections come back, you update the requirements.

## Why this folder is generated, not raw

If it came from outside (transcript, customer brief, screenshot), it belongs in `artifacts/`. If Claude (or you) wrote it after reading artifacts and conversations, it belongs here. The boundary keeps "what the customer said" separate from "what we inferred they meant" — critical when they later say "I never asked for that."

## Skip for small jobs

A change-request job often doesn't warrant user stories or personas — the customer's request IS the requirement. This folder stays empty. That's fine.
