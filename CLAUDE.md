# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo actually is

This started as a fork of the open-source [suno-api](https://github.com/gcui-art/suno-api) (a Next.js wrapper that automates suno.ai via Playwright/2Captcha). Most of the original project's docs, Docker setup, and demo API routes have since been removed. In practice this repo now serves two purposes at once:

1. **A Next.js API backend** (`src/app/api/*`) exposing tool endpoints — Suno music generation, Midjourney/nano-banana image generation, FFmpeg video composition, CapCut draft generation, YouTube upload/trends, etc.
2. **The definition + runtime home of "DGM"** — a multi-agent YouTube channel automation pipeline (research → concept → music → image → video → upload → QA) driven by Claude Code Agent Teams. Agent roles live in `.claude/agents/*.md`; the pipeline calls back into the Next.js API in (1) as its toolset.

The two halves are tightly coupled: agents in `.claude/agents/` reference the API routes by the code names documented in `.claude/agents/api-reference.md` (e.g. `SUNO_GEN`, `MJ_GEN`, `VIDEO_GEN`, `YT_UPLOAD`), and always call them at `http://localhost:3000` — the Next.js server runs locally on whatever machine is executing the pipeline.

## Commands

```bash
npm install       # install JS deps
npm run dev       # start Next.js dev server on :3000
npm run build     # production build
npm run start     # run production build
npm run lint      # next lint
```

There is no test suite/framework configured (no `test` script, no `*.test.*` files).

Python side (used by `scripts/*.py` and `agents/*.py`, invoked by the API routes and pipeline scripts):
```bash
pip3 install --user -r requirements.txt
```
`requirements.txt` deliberately excludes `pycapcut`/`pymediainfo` (CapCut desktop-app integration) since those only work on Windows and the Linux deployment targets can't use that feature anyway.

## Deployment environments — always be aware of which one you're in

This project has moved hosts multiple times, and code must tolerate that instead of assuming one path layout:
- **Windows native** (original dev target): repo at `C:\suno-api`, Python via `python`, work base `D:\AI Agent\Claude`. Note: `D:` is a removable **exFAT** drive, not NTFS — it doesn't support reparse points, and Node's `readlink` on exFAT throws `EISDIR` instead of `EINVAL` for ordinary files. This broke `next build` once (Next's file-tracing scanned a literal absolute path under `D:\AI Agent\Claude` and crashed on the first file it tried to `readlink`), which is why `next.config.mjs` sets `outputFileTracing: false` and why runtime scripts invoked by API routes (e.g. `scripts/make_capcut_draft.py`) live inside the repo (`C:\suno-api\scripts\`) rather than on `D:\`.
- **VPS (OVH, current production)**: repo at `/home/dgm/suno-api`, Python via `python3`, owned by Linux user `dgm`.
- **RunPod (previous production, retired)**: repo at `/workspace/suno-api`.
- **WSL**: sometimes the dev server accidentally gets started inside WSL instead of Windows native — `src/lib/pythonEnv.ts` (`isRunningInsideWSL`) detects this so the right `python`/`python3` binary is chosen.

`src/lib/serverPaths.ts` and `src/lib/pythonEnv.ts` centralize this environment detection — use `getProjectDir()`/`getWorkBase()`/`getPythonCommand()` rather than hardcoding a path or binary name in a new route or script. When a hardcoded absolute path is unavoidable, try the known deployment roots in order (VPS → RunPod → WSL/Windows), the same pattern used in `.claude/agents/system-developer.md`.

Non-ASCII (Korean) paths break some Windows tooling (ffmpeg/python), so video/image/audio inputs are copied to `C:\temp_dgm_upload\` before being passed to `VIDEO_GEN` etc. — see `.claude/agents/api-reference.md`.

## The DGM agent pipeline

`.claude/agents/*.md` defines the agent roster for the automation team: `orchestrator` (team lead, never spawn it as a teammate), `researcher`, `strategist`, `music-generator`, `image-generator`, `video-producer` (FFmpeg mode) or `capcut-draft-producer` (CapCut mode — mutually exclusive with video-producer), `youtube-uploader`, `qa-inspector`, `qa-tester`, `system-developer`. `.claude/agents/api-reference.md` is the shared contract every agent uses to call the Next.js API by code name instead of raw endpoints.

Pipeline mode is chosen per run: **FFmpeg mode** (default) auto-composes video and auto-uploads to YouTube; **CapCut mode** stops after generating a CapCut draft config for the user to edit and upload manually. `orchestrator.md` has the full state-machine diagram for both.

Hard rules baked into `orchestrator.md` (violating these has caused real incidents — duplicate/broken YouTube uploads, wasted Suno credits, runaway spawning):
- Never spawn a second `orchestrator`-like teammate, and the orchestrator itself is never a teammate in its own team roster.
- Never spawn a duplicate of an agent type that's already working/done in the same project — retry by messaging the existing instance, not by spawning another (duplicate spawns collide on Suno's rate limit and create races).
- QA gates are mandatory, not advisory: `video-producer`/`capcut-draft-producer` only runs after `qa-inspector`'s music pre-check passes (badRatio ≤ 10%), and `youtube-uploader` only runs after the video pre-check passes. Agents must route through `qa-inspector`, not call the next stage directly.
- No detached/background completion-watchers (`nohup`/`disown` polling that fires `SendMessage` later) — poll in the foreground and send the message yourself. A backgrounded watcher caused the same video to upload 8 times in one project.
- When spawning teammates via Agent Teams, pass `model` explicitly (`"sonnet"`, `"opus"`, or `"haiku"` per `orchestrator.md`'s roster) — Agent Teams silently defaults to Opus if the frontmatter `model` field isn't passed explicitly, which is a real billing risk.

Project outputs land in `.claude/agents/projects/{YYMMDD}{seq}/`, one subfolder per agent role (`researcher/`, `strategist/`, `music-generator/`, `image-generator/`, `video-producer/`, `youtube-uploader/`, `qa-inspector/`), plus a root `meeting_log.md`. Regenerated artifacts are backed up as `{filename}_{HHMMSS}.{ext}`; other agents always read the version-suffix-free filename.

`agents/*.sh` + `agents/core/*.py` run the pipeline outside of the interactive Claude Code UI (tmux-based execution on the VPS — `setup-vps.sh`, `agent-worker.sh`, `billing-guard.sh`, `limit-watcher.sh`, `completion-watcher.sh`, `preflight.sh`). `preflight.sh` is a read-only health check (tmux session/windows, OAuth billing mode, disk space, required binaries, Python/Node deps, Next.js server reachability, git sync state) — run it before starting a pipeline batch instead of guessing at VPS state; unlike `setup-vps.sh` it never creates or kills anything. `.claude/skills/vps-tmux-connect/` and `.claude/skills/vps-vscode-connect/` are operator runbooks for connecting to that tmux session — read those (`/vps-tmux-connect`, `/vps-vscode-connect`) before manually touching the VPS session, they document footguns (e.g. never send arrow keys/Ctrl+C into a live orchestrator pane; never re-run `setup-vps.sh` against a live session). `.claude/commands/tmux-connect.md` is the older, now-secondary WSL-local equivalent.

## Skills (`.claude/skills/`)

Project-scoped Skills (as opposed to personal `~/.claude/skills/` ones) live here and are auto-loaded whenever a Claude Code session's working directory is this repo — including each tmux pane running its own agent, since they all check out the same repo. Prefer adding new recurring runbooks/procedures here (`.claude/skills/<name>/SKILL.md`) over growing this file, since skill bodies are only loaded into context when invoked instead of on every turn.

## Harness enforcement (hooks)

`.claude/settings.json` wires up `.claude/hooks/*.js` (plain Node scripts, no external deps like `jq` — Node is guaranteed present everywhere this repo runs) as `PreToolUse`/`SessionStart` hooks so the hard rules above aren't just documentation an agent can misjudge or ignore:
- `pretooluse-bash-guard.js` blocks (exit 2) `tmux send-keys` of navigation/interrupt keys (`C-c`, arrows, etc.) into an `orchestrator` pane, blocks running `claude` with `ANTHROPIC_API_KEY` set inline, and blocks spawning an agent (`--dangerously-skip-permissions`/`--append-system-prompt-file`/`--print`) without an explicit `--model` flag.
- `pretooluse-write-secret-guard.js` blocks `Write`/`Edit` calls that would put secret-shaped content (`password:`, `api_key=`, etc.) into a file `git check-ignore` doesn't already cover, given this repo is public.
- `sessionstart-billing-guard.js` injects a warning into context if a session starts with `ANTHROPIC_API_KEY` set at all (catches the case where the *session itself*, not a command run inside it, is already misconfigured).

These encode real past incidents (2026-06-30 orchestrator pane killed by Ctrl+C, 2026-07-04 26M-token API-key billing, Agent Teams Opus default). When you discover a new incident-worthy failure mode, add a hook for it rather than only writing a rule down — an agent that already violated a documented rule once can't be trusted to read the doc more carefully next time.

## Working across VPS/RunPod/Windows after a fix

Per `.claude/agents/system-developer.md`, a code fix isn't done until it's pushed — the deployment servers pull from `git`, so a fix that isn't pushed to `origin main` will silently reappear after the next server migration or `git pull`.

## Secrets

This is a **public** GitHub repo. `.env` holds `SUNO_COOKIE`/`TWOCAPTCHA_KEY`/browser config (see `.env.example`); YouTube OAuth tokens live in `yt_credentials/` (gitignored). `.claude/commands/` is gitignored wholesale as a standing precaution for operator runbooks that might contain plaintext access info (it currently holds no secrets — VPS access turned out to be key-only, no password needed). Before writing anything path- or credential-shaped into a new file, check whether the target is already covered by `.gitignore` (`git check-ignore -v <path>`); `pretooluse-write-secret-guard.js` (see Harness enforcement below) also catches this at write-time.
