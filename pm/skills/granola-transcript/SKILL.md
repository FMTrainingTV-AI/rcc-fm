---
name: granola-transcript
description: Fetch the FULL verbatim transcript of a Granola meeting — not the summary. Use whenever the user pastes a Granola meeting summary and asks for the transcript, drops a notes.granola.ai link, or says "get the full transcript", "pull the transcript for this meeting", "what was actually said". The critical fact this skill exists to carry — the ID in a notes.granola.ai/t/<uuid> link is NOT the meeting UUID the Granola MCP accepts; passing it to get_meeting_transcript always returns "Meeting not found". The reliable path is list_meetings by date range, match the meeting by title/content, then fetch by the REAL id. Do NOT use for summaries or action items (query_granola_meetings handles those directly).
---

# Granola full transcript

Get the verbatim transcript of a meeting from the Granola MCP, starting from what
the user actually has: a pasted summary, a `notes.granola.ai` link, or just "my
call with X yesterday".

## The one fact that matters

**The UUID in a `https://notes.granola.ai/t/<uuid>` link is a share/document id,
not the meeting id.** `get_meeting_transcript(<that-uuid>)` returns
`Meeting not found` every time. Do not try it, do not retry it, and do not
conclude the transcript is inaccessible when it fails — the transcript is there,
you just have to look it up by search instead of by link.

## Recipe

1. **Load the Granola tools.** They are usually deferred. The server prefix is a
   per-machine connector UUID (e.g. `mcp__f3160f4f-…__get_meeting_transcript`) —
   never hardcode it. Use ToolSearch with keyword `granola` or
   `get_meeting_transcript` and take whichever server's tools load.
   - There may be **two** Granola servers: a claude.ai connector (works) and a
     local `granola` server that may be unauthenticated. If a call fails with an
     auth error, try the same-named tool on the other server before giving up.

2. **Find the meeting with `list_meetings`.** Infer the date range from the
   summary content (a "next steps" date, "yesterday", the paste context);
   default to `this_week`, widen to `last_30_days`, then `custom` if needed.
   Match by title and topic — Granola's generated titles paraphrase the content
   (a summary about auction imports matched "Auction platform — end-of-auction
   import, shipping status, and unsold items to eBay").

3. **Fetch with the real id:** `get_meeting_transcript(meeting_id)` using the
   `id` from the `list_meetings` result. Speaker labels: `Me` = the note-taker
   (Joe), `Them` = other participants.

4. If several meetings could match, show the candidates (title + date) and ask,
   or fetch the best match and say which one you picked.

## After you have it

- If the user just wants to work with it (extract decisions, build an intent,
  draft tickets), keep it in context — no file needed.
- If they want it kept, write it to `_pm/transcripts/<date>-<slug>.md` by
  default (create the folder if needed). Transcripts are client
  conversations — **verify `_pm/transcripts/` is gitignored before writing**
  (projects stamped by pm ≥ 0.10 ignore it out of the box; older or foreign
  repos may not — add the ignore line first). Never commit one to a shared
  repo unless the user explicitly says where.

## Don't

- Don't pass the notes.granola.ai URL id to any tool.
- Don't use `query_granola_meetings` when the user asked for the transcript —
  it returns summarized answers, not verbatim text.
- Don't report "Granola can't find it" after one failed id lookup; the search
  path in step 2 is the normal path, not the fallback.
