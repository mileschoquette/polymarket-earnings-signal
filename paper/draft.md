# Do Prediction Markets Know Earnings Before Wall Street Does? Evidence from Polymarket's Corporate Earnings Contracts

## Abstract

Prediction markets that let traders bet directly on whether a company will beat its quarterly earnings estimate offer a novel real-time forecast of corporate performance, distinct from analyst consensus or option-implied volatility. This paper tests whether Polymarket's "Will [company] beat quarterly earnings?" contracts contain information about earnings surprises beyond what a firm's own historical beat rate already predicts, and whether that information is economically exploitable. Using 1,231 resolved contracts spanning June 2025 through August 2026 across roughly 415 companies, we document three findings. First, Polymarket's implied beat probability is well-calibrated and achieves a materially lower Brier score than a naive firm-history baseline (0.149 versus 0.185, a gap whose 90 percent bootstrap confidence interval, [0.027, 0.042], excludes zero). Second, a logistic encompassing regression shows the market's implied probability predicts the actual outcome with a large, highly significant coefficient (5.78, p < 10⁻³⁵) that survives three different clustering-robust inference procedures, decisively beating the firm-history-only model in a likelihood ratio test; the probability's short-run momentum in the days before the print adds no further predictive power, and neither does it forecast the stock's own pre-announcement price reaction. Third, a volatility-targeted trading strategy built on the divergence between the market's price and firm history outperforms both a buy-and-hold benchmark and a firm-history-only trading rule in-sample at both a one-day and a five-day exit horizon, but a permutation test, a block-bootstrap confidence interval on the Sharpe ratio, and a Jobson-Korkie test against the buy-and-hold benchmark all agree this edge does not clear a conventional significance threshold once same-day earnings clustering is properly accounted for. The market's price is genuinely informative; whether that information translates into a statistically confirmed trading edge remains an open question given the sample's effective size of roughly 181 independent trading dates. We discuss implications for market efficiency, the design of consensus-adjacent information sources, and directions for extending the sample as Polymarket's earnings product matures.

## Introduction

On August 4, 2026, Polymarket priced Palantir Technologies at roughly 93 percent to beat its second-quarter earnings estimate. Two days later the company reported results that beat consensus and its shares rose sharply. That anecdote is the kind of story that motivates a broader question: do event-contract markets like Polymarket, which let anyone bet directly on a well-defined corporate outcome, actually know something before the rest of the market does, or is a single striking prediction simply survivorship bias dressed up as insight?

This paper answers that question with data rather than anecdote. Polymarket runs "Will [company] beat quarterly earnings?" as a systematic, recurring product, not a one-off novelty: 1,231 contracts resolved between June 2025 and August 2026 across roughly 415 distinct companies, each with a posted consensus EPS estimate and a continuously updated implied probability visible from contract creation through resolution. That scale and cadence make it possible to ask, with real statistical power, whether the market's price contains information beyond what any observer could already infer from a firm's own history of beating or missing its estimates, and whether a trader could have captured that information as a systematic strategy rather than a single lucky call.

The central empirical claim of this paper is that the market's price does carry real information. Polymarket's implied probability is close to well-calibrated across the range where most trading activity occurs, and it substantially outperforms a firm-specific historical base rate as a forecast of the actual outcome, both in a direct scoring-rule comparison and in a regression that nests the two forecasts against each other. This holds up under three different approaches to clustering standard errors, which matters here because many companies report earnings on the same handful of dates each quarter and are exposed to the same market-wide shocks on those days.

The secondary and more cautious claim concerns tradability. A strategy that goes long or short a company's stock ahead of its earnings print, sized by the divergence between the market's implied probability and the firm's own historical beat rate, outperforms both a naive buy-and-hold approach and a strategy built on firm history alone, at both exit horizons we test. But the sample's effective size for inference purposes is much smaller than its raw event count suggests. Because earnings reports cluster heavily on a handful of dates each quarter, the 1,231 events collapse to roughly 181 independent trading dates once that clustering is respected, and a permutation test, a block bootstrap, and a Jobson-Korkie test against the buy-and-hold benchmark all show the strategy's apparent edge is suggestive rather than statistically confirmed at conventional thresholds. We report this plainly rather than overstating a result that a more careful inference procedure does not fully support.

The paper proceeds as follows. Section 2 surveys the relevant literature on prediction-market efficiency and the closest existing empirical precedent, a 2026 Federal Reserve working paper evaluating Polymarket's sibling platform Kalshi against Bloomberg consensus for macroeconomic releases. Section 3 describes the data and methodology in five parts: the data itself (3.1), descriptive characteristics of the sample (3.2), a calibration and encompassing-regression test of informational content (3.3), a test of whether the stock's own pre-announcement price reaction anticipates the market's signal (3.4), and a volatility-targeted backtest with formal significance testing (3.5). Section 4 presents results and discusses their implications. Section 5 concludes and outlines directions for extending this analysis as Polymarket's earnings-contract coverage grows.

## Literature Survey

The idea that markets aggregate dispersed information into prices more efficiently than any single forecaster is foundational to the prediction-market literature. Early experimental work by Plott and Sunder (1988) showed that double-auction markets can aggregate private information held by individual traders into a price that reflects the pooled information set, even when no single trader holds enough information to make the correct call alone. Field evidence followed: the Iowa Electronic Markets, running since 1988, produced presidential-election vote-share forecasts that were closer to the eventual outcome than contemporaneous opinion polls in roughly 74 percent of 964 direct comparisons across the 1988-2004 election cycles (Berg, Nelson, and Rietz, 2008).

The most directly relevant precedent is a 2026 Federal Reserve Finance and Economics Discussion Series working paper by Diercks, Katz, and Wright, "Kalshi and the Rise of Macro Markets" (SSRN 6333085). The authors evaluate Kalshi's macroeconomic event contracts, covering Federal Reserve rate decisions, CPI releases, and jobs reports, against Bloomberg's survey-based consensus forecasts. They find that for headline CPI specifically, Kalshi's implied expectations deliver a statistically significant improvement in forecast accuracy over Bloomberg consensus; for core CPI and the unemployment rate, Kalshi's accuracy is statistically indistinguishable from Bloomberg's rather than superior. Their framing, that a CFTC-regulated event-contract exchange can be benchmarked directly against an established professional forecasting product using standard forecast-encompassing methodology, is the template this paper adapts to the earnings-forecasting setting, with two departures. First, the benchmark here is not a survey of professional forecasters but a firm's own historical tendency to beat or miss its estimates, since no free, systematic, point-in-time analyst-consensus panel for corporate earnings across hundreds of tickers was available for this study; a firm-specific historical base rate is a defensible, if more modest, substitute, and one a sophisticated trader could plausibly already know without paying for any data. Second, this paper extends the encompassing framework to ask not only whether the market's price level adds information, but whether the price's trajectory in the days before the print does as well, a question with more direct bearing on whether the market's edge could plausibly be captured through a trading strategy rather than only observed after the fact.

This paper's contribution relative to both anchors is to move the encompassing-market question from macroeconomic releases, which are single, simultaneous, economy-wide events, to firm-level corporate earnings, which recur hundreds of times a quarter and let the same test be run with cross-sectional, not just time-series, statistical power. Where Diercks, Katz, and Wright ask whether one market beats one consensus forecast release after release, this paper asks whether a market's price beats a firm-specific baseline across hundreds of distinct companies at once, and whether any resulting edge survives the panel's own clustering structure once it is used to trade.

The trading-strategy portion of this paper also connects to the older literature on post-earnings-announcement drift, the finding that stock prices do not fully and immediately incorporate the information in an earnings surprise, so that returns continue to drift in the direction of the surprise for weeks afterward (Bernard and Thomas, 1989, 1990). That drift is a standing anomaly this paper's trading strategy implicitly tries to front-run using the market's own probability rather than the earnings surprise itself, and Snowberg, Wolfers, and Zitzewitz (2012) survey the broader empirical record on when and why prediction markets add value as economic forecasting tools, a useful frame for interpreting why this paper's informational result is robust while its trading result is not: the literature they survey consistently finds prediction-market prices are informative in aggregate well before it finds that trading on that information alone is profitable net of the sampling uncertainty a short historical record leaves behind.

## Data and Methodology

### 3.1 Data

The core dataset is drawn from Polymarket's public Gamma and CLOB APIs, both unauthenticated and free to query. Polymarket tags every "Will [company] beat quarterly earnings?" contract under a single category (tag ID 1013, labeled "Earnings"). We enumerate all such contracts using cursor-based pagination and retain the 1,231 that resolved between June 2025 and August 2026, spanning roughly 415 distinct tickers. An earlier version of this analysis mistakenly dated the sample to January 2024, an error traced to one unrelated, mistagged contract (a market on the revenue from a viral social media post that happened to share the "Earnings" tag); excluding that single contract, the earliest genuine earnings-beat contract in the data resolves in June 2025, consistent with Polymarket having scaled this product only recently.

Each contract's title and description follow one of a small number of auto-generated templates that state the company, the scheduled earnings date, the consensus non-GAAP or GAAP EPS estimate, and the resolution criterion. We extract the ticker, accounting basis, scheduled date, and consensus estimate from this description text using a small set of regular expressions validated against the full sample; 1,274 of 1,275 raw contracts parse successfully, and the single failure is the mistagged contract discussed above. For each contract we also pull the full implied-probability price history for the "Yes" token from Polymarket's CLOB API, and the underlying stock's daily price history and sector, industry, and market-capitalization metadata from Yahoo Finance. Nine of 424 unique tickers could not be resolved in Yahoo Finance at all, plausibly reflecting delistings, acquisitions, or renamings in the roughly 18 months since our knowledge of these companies was last current; these affect 16 of the 1,231 events and are treated as missing rather than imputed. A tenth ticker, BBBY, resolved a full price history but carries no sector or industry classification in Yahoo Finance, likely a residual effect of its 2023 bankruptcy and delisting; its 4 events are included everywhere a sector label is not required but excluded from the sector breakdown in Table 1. Together these ten tickers account for the 20 events missing from Table 1's eleven named sectors.

Polymarket's own coverage of this product grew substantially over the sample period: from a single contract in the first partial quarter (2025 Q2) to 17 in the following quarter, a peak of 375 in the quarter ending December 2025 (2025 Q4), then 296, 319, and 223 in the three quarters since (below). A rough proxy for market liquidity and data density, the number of recorded price ticks per contract, rose in step, from roughly 50 in the earliest quarter to a range of 165 to 305 in every quarter since (below). Both series point the same way: this is a young product whose coverage and trading activity are still scaling, a fact that matters for how much weight the trading-strategy results in Section 3.5 can bear.

![Contracts resolved per quarter](figures/events_per_quarter.png)

Bar heights above are event counts, matching the figures in this paragraph; the number labeled on each bar is the count of distinct tickers reporting that quarter, a related but not identical figure, since a small number of tickers appear more than once within the same calendar quarter.

![Price-tick density per contract by quarter](figures/liquidity_proxy_trend.png)

### 3.2 Descriptive characteristics

The realized beat rate across the full sample is 74.7 percent (n = 1,231), consistent with the well-documented tendency of companies to guide estimates down ahead of earnings and then beat the resulting lowered bar. Table 1 breaks this rate out by sector. It varies meaningfully: Technology beats 84.4 percent of the time (n = 244) and Industrials 82.1 percent (n = 95), while Real Estate shows a realized rate of only 38.5 percent, on a sample of just 13 events and 5 distinct tickers, too small to treat as a reliable sector effect rather than noise. The firm-specific historical beat-rate baseline described in Section 3.3 averages 0.749 with a standard deviation of 0.086 across the sample, close to the realized overall rate by construction, since the baseline is built from each firm's own prior outcomes.

**Table 1. Realized beat rate by sector**

| Sector | n | Beat rate |
|---|---|---|
| Technology | 244 | 0.844 |
| Industrials | 95 | 0.821 |
| Basic Materials | 15 | 0.800 |
| Utilities | 10 | 0.800 |
| Consumer Defensive | 108 | 0.796 |
| Financial Services | 222 | 0.779 |
| Healthcare | 82 | 0.756 |
| Energy | 43 | 0.674 |
| Consumer Cyclical | 267 | 0.652 |
| Communication Services | 112 | 0.643 |
| Real Estate | 13 | 0.385 |
| Unknown / missing sector | 20 | 0.700 |
| **All sectors** | **1,231** | **0.747** |

The eleven named sectors sum to 1,211 events; the "Unknown / missing sector" row adds the 20 events described in Section 3.1 (16 from tickers Yahoo Finance could not resolve at all, plus 4 from BBBY, which resolved a price history but no sector classification), bringing the total to the full 1,231-event sample. We report beat rate and sample size rather than higher moments such as skewness and kurtosis, since the underlying outcome is a binary beat/miss indicator rather than a continuous return series, and a rate and a count are the informative summary of a binary variable's distribution.

![Realized beat rate by sector](figures/beat_rate_by_sector.png)

### 3.3 Informational content: calibration and encompassing regression

The paper's central empirical question is whether Polymarket's implied probability carries information about the actual earnings outcome beyond a firm's own history. We construct a firm-specific historical beat-rate baseline for each event using only that firm's outcomes in the quarters strictly prior to the event being scored, shrunk toward an expanding global base rate when a firm has few prior observations (an empirical-Bayes-style backoff), so that this baseline never has access to information a real observer would not have had at the time.

We first compare this baseline against Polymarket's pre-earnings implied probability directly, using the Brier score as a proper scoring rule: Polymarket's implied probability achieves a Brier score of 0.1494 versus 0.1847 for the firm-history baseline alone (n = 1,216), a gap of 0.0353. Resampling the sample by calendar date with replacement 1,000 times to respect the same clustering discussed below, the gap's 90 percent bootstrap confidence interval is [0.0273, 0.0424], comfortably excluding zero: the market's calibration advantage over firm history is not an artifact of one lucky draw of companies or dates. A Murphy (1973) decomposition of Polymarket's Brier score into reliability, resolution, and uncertainty components shows a small reliability term (0.0011) relative to resolution (0.0410) and uncertainty (0.1895), indicating the market's probabilities are close to well-calibrated rather than systematically over- or under-confident (the reliability diagram below plots mean predicted against mean realized probability within ten equal-width prediction bins).

![Reliability diagram: mean predicted vs. mean realized outcome by probability bin](figures/reliability_diagram.png)

We then estimate a logistic encompassing regression nesting the firm-history baseline inside a fuller model that also includes Polymarket's pre-earnings implied probability and its short-run momentum in the days before the print:

**Equation 1.**

logit(Pr(beat<sub>i</sub> = 1)) = β₀ + β₁ · historical_beat_rate<sub>i</sub> + β₂ · implied_prob_pre_earnings<sub>i</sub> + β₃ · implied_prob_momentum<sub>i</sub> + ε<sub>i</sub>

where `historical_beat_rate` is the same prior-only baseline from Section 3.2, `implied_prob_pre_earnings` is Polymarket's implied probability shortly before the scheduled print, and `implied_prob_momentum` is the change in that implied probability over the days immediately preceding the print, capturing whether the market's price is still moving toward or away from a beat in the run-up to the announcement. Standard errors are clustered by announcement date to account for the fact that many companies report on the same handful of dates each quarter and share exposure to the same market-wide news on those days.

The implied-probability level coefficient (β₂) is large and highly significant: 5.78, standard error 0.46, z = 12.5, p < 10⁻³⁵ under date clustering, and this result is robust to clustering by ticker instead (standard error 0.54) and to two-way clustering by both date and ticker jointly using the Cameron-Gelbach-Miller correction (standard error 0.50). The momentum coefficient (β₃), by contrast, is small, negative, and statistically indistinguishable from zero (-0.83, p ≈ 0.25 under every clustering specification): once the market's price level is in the model, the direction it has recently been moving adds no further information about the outcome. A likelihood ratio test comparing the full model to the firm-history-only model rejects the restriction that β₂ = β₃ = 0 overwhelmingly (χ² = 202.0, 2 degrees of freedom, p ≈ 1.4 × 10⁻⁴⁴). Comparing the two forecasts as single predictors directly, Polymarket's implied probability alone achieves a substantially higher log-likelihood (-513.2) and pseudo-R² (0.183) than the firm-history baseline alone (-612.1 and 0.026, respectively, n = 1,119). Firm history is a weak forecaster of earnings surprises on its own; the market's price level is not, though its short-run trajectory adds nothing beyond the level.

### 3.4 Pre-announcement price reaction

The encompassing regression in Section 3.3 asks whether the market's implied probability, including its recent trajectory, predicts the eventual outcome. A related but distinct question is whether the stock's own price already starts moving in the direction of that trajectory before the print, independent of whether the trajectory is genuinely informative about the outcome. If the equity market is efficiently absorbing the same signal Polymarket traders are acting on, the stock's pre-announcement return should track the implied-probability momentum even though, per Section 3.3, that momentum does not itself forecast the actual beat or miss.

We construct a market-adjusted pre-announcement cumulative abnormal return, `car_pre`, as each stock's raw return from five to one trading days before the scheduled earnings date, minus the S&P 500's (SPY) return over the identical window. This is available for 1,215 of 1,231 events (98.7 percent). We regress `car_pre` on `implied_prob_momentum`, with standard errors clustered by announcement date for the same reason as Section 3.3:

**Equation 2.**

car_pre<sub>i</sub> = α + γ · implied_prob_momentum<sub>i</sub> + ε<sub>i</sub>

The estimated coefficient is small and not statistically significant: γ = 0.0104, standard error 0.0107, p = 0.330, n = 1,104 (below). We read this as a null result rather than a disappointing one. It says the stock's own pre-announcement price action does not detectably track Polymarket's implied-probability momentum, which is consistent with, not contradictory to, the encompassing regression's finding that momentum itself carries no incremental information about the outcome: there is nothing informative in the momentum signal for either market to have already priced in.

![Pre-announcement CAR vs. implied-probability momentum](figures/car_vs_momentum.png)

### 3.5 Trading strategy and significance testing

Given that the market's price level is informative, we construct a trading strategy around the divergence between Polymarket's implied probability and the firm-history baseline:

**Equation 3.**

divergence<sub>i</sub> = implied_prob_pre_earnings<sub>i</sub> − historical_beat_rate<sub>i</sub>

The strategy takes a position only when this divergence exceeds, in absolute value, half a standard deviation of an expanding, strictly-prior-only measure of divergence dispersion (so the threshold itself is never calibrated using future information), and requires at least 20 prior observations before trading at all. Position size is volatility-targeted:

**Equation 4.**

position_size<sub>i</sub> = clip(target_daily_vol / vol<sub>i</sub>, min_leverage, max_leverage)

where `vol_i` is the stock's trailing 20-trading-day realized volatility as of the day before entry, `target_daily_vol` is a fixed daily risk budget, and the clip to `[min_leverage, max_leverage]` keeps any single low-volatility or high-volatility stock from dominating the portfolio's risk. The strategy enters at the closing price the day before the scheduled earnings date, exits either one or five trading days after the print, and pays a transaction cost of 5 basis points per side (10 basis points round-trip on `position_size`), the default in this project's backtest engine (`src/strategy/backtest.py`) and a level broadly consistent with typical bid-ask spreads on liquid large-cap equities.

**Table 2. Performance by exit horizon (main divergence strategy)**

| Metric | t+1 (event-level) | t+1 (date-aggregated) | t+5 (event-level) | t+5 (date-aggregated) |
|---|---|---|---|---|
| Sharpe | 1.031 | 1.095 | 1.052 | 1.083 |
| Sortino | 0.976 | 1.520 | 0.995 | 1.401 |
| Max drawdown | -1.025 | -0.978 | -1.005 | -0.964 |
| Calmar | 1.375 | 1.441 | 1.609 | 1.677 |
| Hit rate | 0.529 | n/a | 0.483 | n/a |
| Executed trades | 384 | 181 dates | 352 | 181 dates |

At both horizons the strategy outperforms two natural benchmarks constructed through the identical backtesting machinery (date-aggregated Sharpe): a buy-and-hold strategy that is always long every stock ahead of its earnings print achieves 0.708 at t+1 and 0.508 at t+5, and a strategy that trades on firm history alone, with no market information, achieves 0.426 at t+1 and 0.278 at t+5. A perfect-foresight strategy that knows the actual outcome in advance, included only as a sanity ceiling rather than a real competitor, achieves 3.899 at t+1 and 3.397 at t+5, confirming the backtest engine behaves sensibly at the extremes.

![Backtest equity curve, both exit horizons](figures/backtest_equity_curve.png)

![Strategy vs. buy-and-hold S&P 500, t+1 horizon](figures/strategy_vs_market.png)

That in-sample outperformance does not survive formal significance testing as cleanly as the encompassing regression's informational claim does, at either horizon. A permutation test that randomly reassigns the sign of each executed trade's direction, holding trade selection, timing, and sizing fixed, and recomputes the date-aggregated Sharpe ratio over 1,000 draws, finds that 10.10 percent of random sign assignments matched or exceeded the observed Sharpe ratio at t+1 (9.50 percent at t+5), missing the conventional 5 percent threshold at both horizons. A block bootstrap that resamples entire calendar dates with replacement produces a 90 percent confidence interval for the Sharpe ratio of [-0.506, 2.498] at t+1 and [-0.488, 2.523] at t+5, both wide enough to include economically large positive and negative values. A Jobson-Korkie test of the Sharpe-ratio difference between the main strategy and buy-and-hold, using the Memmel (2003) small-sample correction, likewise fails to reject equality: z = 0.335, p = 0.737 at t+1 and z = 0.492, p = 0.623 at t+5, both far from conventional significance. Three independent inference procedures agree at both exit horizons. The reason is structural rather than a flaw in the strategy: once same-day earnings announcements are correctly treated as a single clustered observation rather than as independent events, the effective sample size for inference is only about 181 distinct trading dates, not 1,231 events. A promising point estimate built on that many effective observations is not yet distinguishable from noise at conventional confidence levels.

The strategy's edge is also sensitive to trading costs. Raising the assumed round-trip cost from the baseline 5 basis points per side to 10 and then 20 lowers the t+1 date-aggregated Sharpe from 1.095 to 0.854 and then 0.375: the point estimate survives even a quadrupling of the cost assumption, but shrinks by two-thirds, underscoring that this is a strategy whose in-sample edge is modest in absolute terms even before the statistical significance question is considered.

## Results and Discussion

Three results anchor this paper. Polymarket's earnings-beat contracts are well-calibrated and add genuine forecasting power beyond a firm's own history, a finding that mirrors, in a cross-sectional corporate-earnings setting, what Diercks, Katz, and Wright document for Kalshi's macroeconomic contracts against Bloomberg consensus. Neither the market's short-run momentum nor the stock's own pre-announcement price action adds anything to that informational picture, a coherent pair of null results rather than two unrelated ones. A trading strategy built on the market's price level beats naive alternatives in-sample at both exit horizons tested. But the strategy's statistical significance does not clear conventional thresholds once the earnings calendar's natural clustering is respected in the inference procedure, a distinction that matters for interpreting what this paper has and has not shown.

It is worth separating statistical significance from economic significance explicitly, since the two point in different directions here. Statistically, the informational result is not in question: three different clustering-robust standard error procedures, a nonparametric scoring-rule comparison with its own bootstrap confidence interval, and a likelihood ratio test all agree the market's price is meaningfully informative, with p-values many orders of magnitude past any reasonable multiple-comparisons correction. The trading result is the reverse: it is economically suggestive, a Sharpe ratio near 1.1 that beats buy-and-hold by roughly 0.4 at both horizons and survives a quadrupling of assumed trading costs, but three independent significance tests (permutation, block bootstrap, Jobson-Korkie) each fail to distinguish it from noise at conventional confidence. What remains genuinely uncertain is whether 181 independent earnings seasons is enough data to distinguish a real, exploitable trading edge from a strategy that happened to perform well over one particular 14-month stretch. That is a sample-size problem, not a design flaw, and it is the natural next question as Polymarket's earnings-contract coverage continues to grow: the same tests, rerun in two or three years with several times as many independent trading dates, would settle a question this paper can only leave open.

A secondary implication concerns the design of firm-specific baselines for evaluating any forecasting product against corporate outcomes. The historical beat-rate baseline used here performs poorly as a standalone predictor (pseudo-R² of 0.026), a reminder that "the company usually beats" is a much weaker forecast than it might intuitively seem, precisely because it is already common knowledge and priced into low analyst estimates before the market's information is layered on top.

## Conclusion

This paper set out to test a specific, falsifiable version of a viral trading anecdote: does a prediction market's implied probability that a company will beat earnings actually contain tradable information, or is a single striking call just noise in retrospect. Using 1,231 resolved Polymarket earnings-beat contracts, we find the market's price is genuinely informative, well-calibrated, and a substantially better predictor of the actual outcome than a firm's own trading history, a result that holds up under multiple approaches to statistical inference. A trading strategy built on this information outperforms sensible naive benchmarks in-sample at both a one-day and a five-day exit horizon, but that edge is not yet statistically distinguishable from noise, by three separate tests, once the earnings calendar's clustering structure is properly accounted for, given an effective sample of roughly 181 independent trading dates.

Several limitations bound how far these results should be read. The effective sample size for the trading-strategy inference is roughly 181 independent calendar dates, not the 1,231 raw events, and that is the binding constraint on statistical power throughout Section 3.5. The Real Estate sector's 38.5 percent beat rate rests on just 13 events across 5 tickers and should not be read as a reliable sector effect. All results here are in-sample; the strategy has not been tested on a genuine out-of-sample holdout period, since the underlying market has not yet existed long enough to support one. The pre-announcement price-reaction regression in Section 3.4 is a null result on its own terms (p = 0.330), which is informative but means this paper cannot claim the equity market itself is reacting to the same signal Polymarket traders see. And the trading edge, while it survives a quadrupling of the assumed transaction cost from 5 to 20 basis points per side, shrinks by roughly two-thirds over that range, so its robustness to real-world execution costs is only partial.

Future extensions of this work should incorporate a genuine point-in-time analyst-consensus panel as an additional benchmark alongside firm history, extend the backtest as more quarters of data become available to narrow the bootstrap confidence interval and build a true out-of-sample holdout, and examine whether the same result holds for Kalshi's own nascent single-company earnings products (its "Public Companies Hub," launched only in the days before this study began) as that platform's coverage matures, which would allow a direct cross-platform test of whether this informational edge is a general feature of regulated event-contract markets or specific to Polymarket's particular trader base and market design.

## Literature

Bernard, V. L., & Thomas, J. K. (1989). Post-Earnings-Announcement Drift: Delayed Price Response or Risk Premium? *Journal of Accounting Research*, 27, 1-36.

Bernard, V. L., & Thomas, J. K. (1990). Evidence That Stock Prices Do Not Fully Reflect the Implications of Current Earnings for Future Earnings. *Journal of Accounting and Economics*, 13(4), 305-340.

Berg, J. E., Nelson, F. D., & Rietz, T. A. (2008). Prediction Market Accuracy in the Long Run. *International Journal of Forecasting*, 24(2), 285-300.

Diercks, A. M., Katz, J. D., & Wright, J. H. (2026). *Kalshi and the Rise of Macro Markets*. Federal Reserve Finance and Economics Discussion Series. SSRN 6333085.

Plott, C. R., & Sunder, S. (1988). Rational Expectations and the Aggregation of Diverse Information in Laboratory Security Markets. *Econometrica*, 56(5), 1085-1118.

Snowberg, E., Wolfers, J., & Zitzewitz, E. (2012). *Prediction Markets for Economic Forecasting*. NBER Working Paper 18222.
