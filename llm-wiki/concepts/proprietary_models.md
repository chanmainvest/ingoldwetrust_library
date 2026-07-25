# Incrementum's proprietary models

The four house-built (or house-hosted) analytical models that recur across the
corpus: the **Inflation Signal** (a monetary seismograph), the **Synchronous Equity
and Gold Price Model / SEGPM** (the M2-tracking joint index), the **Active Aurum
Signal** (a mining-stock timing signal), and the **Midas Touch Gold Model** (the
Grummes multi-component technical table). This page consolidates material that was
previously distributed across several pages.

> "Essentially, all models are wrong, but some are useful." — George Box (the
> epigraph the authors use for both the Inflation Signal and the SEGPM)

See also: [technical_analysis](technical_analysis.md),
[monetary_policy_inflation](monetary_policy_inflation.md),
[gold_valuation](gold_valuation.md),
[portfolio_diversification](portfolio_diversification.md),
[gold_mining_stocks](gold_mining_stocks.md).

---

## 1. The Incrementum Inflation Signal

**Purpose.** A proprietary "monetary seismograph" that measures **how much monetary
inflation actually reaches the real economy** — forward-looking, in contrast to
"conventional inflation statistics [which] only ever show past inflation trends,
i.e. they look in the 'inflation rear-view mirror'" (2020). It is used in-house:
"In the fund we manage, our Inflation Signal gauges the inflation trend and we
position the fund accordingly" (2014).

**Components.** A composite of inflation-sensitive assets: **gold, silver, the BCOM
commodity index, and the HUI gold-mining-stock index** (2020). The conceptual
backbone is the **gold/silver ratio**, which Incrementum calls "the deflation/
reflation ratio" — silver is a hybrid (monetary + industrial, early-cycle) so it
leads inflation, whereas gold is almost purely monetary and also benefits from
deflation. A rising signal = inflationary pressure; a falling signal =
disinflation/deflation.

**Evolution 2014 → 2024:**
- **2014 (origin):** introduced as the "Incrementum Inflation Signal," gold/silver
  ratio central, used for fund positioning.
- **2020:** components made explicit (Gold, Silver, BCOM, HUI), indexed to 01/2007
  = 100, read across six historical phases.
- **2024 (major revision):** after the 2023 miss (see below), expanded inputs,
  reweighted toward broad commodities and "inflation precursors," simplified from
  six stages to three (mirroring the Active Aurum Signal), BCOM → BCOM TR.

**What it signaled at key moments:**
- Inflationary until Aug 2008, then deflationary shock (GFC) into Mar 2009.
- Reflation until 2011/12, then disinflation to end-2015 (the 2014-15 deflationary
  scare is visible in the rising gold/silver ratio).
- Covid deflation shock Q1 2020, then "slightly rising inflation since April 2020."
- **The 2023 miss:** "the signal failed to correctly capture the continuing
  disinflationary phase throughout 2023. This misjudgment prompted us to critically
  review and optimize our signal methodology" (2024).
- April 2024: "neutral inflation tendency"; "disinflation — in the US — is over, at
  least for the moment."

**Nuance.** The authors are unusually candid — they open the signal section with
George Box's "all models are wrong" and directly admit the 2023 failure, framing
the entire 2024 revision as a response rather than a defense. The proprietary
weights are withheld, so independent verification isn't possible from the reports
alone.

*Sources: [2014 — Monetary Tectonics](../markdown/2014/08_monetary_tectonics_the_interaction_between_inflation_and_deflation.md);
[2020 — Status Quo of Inflation Dynamics](../markdown/2020/07_status_quo_of_inflation_dynamics.md);
[2024 — Status Quo of Inflation](../markdown/2024/05_status_quo_of_inflation.md).*

---

## 2. The Synchronous Equity and Gold Price Model (SEGPM)

**Thesis (author: Dietmar Knoll).** For ~50 years there has been "a close and
predictable relationship between the money supply and the prices of equities and
gold," overlaid by investor confidence. The SEGPM defines a **joint index = S&P 500
+ 1.5 oz of gold** and shows this joint index tracks **US M2** far more tightly
than either asset alone (2022).

**Two-variable decomposition:**
- **Money supply (M2)** determines the *level* of the joint index (the long-run
  driver). "Each $1,000 bn increase in M2 leads to a $333 increase in the value of
  the joint index" (data since 1963).
- **Investor trust**, measured by the **S&P 500/gold ratio**, determines the
  *split* between the two assets (the short-run driver). Because M2 growth appears
  in both numerator and denominator of the ratio, it is "trimmed out," isolating
  pure investor confidence.

**Why 1.5 oz?** Borrowed from Gary Christenson's "F.E.D. Index" (Fiat-Enduring
Devaluation) — an empirical historical-average calibration representing "a roughly
50/50 split on a historical average basis." It is a fixed definitional feature,
not dynamically re-estimated.

**Within-index share swings:** gold's share peaked at **90.5% (Feb 1980)**;
equities peaked at **~78% (Aug 2000)**. The S&P/gold ratio's trust percentile
scale (1973-2021): 90th = 2.90; median = 1.20; 10th = 0.41; max = 5.41 (Aug 2000);
min = 0.16 (Jan 1980).

**The Synchronous Bull Market Indicator (2023 operationalization).** Compare the
monthly S&P/gold ratio to its **40-month moving average**:
- Ratio above the 40-month MA → equity bull market.
- Ratio below → gold bull market.
- **Trigger:** rebalance only when deviation exceeds **±5%** (to filter noise).

It identifies four secular bull markets: gold 1970-80 (+1,828%, 34.5%/yr), S&P
1980-2000 (+1,188%, 13.6%/yr), gold 2000-11 (+551%, 18.5%/yr), S&P 2011-21 (+287%,
14.5%/yr). Three false signals (1974-76, Oct 1987, Covid-2020) — the latter two
"rescued" by aggressive Fed easing. Confirmation lag typically 1-2 years.

**Backtest (07/1971 – 03/2023):** the SBMI trend-following strategy returned
**+62,798% (13.28%/yr)** vs. S&P +3,909% (7.41%), gold +4,411% (7.65%), 50/50
+4,105% (7.50%) — with only **9 reallocations in ~52 years**.

**Nuance.** Both chapters are framed with George Box's "all models are wrong." The
backtests show the model undershoots during "exaggeration phases" (gold booms of
the late 1970s and 2011; the S&P boom of 1998-2001). Turning points can only be
"determined with absolute certainty in retrospect." Money-supply forecasting is
acknowledged as hard, so the long-run price targets are scenario-conditioned, not
point forecasts.

*Sources: [2022 — The Synchronous Equity and Gold Price Model](../markdown/2022/16_the_synchronous_equity_and_gold_price_model.md);
[2023 — The Synchronous Bull Market Indicator](../markdown/2023/16_the_synchronous_bull_market_indicator.md).*

---

## 3. The Incrementum Active Aurum Signal

**Purpose.** A proprietary **timing signal for sizing gold-mining-stock exposure**,
launched 2024 (the "Mastering the New Gold Playbook" chapter). It underpins the
real managed *Incrementum Active Gold Strategy*. The premise: mining stocks are
"not a buy-and-hold investment" because both bull and bear markets are more extreme
than in conventional equities.

**Two sub-signals:**

**(a) Cycle signal** — five **anticyclical** (countercyclical) components, each
oscillating 0-100 and combined into an aggregate 0-100 value:
1. **Momentum** — RSI of gold mining stocks.
2. **Sentiment** — CFTC net gold positioning.
3. **Risk appetite** — Bollinger Bands on the mining-stocks/gold ratio (and
   juniors/seniors).
4. **Macro environment** — TIPS real yields vs. their 52-week moving average.
5. **Boom/bust indicator** — gold mining stocks vs. their moving average.

Thresholds: aggregate >85 = sell; <20 = buy.

**(b) Fundamental signal** — a **procyclical**, binary indicator (0 or 100) built
around a "gold mining stock margin trend channel" that incorporates commodity-
market developments.

**The three levels** (deterministic AND-combination of the two sub-signals):
- **Offensive** (both buy) → **100% mining stocks.**
- **Neutral** (diverge) → **50%.**
- **Defensive** (both sell) → **0%.**

**Backtest (BGMI 1971-2005, then GDX):** ~1.5 signal changes/year since 1971.

| Report | As-of | Passive | **Active** | Active CAGR |
|--------|-------|---------|-----------|-------------|
| 2024 | 04/2024 | 469% | **7,723%** | 8.61% |
| 2025 | 04/2025 | 716% | **11,107%** | 9.17% |
| 2026 | 04/2026 | 1,477% | **16,279%** | 9.76% |

Risk side (2026): active annualized volatility **26.05%** vs passive 36.93%; max
drawdown −62.56% vs −82.53%; Sharpe 0.36 vs 0.14; Sortino 0.46 vs 0.19.

**Live performance 2024-2026:** Live tracking began 1 Jan 2024 on **Offensive**
(since Dec 2023) — capturing the HUI's ~150% rally. **10 Oct 2025: Offensive →
Neutral** (cycle signal overheating; fundamental still positive). **20 Mar 2026:
Neutral → Defensive** (Iran war, deteriorating precious-metals environment; the
fundamental signal also turned). A clean first live cycle.

**Nuance — overfitting and transparency.** Component names and the 85/20 thresholds
are disclosed, but the component weightings, the margin-trend-channel construction,
and the precise parameters are proprietary. **No explicit overfitting caveat** is
made; the authors argue the opposite (low turnover, consistency of excess return).
The signal underpins a commercial product, which colors how aggressively the
favorable backtest is presented.

*Sources: [2024 — Mastering the New Gold Playbook](../markdown/2024/08_mastering_the_new_gold_playbook.md);
[2025 — Bringing It Home](../markdown/2025/11_bringing_it_home_central_bank_gold_repatriation.md);
[2026 — Gold and Silver Miners: From Problem Child to Model Student](../markdown/2026/25_gold_and_silver_miners_from_problem_child_to_model_student.md).*

---

## 4. The Midas Touch Gold Model™

**A recurring guest contribution** from **Florian Grummes** (Midas Touch
Consulting), present in every technical-analysis chapter since **2016**. A
holistic, multi-component table synthesizing buy/sell signals across many
independent angles into one compact read — "to analyze the market rationally from
as many independent perspectives as possible and to derive simple short- to
medium-term signals" (2016).

**Structure.** A single table aggregating many component rows (each flagged
bullish/bearish/neutral) across **monthly (long-term), weekly (medium-term), and
daily (short-term)** timeframes, with a net qualitative verdict ("buy signal / sell
signal / bearish mode / bullish mode / neutral").

**Component evolution:**
- **2016:** trend-following (monthly/weekly/daily); volatility; CoT + sentiment;
  ratios (Dow/gold, gold/silver, **gold/oil**, gold vs other commodities); GLD
  holdings; **gold in CNY and INR**; GDX; USD performance + futures positioning;
  real interest rates.
- **2022:** monthly gold-USD; **gold in INR and CNY**; GDX; **Dow/gold**;
  **gold/silver** (turned 11 April, early warning); **Bitcoin/gold** (new
  addition); negative real rates; **DXY**. Gold/oil and GLD lines de-emphasized.
- **2025:** monthly/weekly/daily in USD; **gold in four currencies (USD, INR, CNY,
  EUR)**; CoT (with a candid note that its relevance is declining as Asian physical
  flows dominate); **seasonality** (more prominent); sentiment; **Dow/gold**
  (long-term target 1:1); **gold/silver**; DXY; psychological price targets
  ($4,000, $5,000).

**Track record:**
- **2016 (origin):** model had been on **sell for most of 2015** (correct — gold
  bottomed Dec 2015 at $1,046), switched to **buy early 2016**; primary-trend
  monthly buy fired Feb 2016 — "the first time since November 2011." Target $1,500;
  gold continued higher.
- **2022:** switched to **bearish mode on 19 April 2022** after gold slid below
  $1,940 — correctly anticipated the 2022-H1/2023 consolidation.
- **2025:** flipped to **bearish mode on 30 April 2025** (near the $3,500 ATH)
  while the **monthly buy (active since 28 Feb 2023) stayed intact** — caught the
  ~$300 pullback while remaining structurally long.

**The monthly/primary calls have been the strong suit** (Feb 2016 buy, Feb 2023
buy); the daily/weekly tactical calls are more mixed but generally defensive near
short-term tops.

**Vs. the Active Aurum Signal.** Midas Touch is a **discretionary, holistic table**
read by a human analyst; Active Aurum is a **rule-based composite** with fixed
thresholds and a deterministic 100/50/0% mapping. Midas Touch primarily times the
**gold price**; Active Aurum times **mining-stock exposure**. Midas Touch is a
guest contribution; Active Aurum is Incrementum's own product.

*Sources: [2016 — Excursus: The Midas Touch Gold Model](../markdown/2016/47_excursus_the_midas_touch_gold_model.md);
[2019 — Technical Analysis](../markdown/2019/18_technical_analysis.md);
[2022 — Technical Analysis](../markdown/2022/24_technical_analysis.md);
[2025 — Bringing It Home](../markdown/2025/11_bringing_it_home_central_bank_gold_repatriation.md).*

---

## Synthesis: how the four models fit together

| Model | Object | Horizons | Method | Status |
|-------|--------|----------|--------|--------|
| **Inflation Signal** | the inflation regime | months-quarters | composite of gold/silver/BCOM/HUI | proprietary, used in-house; revised 2024 |
| **SEGPM / SBMI** | the gold-vs-equities regime | years (secular) | joint S&P+1.5oz index vs M2; S&P/gold ratio vs 40-mo MA | guest (Knoll); operationalized 2023 |
| **Active Aurum** | mining-stock exposure | weeks-months | 5 anticyclical + 1 procyclical component; 3 levels | proprietary, drives a live strategy |
| **Midas Touch** | the gold price | days-weeks-months | multi-component discretionary table | guest (Grummes), since 2016 |

The four cover different timeframes and objects, and Incrementum uses them
complementarily: the Inflation Signal sets the macro regime; SEGPM frames the
secular gold-vs-equities choice; Active Aurum tactically sizes mining stocks within
that; Midas Touch gives short-term gold-price calls. All four are presented with
unusual epistemic humility (the George Box epigraph recurs), and all four have
published misses as well as hits — the Inflation Signal's 2023 disinflation miss,
SEGPM's three false signals, Midas Touch's mixed tactical record.

## Sources (consolidated)

- [2014 — Monetary Tectonics: The Interaction between Inflation and Deflation](../markdown/2014/08_monetary_tectonics_the_interaction_between_inflation_and_deflation.md) *(Inflation Signal origin)*
- [2020 — Status Quo of Inflation Dynamics](../markdown/2020/07_status_quo_of_inflation_dynamics.md) *(Inflation Signal update)*
- [2024 — Status Quo of Inflation](../markdown/2024/05_status_quo_of_inflation.md) *(Inflation Signal 2024 revision)*
- [2022 — The Synchronous Equity and Gold Price Model](../markdown/2022/16_the_synchronous_equity_and_gold_price_model.md) *(SEGPM origin)*
- [2023 — The Synchronous Bull Market Indicator](../markdown/2023/16_the_synchronous_bull_market_indicator.md) *(SEGPM operationalization)*
- [2024 — Mastering the New Gold Playbook](../markdown/2024/08_mastering_the_new_gold_playbook.md) *(Active Aurum origin)*
- [2025 — Bringing It Home: Central Bank Gold Repatriation](../markdown/2025/11_bringing_it_home_central_bank_gold_repatriation.md) *(Active Aurum + Midas Touch 2025)*
- [2026 — Gold and Silver Miners: From Problem Child to Model Student](../markdown/2026/25_gold_and_silver_miners_from_problem_child_to_model_student.md) *(Active Aurum latest)*
- [2016 — Excursus: The Midas Touch Gold Model](../markdown/2016/47_excursus_the_midas_touch_gold_model.md) *(Midas Touch origin)*
- [2019 — Technical Analysis](../markdown/2019/18_technical_analysis.md) *(Midas Touch)*
- [2022 — Technical Analysis](../markdown/2022/24_technical_analysis.md) *(Midas Touch update)*
