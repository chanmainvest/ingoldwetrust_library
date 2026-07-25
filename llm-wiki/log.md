# Log — LLM-Wiki activity

Append-only chronological record of every ingest, query, and lint action.
Header format: `## [YYYY-MM-DD] ingest|query|lint | <short title>`

---

## [2026-07-23] ingest | Wiki initialized

Initialized the LLM-Wiki scaffolding per Karpathy's LLM-Wiki pattern.

- Created `AGENTS.md` (schema / operating rules).
- Created `index.md` (catalog of source corpus + empty concept index).
- Created `concepts/` (empty; pages added during ingest).
- Verified source corpus: 20 annual reports (2007–2026) in `../markdown/`,
  each split into chapters. 2024 has 26 chapters and is the richest sample.

**No concept pages compiled yet.** Candidate themes listed in `index.md` are
placeholders, not authoritative. Actual pages will be created as sources are
ingested and recurring themes are confirmed across ≥2 chapters.

Next step: pick a starting year (2024 recommended — densest TOC) and run the
ingest loop.

---

## [2026-07-23] ingest | Initial concept compilation — 8 thematic pages

Built the first wave of concept pages from a full read of the corpus. Read ~73
representative chapters spanning all 20 years via parallel research passes, then
compiled 8 thematic pages. Each page synthesizes the theme's evolution across
years with verified citations (all 73 source links confirmed to exist).

**Concept pages created:**

- `concepts/de_dollarization.md` — 10 sources (2014, 2017, 2018, 2019, 2020, 2021,
  2022, 2023, 2024, 2026). Traces the arc from speculative sidebar to the 2026
  inversion where the US itself ends the dollar standard.
- `concepts/central_bank_gold.md` — 8 sources (2009, 2011, 2012, 2020, 2024, 2025,
  2026 ×2). From the CBGA selling regime to the 2020s record buying and the
  repatriation wave.
- `concepts/gold_mining_stocks.md` — 10 sources (2008, 2013, 2015, 2016 ×2, 2019,
  2022, 2024, 2026 ×2). The "problem child" → "model student" redemption arc.
- `concepts/monetary_policy_inflation.md` — 10 sources (2010, 2011, 2013, 2014,
  2016, 2022 ×2, 2023, 2024, 2025). The Austrian framing, real rates, monetary
  tectonics, and the directional-call evolution.
- `concepts/sovereign_debt.md` — 10 sources (2011, 2013, 2014, 2015, 2016, 2020,
  2022, 2024, 2025, 2026). Structural over-indebtedness and financial repression.
- `concepts/china_gold.md` — 8 sources (2008, 2009, 2010, 2012, 2014, 2019, 2024,
  2025). China's open + covert accumulation and the system-rivalry dimension.
- `concepts/gold_as_money.md` — 8 sources (2010, 2012, 2013 ×3, 2021 ×2, 2026).
  Stock-to-flow, the regression theorem, 1971, and the remonetization thesis.
- `concepts/bitcoin_vs_gold.md` — 9 sources (2017, 2018 ×2, 2019 ×2, 2020, 2022,
  2024, 2026). The "digital gold" debate and the complementary-hedges thesis.

**Index updated:** chapter counts per year verified via filesystem (total ≈436);
concept index populated; candidate concepts (silver, technical analysis, gold
storage, ESG, confiscations, interviews) listed for future ingest.

**Cross-linking:** each concept page links to its related siblings (e.g.
de_dollarization ↔ central_bank_gold ↔ china_gold). Navigation flows from
`index.md`.

**Observation:** the corpus has strong internal consistency but genuine evolution
over time — notably the de-dollarization yuan walk-back (2026), the inflation-
signal model revision (2024), and the "gold is not the ideal final architecture"
concession (2026). These shifts are recorded in each page's "Nuance" section.

Next: run the lint loop (check for orphan pages, single-citation pages, broken
links) and consider promoting the "silver" candidate to a full page.

---

## [2026-07-23] lint | Post-compilation link check

Ran the first lint pass over all 8 concept pages + `index.md`.

- **128 links checked, 0 broken.** All 73 source citations (`../markdown/...`)
  resolve to real files; all concept cross-links resolve.
- **Fixed:** removed 2 dangling cross-links to `portfolio_diversification.md` —
  a page that was referenced but not created (in `bitcoin_vs_gold.md` and
  `gold_mining_stocks.md`). Added "Gold portfolio diversification" to the
  candidate list in `index.md` instead of stubbing a half-researched page.
- **Orphan check:** no orphans — every concept page has ≥1 incoming cross-link,
  and all are indexed in `index.md`.
- **Citation count:** every concept page cites ≥8 source chapters (the schema
  requires ≥2); the richest (de-dollarization, gold-mining-stocks,
  monetary-policy, sovereign-debt) cite 10 each.

**Status:** wiki is internally consistent and ready for use. No contradictions
flagged at this pass. Candidate concepts (silver, portfolio diversification,
technical analysis, ESG, confiscations, interviews) remain for future ingest.

---

## [2026-07-24] ingest | Second wave — 10 more concept pages

Expanded the wiki from 8 to **18 concept pages** after reading a further ~95
chapters via 10 parallel research passes (silver, manipulation, technical
analysis, storage/custody, war-on-cash/CBDC, ESG, portfolio diversification,
supply/demand, the interviews, India/Eastern demand).

**New concept pages created:**

- `concepts/silver.md` — 8 sources (2010-2026). Silver as high-beta-to-gold; the
  GSR as monetary barometer; solar/AI demand; the structural-deficit thesis.
- `concepts/manipulation_intervention.md` — 7 sources (2009-2016). The
  manipulation-vs-intervention distinction; paper-vs-physical divergence; the 2016
  Deutsche Bank settlements.
- `concepts/technical_analysis.md` — 11 sources (2009-2026). The 1970s comparison,
  "Quo vadis, aurum?" price targets ($4,800-by-2030 reached early), the Active
  Aurum Signal.
- `concepts/gold_storage_custody.md` — 5 sources (2016, 2020-2022). The
  jurisdiction fact-checking series; allocated vs unallocated; confiscation
  history.
- `concepts/war_on_cash_cbdc.md` — 6 sources (2016-2022). Cash as the exit from
  fiat; the "Σ 0 ∞ € ¥" money metamorphosis; commercial banks create ~97% of money.
- `concepts/esg_responsible_mining.md` — 10 sources (2019-2026). ESG as capital-
  allocation gatekeeper; the "gold as ESG-positive / portfolio decarbonizer"
  thesis.
- `concepts/portfolio_diversification.md` — 9 sources (2008-2026). Low correlation,
  drawdown protection, anti-fragility, optimal allocation 2%→25%; the 2026
  "renaissance."
- `concepts/supply_demand.md` — 10 sources (2008-2026). Peak gold; the stock-to-
  flow inversion; the "great fallacy of high gold demand"; CB/ETF dominance.
- `concepts/voices_interviews.md` — 7 sources (2019-2026). FOFOA, Macleod, Gromen,
  Pozsar, Napier, Tindale — and the flagship ideas (Bretton Woods III, Freegold,
  the exorbitant burden) that entered via them.
- `concepts/india_eastern_demand.md` — 8 sources (2012-2026). India's ~35,000 t
  household hoard; the "golden love trade"; Eastern hubs vs LBMA.

**Index restructured** into four groups (foundations → macro drivers → market &
investing → voices) with source counts. Candidate list trimmed to genuinely
uncovered themes (petrodollar/oil-gold nexus; tokenization; hyperinflation
history; the proprietary models).

### ⚠ Source-corpus data-integrity issues found

Two 2019 source files are **mis-extracted** (their filenames/README labels do not
match their content). The genuine content for these chapters appears to be missing
from `markdown/2019/`:

1. `markdown/2019/07_gold_storage_fact_checking_liechtenstein_switzerland_and_singapore.md`
   — actual content is **"History Does (not) Repeat Itself – Plaza Accord 2.0?"**
   (not the Liechtenstein/Switzerland/Singapore storage chapter).
2. `markdown/2019/05_highlights_20_years_later_a_freegold_project_interview_with_fofoa.md`
   — actual content is **"The Enduring Relevance of Exter's Pyramid"** (interview
   with Barry Downs, not FOFOA). The genuine FOFOA interview is cited from the
   2021 file instead.

Both issues are flagged inline on the affected concept pages
([gold_storage_custody](concepts/gold_storage_custody.md) and
[voices_interviews](concepts/voices_interviews.md)) and should be fixed at the
source (re-extract from the 2019 PDF) rather than in the wiki. The "Plaza Accord
2.0?" and "Exter's Pyramid" content is itself valid and citable if separate pages
are ever built for those topics.

Next: run the final lint pass over all 18 pages.

---

## [2026-07-24] ingest | Source-corpus fix + third wave — 4 more concept pages

### Source-corpus data-integrity fix (2019)

Fixed the two mis-extracted 2019 chapters identified in the previous lint. Root
cause: the printed-TOC parser's fuzzy heading-match landed two real-but-unlisted
chapters into neighbouring files' page ranges.

- Re-extracted `2019/05_..._fofoa.md` with the genuine FOFOA interview
  (pdf pages 121-129).
- Re-extracted `2019/07_..._singapore.md` with the genuine Gold Storage chapter
  (pdf pages 165-175).
- Saved the two displaced chapters as new files: `2019/06a_exters_pyramid.md`
  (pages 130-142) and `2019/06b_..._plaza_accord_2.md` (pages 176-192).
- Regenerated the 2019 README (now 22 entries, was 20) and fixed the numbering.
- Fix script: `scripts/fix_2019_chapters.py` (with boundary sanity-checks before
  any writes). All four files verified for correct content + no cross-contamination.

Updated [gold_storage_custody](concepts/gold_storage_custody.md) and
[voices_interviews](concepts/voices_interviews.md) to cite the now-correct 2019
sources; the data-integrity warnings on those pages are marked **resolved**.

### Third wave — 4 new concept pages

Read a further ~30 chapters via 4 parallel research passes (hyperinflation, gold
valuation, the Status Quo framework, tokenization). New pages:

- `concepts/hyperinflation.md` — 4 sources (2010, 2019, 2022, 2023). The Cagan/
  Hanke threshold; Weimar/Zimbabwe/Venezuela; the Misesian crack-up boom; treated
  as a tail risk, not a forecast.
- `concepts/gold_valuation.md` — 8 sources (2012-2016). The no-cash-flow problem;
  ratio analysis; the Shadow Gold Price (monetary-base backing); the $2,300
  target's history; the 1934 revaluation precedent.
- `concepts/status_quo_framework.md` — 12 sources (2019-2026). The recurring
  annual multi-pillar diagnostic; the 2024 "new playbook" reframing; the
  evidentiary record for the standing bullish call.
- `concepts/tokenization_digital_gold.md` — 4 sources (2019, 2020, 2026 ×2).
  From 2019 skepticism to the 2026 "sixth vector of remonetization"; the
  counterparty-risk tension.

**Wiki now: 22 concept pages.** Index restructured to include the four new pages
across the foundations / macro-drivers / market-&-investing groups. Candidate list
trimmed (petrodollar nexus; proprietary models; image problem; Plaza Accord &
Exter's Pyramid remain).

Next: final lint over all 22 pages.

---

## [2026-07-24] ingest | Fourth wave — 4 more concept pages (26 total)

Read a further ~20 chapters via 4 parallel research passes (petrodollar/oil-gold,
image/psychology, Jastram+Austrian School, Exter/Plaza/Mackinder). New pages:

- `concepts/petrodollar_oil_gold.md` — 4 sources (2008-2012). The gold/oil ratio
  (7x-42x); petrodollar recycling; India-paying-Iran-in-gold; the 2012 "silent
  farewell."
- `concepts/image_psychology.md` — 4 sources (2012, 2013, 2024, 2026). Aurophobia,
  normalcy bias, cognitive dissonance, career risk, the "barbarous relic"
  inheritance, and the Overton-window defamation thesis.
- `concepts/golden_constant_austrian_school.md` — 5 sources (2009, 2010, 2013,
  2014, 2024). Jastram's five-century purchasing-power proof + "inflationary
  deflation"; the Austrian framework (money creation, Cantillon, deflation-as-cure).
- `concepts/exter_pyramid_heartland.md` — 5 sources (2011, 2012, 2019 ×2, 2026).
  The deflationary counter-narrative: Exter's inverted pyramid, the Exter-vs-Mises
  tension, Plaza Accord 2.0, Mackinder's Heartland applied to the monetary order.

**Wiki now: 26 concept pages.** Index updated; candidate list trimmed to three
genuinely uncovered themes (proprietary models; demographics/generational handoff;
empire & reserve-currency history).

The corpus's two major intellectual tensions are now both documented: the
inflation-vs-deflation endgame (Mises/monetarists vs Exter/deflationists) and the
gold-as-inflation-hedge vs gold-as-transition-hedge debate (FOFOA vs the rest).
See [monetary_policy_inflation](concepts/monetary_policy_inflation.md),
[hyperinflation](concepts/hyperinflation.md), and
[exter_pyramid_heartland](concepts/exter_pyramid_heartland.md).

Next: final lint + commit/push.

---

## [2026-07-24] ingest | Fifth wave — 3 more concept pages (29 total)

Read a further ~11 chapters via 3 parallel research passes (empire/monetary-order,
demographics/generations, crisis-triggers/swans). New pages:

- `concepts/empire_monetary_order.md` — 4 sources (2015, 2017, 2019, 2022). The
  long-arc narrative; the Bismarck-Ruhland meta-thesis; the Rome analogy (denarius
  debasement to 0.02% silver); the "acceleration" thesis; the zero-interest-rate
  trap.
- `concepts/demographics_generations.md` — 3 sources (2021 ×2, 2023). Demographics
  turning inflationary; Strauss-Howe Fourth Turning + Turchin elite-overproduction;
  the Millennial handoff; the capex/commodity supercycle.
- `concepts/crisis_triggers_swans.md` — 3 sources (2016, 2017, 2018). The white/
  gray/black-swan taxonomy; QT/China/Volmageddon triggers; the Austrian credit-
  cycle argument; a candid retrospective on prediction accuracy (right on
  fragility & monetary response, early on timing, wrong on mechanism — COVID was a
  genuine black swan that validated the taxonomy while bypassing every specific
  trigger).

**Wiki now: 29 concept pages.** Candidate list trimmed to two genuinely uncovered
themes (proprietary models; demand components in detail).

The corpus's major intellectual tensions are now all documented: inflation-vs-
deflation endgame (Mises vs Exter); gold-as-inflation-hedge vs transition-hedge
(FOFOA vs the rest); and the timing-vs-fragility tension in the crisis-triggers
work (structural-risk alarm bells vs reliable timing devices).

Next: final lint + commit/push.
