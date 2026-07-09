# CODING AGENTS: READ THIS FIRST

This folder holds **handoff bundles** from Claude Design (claude.ai/design).

A user mocked up designs in HTML/CSS/JS using an AI design tool, then exported the bundle so a coding agent can implement the designs for real. Bundles typically arrive as a project-slug subfolder (e.g., `my-product/`) containing `project/` (HTML prototypes, CSS, JSX source, uploaded brief) and `chats/` (conversation transcripts).

## What you should do — IMPORTANT

**Read the chat transcripts first.** Transcripts in `<slug>/chats/` show the full back-and-forth between the user and the design assistant — they tell you **what the user actually wants** and **where they landed** after iterating. Don't skip them. The final HTML files are the output; the chat is where the intent lives.

**Read the primary HTML file in full.** The user had a specific file open when they triggered the handoff — it's almost certainly the primary design they want built. Read it top to bottom — don't skim. Then **follow its imports**: open every file it pulls in (shared components, CSS, scripts) so you understand how the pieces fit together before implementing.

**If anything is ambiguous, ask the user to confirm before implementing.** Cheaper to clarify scope up front than to build the wrong thing.

## About the design files

The design medium is **HTML/CSS/JS** — prototypes, not production code. Your job is to **recreate them pixel-perfectly** in whatever technology fits the target codebase (React, Astro, Vue, native — whatever). Match the visual output; don't copy the prototype's internal structure unless it happens to fit.

**Don't render these files in a browser or take screenshots unless the user asks.** Everything you need — dimensions, colors, layout rules — is spelled out in the source. Read the HTML and CSS directly.
