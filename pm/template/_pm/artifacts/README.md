# Artifacts

Raw inputs **you** brought in from outside. The opposite of `requirements/` (Claude-generated curated structure) or `docs/` (Claude-managed prose). If it came from a transcript, a customer document, a screenshot, an export — it lives here.

## Layout

- **`transcripts/`** — Zoom downloads, Granola exports, meeting recordings transcribed. Markdown or text. Filename: `YYYY-MM-DD-<topic>.md`.
- **`customer-docs/`** — PDFs, briefs, requirements docs, anything the customer sent. Preserve original format AND drop a markdown version next to it if you want Claude to read it.
- **`exports/`** — DDR XML, JSON schemas, screenshots of existing UI, anything exported from systems you're integrating with.
- **`recordings/`** — raw audio/video, optional. Git-ignored by default (binary, often large). Track via external storage if retention matters.

## Workflow

1. Customer conversation happens → Zoom or Granola transcript → drop in `transcripts/`.
2. Customer sends a brief → drop in `customer-docs/` with the original filename preserved.
3. You export a DDR or screenshot a UI → goes in `exports/`.
4. Then distill into `requirements/` — user stories from transcripts, personas from conversations, acceptance criteria from documents.

## The split

> If it came from outside (`artifacts/`), Claude reads it. If Claude wrote it after reading (`requirements/` or `docs/`), it's curated. The boundary keeps "what the customer said" separate from "what we inferred they meant."

## Naming and dating

Always date-prefix transcripts and exports — they're the historical record. Customer docs keep their original filenames so you can refer to "the doc Sandy emailed me" without renaming-induced confusion.
