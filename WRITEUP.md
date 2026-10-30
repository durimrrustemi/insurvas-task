# Write-up: Partner Outreach Pipeline

A single-user tool that finds BPO call centers and insurance lead vendors worldwide, ranks them with the evidence visible, drafts outreach for a person to approve and tracks each partner from `found` to `signed` or `lost`. Setup: `cp .env.example .env && docker compose up`.

Your answers set the frame: INSURVAS supplies nothing and has no network yet. So discovery is cold and worldwide, the pitch is "we buy your live transfers, start with a test batch", and no ranking can be calibrated against known partners.

## How I find and qualify partners

**Find.** Search queries per country and city (13 countries, in config) go through the Serper API; scraping Google or LinkedIn would break their terms. BPO and lead-vendor queries alternate, so a small run finds both. Directories, job boards, listicles ("Top 40 call centers") and bot-check pages are dropped. For each result, the homepage and up to three inner pages are fetched, respecting robots.txt. The site's own language decides whether it's a vendor or a BPO.

**Qualify.** Four criteria: insurance experience, English, size and compliance. Each is built from signals that store the URL and exact text they came from. There are no labelled outcomes yet, so the weights are priors kept in config, and `make recompute` re-ranks after a change. Unknown stays unknown: a site with only a country prior gets no total instead of a top rank.

**Gates, not weights.** US hours and TCPA compliance are what kill deals later, so they sit outside the score where nothing can average them away. An unknown gate still allows outreach (the first message asks) but blocks test calls; a "no" closes the partner.

## How outreach feels personal, not spammy

- **One concrete hook.** The opening uses one or two facts from that partner's evidence. The prompt forbids claims that aren't in the evidence.
- **The first message qualifies.** BPOs are asked about US hours, seats and consent; vendors about lead sources, consent capture, volume and price per transfer. A reply then tells us something useful.
- **Short, on their channel.** The channel follows the country (WhatsApp in the Philippines, email and LinkedIn in the US). Length limits are enforced in code.
- **Two follow-ups, each with a reason,** then it stops.
- **A person approves and sends every message.**

## What I'd build next with another month

Send approved messages from the user's own accounts and ingest replies. Feed test-call results and lost reasons back into the weights, since those are the first real labels. Add a lost-reason funnel, LLM grading of site English, review of candidates before they enter the pipeline, multi-user ownership, and handing signed partners and their rates to the INSURVAS admin console.

## Where AI helped, and where it got things wrong

**Helped.** AI polished my questions to you, and I built the app with Claude Code. It was fastest at scaffolding (Docker, models, API, UI) and at writing tests. It was most useful once I ran it against real data: most bugs came from real discovery runs and the demo script, not from reading code.

**Got wrong.** Code that looked finished but quietly did something else:
- **Swallowed errors.** A stage change returned 500 after saving, and "Generate outreach" failed on every click; the UI only logged both.
- **Rules on paper only.** The gate checks I specified weren't enforced, and rescoring deleted manual gate decisions.
- **Numbers without provenance.** Seed scores were random, and a blocked US site ranked 100% on the country prior alone.
- **Wrong partners.** The first real run saved Wikipedia and a listicle as partners and filed a lead vendor as a BPO.

Each fix came with a test. Limits: scores are priors until test calls validate them; single user, no auth; the Places source targets Google's legacy API, so the demo uses Serper only; without an Anthropic key every partner gets the same canned draft.
