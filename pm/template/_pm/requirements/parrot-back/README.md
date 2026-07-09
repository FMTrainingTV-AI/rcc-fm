# Parrot-back

Validation bundles you've sent the customer. Each bundle is a dated subfolder:

```
parrot-back/
└── 2026-06-10-discovery-validation/
    ├── what-we-sent.md          ← the user stories / mockups / criteria you asked them to confirm
    ├── customer-reply.md         ← their response, if you got one in writing (otherwise: in session log)
    └── attachments/              ← any HTML prototypes, screenshots, etc. you sent
```

## Why parrot-back?

Wei Hao called it "parrot back to make sure we're on the same page." Before going technical, mirror what you heard back to the customer and get explicit confirmation. Catches misunderstanding early — cheap to fix at this stage, expensive after the build starts.

## When to do it

- After every requirements-gathering conversation that produced more than one user story.
- Before writing technical specs.
- When the customer's request feels ambiguous — your gut is right; force the alignment.

## What to include

- The user stories or capabilities, in plain customer language (not technical).
- An HTML prototype if visuals will land better than prose (often the case).
- Explicit "is this right?" framing. Make it easy to disagree.
