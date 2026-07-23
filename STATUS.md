# Patcy Ops — Status & Handoff
_Last updated: Jul 23, 2026. Resume from here._

## What Patcy Ops is
**One AI operations agent** that runs a back office — and, next, runs the content — with every consequential action gated by a human. The rule the whole system obeys: **Read + draft = free. Act = ask.**

## Owner & accounts (important)
- Built for **Peace Maikasuwa** — `patmaikasuwa@gmail.com`, GitHub `Patcy-AI`. **Not** the Missy / Vero Dawn accounts (GHL etc. are Missy's — don't use them here).
- Repo: `github.com/Patcy-AI/patcy-ops` (branch `main`)
- Local: `~/AI_projects/AI_Agents/patcy-ops`

## What it can do right now (on demo data, fully working)
- Multi-agent pipeline: classify inbox → real **proposal / invoice / TR1 PDFs**, inspector **scheduling** + calendar event, **payment** processing, **follow-ups** (overdue invoices + expiring proposals), client **Q&A**
- **Guardrails**: human-in-the-loop approval queue (payments, DOB filings, sends ≥ $10k) + **prompt-injection scan** on the untrusted inbox (poisoned emails flagged & quarantined)
- **Ask Patcy** conversational layer (Groq; safe template fallback with no key)
- Streamlit console: Approvals · Security · Activity · Documents · Schedule · Follow-ups · Tasks · Ask Patcy
- **9/9 tests**; `Dockerfile` ready for Cloud Run

## Decided stack
| Piece | Choice |
|---|---|
| Ops brain (reasoning) | **Groq** (free/fast) |
| Content brain (writing) | **Claude** — Peace's Anthropic API |
| Memory / database | **Firestore** (GCP serverless) |
| Hosting | **Google Cloud Run** |
| Posting | **Auto-post via Chrome, on approval** (not GHL) |
| Secrets | **Secret Manager** (all keys/tokens) |
| Automation | **Cloud Scheduler** (daily brief) |

## Architecture
Five layers: **Triggers → Connectors → Brain (supervisor + specialists + LLM) → Guardrails → Memory + Outputs.** See the saved artifact **`patcy-ops-architecture`** for the full diagram. Content is a *capability of this same agent* (Trend scan → Claude draft → graphic → approve → Chrome post), not a separate app.

## Progress: ~45% to the full live vision
**Done (the hard, inventive half):** core agent + specialists + docs (~95%), guardrails (~90%), architecture (~95%), conversational scaffold (~65%), voice profile + content foundation (~90%). *(Plus the two flagship security projects — PatcyPay + AI Agent Security Lab — 100%, separate.)*
**Left (the connect-and-deploy half):** real LLM key, Firestore, Peace's connectors, Cloud Run deploy, Secret Manager + Scheduler, content module coded in, meeting-prep/daily-brief.

## Punch-list (in order) — pick up here
1. ✅ Push latest code (this commit)
2. **Add Groq key** → `.env` locally (`GROQ_API_KEY=…`), Secret Manager for cloud → real conversation
3. **Deploy to Cloud Run** (Dockerfile ready) — `gcloud run deploy patcy-ops --source . --region us-central1 --allow-unauthenticated`
4. **Firestore memory** — replace the JSON store so it persists on Cloud Run
5. **Connect Peace's accounts** — Google OAuth (Calendar + Gmail: `credentials.json` + `token.json`), Slack bot token (`xoxb-`)
6. **Content module** — code the trend-scan → Claude-draft → graphic → approve → Chrome-post flow into the console
7. **Meeting prep / daily brief** — calendar → Gmail → research → prep card
8. **Cloud Scheduler** — fire the morning run automatically

## Keys/tokens needed (Peace's — never commit them)
- `GROQ_API_KEY` (console.groq.com) · `ANTHROPIC_API_KEY` (Claude, for content)
- Google OAuth `credentials.json` + `token.json` (Calendar + Gmail)
- Slack `xoxb-` bot token
→ all live in `.env` (local) / **Secret Manager** (cloud). Gitignored.

## Companion files
- **`patcy-ops-architecture`** (saved artifact) — the system diagram
- **`peace-voice-and-content-pack.md`** — voice profile (both modes) + full content pack
- **`content-pack-ai-agent-security.md`** + hero graphic — first grand-slam pack
