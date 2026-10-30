# Write-up: Partner Outreach Pipeline

## What I built

A single-user tool that finds call centers worldwide from public web data, scores them with the evidence visible, drafts outreach for human approval and tracks each center from `found` to `signed` or `lost`. Setup is `cp .env.example .env && docker compose up`; see the README.

Three decisions shaped it:

1. **Cold, worldwide discovery.** INSURVAS has no warm network, so there is nothing to calibrate a ranking against. Every score is therefore a transparent prior: weights live in `config/scoring.yaml`, every signal row stores the URL and text it came from, and unknown stays unknown (`None`, shown as a gap) instead of becoming 0.
2. **Hard requirements are gates, not weights.** US hours and compliance (TCPA) are what kill deals later. They sit outside the score so a strong English score can't average away a compliance "no". A "no" closes the partner; an "unknown" is fine for outreach (the first message asks) but blocks test calls.
3. **Nothing sends itself.** Drafts are grounded in evidence rows, length limits are enforced in code rather than trusted to the prompt, and every message needs a human approval. BPOs reply readily, so the scarce resource is judgment about quality, not message volume.

## Why these sources

Serper (Google results via API) and Google Places, both behind a one-method `Source` protocol. Scraping Google or LinkedIn directly breaks their terms and is brittle. The crawler respects robots.txt, fetches at most four pages per site and caches them for 30 days, so it stays polite and reproducible.

## Where AI got it wrong

I built this with Claude Code. Its mistakes were consistent in kind: code that looks finished but quietly does something else.

- **Errors swallowed in the UI.** Changing a stage returned a 500 *after* the change had been saved, and "Generate outreach" returned a 422 on every click. The frontend logged both to the console, so the UI just looked unresponsive. Only API tests against Postgres surfaced them. All handlers now show the error.
- **Rules that existed only on paper.** My conventions said transitions check gates; the code didn't. The readiness checklist was recomputed in the frontend, and rescoring deleted manual gate decisions. The rules now live in one pure module that the API enforces and the UI only renders.
- **Numbers without provenance.** The seed data had random scores unrelated to its own evidence, which is exactly what the tool is meant to prevent. Seed scores now come from the real formula, and a test guards that.

## Known limits

- Scores are priors until test calls validate them. There are no labelled outcomes yet, so no learned weights.
- Not built from my plan: LLM grading of site English (the signal is configured but never produced), the lost-reason funnel, the overclaim flag, reviewing discovery candidates before they become partners, and drag-and-drop on the board (buttons instead). Discovery runs inside the request rather than in the background.
- Single user, no auth. Replies are logged by hand; nothing is ingested.

## With a month more

Reply ingestion from Gmail and WhatsApp; test-call quality per partner feeding back into the weights (lost reasons and call results are the future labels); multi-user ownership; and handing a signed partner, with its agreed rates, into the INSURVAS admin console.
