# Recordings

Raw audio/video. **Git-ignored by default** — these files are large and often confidential.

## What goes here

- Zoom recordings (before transcription)
- Screen recordings of the customer's existing system
- Walk-through videos from the customer

## Retention strategy

For long-term retention, push to external storage (OneDrive, Dropbox shared folders, secure S3) and reference the URL from the relevant session entry. Don't try to keep recordings in git.

For short-term — keep it here until you've transcribed it, then delete or archive.

## Why the gitignore

`.gitignore` excludes everything in this folder except `.gitkeep` and `README.md`. If you genuinely need to track a small recording in git for some reason, force-add it (`git add -f`).
