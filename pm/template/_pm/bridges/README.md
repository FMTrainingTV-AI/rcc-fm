# Bridges

Manual hand-off between Claude (no PII allowed under most company policies) and another model that CAN handle PII (e.g. enterprise ChatGPT, internal LLM).

## How it works

1. You're working in Claude on a problem that touches PII.
2. Claude detects it can't query the sensitive data and writes a question to `bridges/inbox/CHATGPT-<date>-<n>.md`.
3. You manually take the question to the other model (paste it in).
4. You paste the model's response back into `bridges/outbox/CHATGPT-<date>-<n>.md`.
5. Claude reads the outbox and continues.

## Why manual

Avoids exfiltrating PII through any automated bridge. The human is the boundary — if you decide a question shouldn't go through, you just don't carry it.

## Naming convention

- `<MODEL>-<YYYY-MM-DD>-<n>.md` where MODEL is the target (CHATGPT, GEMINI, etc.) and n increments per day.
- Pair inbox and outbox files by exact filename — `inbox/CHATGPT-2026-06-10-1.md` ↔ `outbox/CHATGPT-2026-06-10-1.md`.

## Folder hygiene

`bridges/inbox/*` and `bridges/outbox/*` are git-ignored by default — contents often contain PII or sensitive context. The READMEs and `.gitkeep` files are committed; everything else stays local.

When you're done with a bridge exchange, delete both files. Don't archive — they're transient by design.
