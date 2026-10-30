# Later

Deferred from the 7-day plan. Each is a known gap, not a hidden one.

- LLM grading of site English (`llm_english_grade` is configured in `scoring.yaml` but never produced; prompt `ENGLISH_GRADE_V1` not written).
- `/funnel`: % lost per reason per stage. Needs the lost reason stored as a field rather than in the stage-change activity text.
- Overclaim flag: stated seats/years in replies vs. what the site shows.
- Discovery candidate review (accept/reject) before candidates become partners; today discovery upserts partners directly.
- Discovery as a background job returning 202 + polling; today it runs inside the request.
- Drag-and-drop on the board (move buttons today).
- Attention priority 1 ("replied and gates look good") does not yet look at gate status.
- `size._extract_years` computes "since 2005" against a hardcoded 2026.
- Short ADRs in `docs/decisions/`.
- Playwright smoke test.
