## Verifying your work

Before reporting any task done, fixed, or passing:

- **Run the check fresh** — after the last edit — and **paste its output**. Tests, build, lint, a real request, a screenshot: whichever would catch the failure you'd most plausibly have caused.
- The claim is exactly what the output supports. Red → report it verbatim. Partial → say which parts. Nothing runnable → say what *would* verify it and that it wasn't run.
- Fix the code, not the test. Never skip or delete a failing test to get green.

(Deterministic backing and the full rule: the pm plugin's `verify-before-done` skill.)
