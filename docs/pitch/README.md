# Pitch materials

- `deck/` — source of the pitch deck (Slides artifact). `deck.json` holds the slide order; each `slides/<id>.html` is one slide with speaker notes in `<aside>`. Images are referenced as `/_blob/<id>` and live in the artifact's asset store.
- `diagrams/` — personal data vault agent diagram (`vault.html` → `vault-agent.png`) and the eight scenarios (`scen.html` → `vault-scenarios.png`). Re-render with `node r.js <html> <png>` (Playwright, 1920×1080 at 2x).

All data shown is synthetic and runs on Testnet. Testnet: test USD stands in for RLUSD.
