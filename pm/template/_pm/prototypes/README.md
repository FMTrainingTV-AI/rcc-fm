# Prototypes

HTML mockups for customer validation. Charlie Bailey's pattern: high-fidelity in 30–45 minutes, send to the customer, get reactions, iterate.

## Why HTML over paper

Paper prototypes are great because they're throwaway — nobody defends them. But they require the customer to imagine. HTML prototypes generated quickly with Claude give you the throwaway-ness AND the higher fidelity. Customer sees something close to what they'll get; conversation moves to "I don't like these colors" not "I can't tell what this will look like."

## Workflow

1. Conversation produces enough understanding of the goal.
2. Ask Claude to generate an HTML prototype based on the skeleton + user stories.
3. Iterate in conversation — color, layout, branding. Match the customer's existing system CSS if relevant.
4. Send to customer (single file, paste-and-open simple).
5. Send-bundle goes in `requirements/parrot-back/YYYY-MM-DD-<topic>/attachments/` — keep the validated version there for the historical record.

## Naming

`prototype-<feature-or-flow>-<n>.html` — e.g. `prototype-search-results-v2.html`. Version numbers when you iterate; iteration history matters when the customer says "I liked v1 better."

## Companion mode

In a companion-mode project (e.g. dropped into `datacraft-fm`), use the code starter's existing `dev/`, `webviewer/`, or `web/` folders for prototype work instead — don't duplicate. This `prototypes/` folder is for standalone-mode use.
