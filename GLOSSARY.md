# Domain Glossary: Quantitative Pattern Search Engine (`dtwmagic`)

This glossary establishes the canonical vocabulary for all requirements, tests, code, and agent skills.

## Core Concepts

- **Historical Analogy (Fractal):** A past sequence of candlestick bars that exhibits high geometrical similarity to a current query pattern.
- **Query Pattern:** The recent sequence of $N$ candlestick bars (e.g., last 10 daily sessions) being searched against historical data.
- **Z-Score Normalization:** Transforming relative cumulative returns into standard normal space ($z = (r - \mu) / \sigma$) to compare price action across different eras and index levels independently of raw price.
- **Euclidean Distance:** The $L_2$ norm between two normalized price vectors. Serves as the primary fast sliding-window filter ($O(N)$ dot product).
- **Dynamic Time Warping (DTW):** An algorithm measuring distance between time-series with local phase shifts. Constrained via a **Sakoe-Chiba band** to prevent excessive temporal distortion.
- **Market Regime:** The macroscopic market environment characterized by two independent factors:
  - **Trend Regime:** Directional bias determined by Moving Average stack & slope (Bullish, Bearish, Neutral).
  - **Volatility Regime:** Volatility level determined by rolling ATR percentile rank (Low, Normal, High).
- **Maximum Adverse Excursion (MAE):** The deepest observed intraday or closing drawdown experienced by a stock between trade entry and a specified forward horizon ($T+H$). Used to assess historical volatility depth.
- **Maximum Favorable Excursion (MFE):** The peak observed intraday or closing gain experienced by a stock between trade entry and a specified forward horizon ($T+H$).
- **Sample Positive Return Frequency:** The empirical proportion of matched historical analogs that recorded positive returns at horizon $T+H$. (Descriptive historical frequency, NEVER called "win rate" or "probability").
- **Historical Outcome Cone:** Empirical quantile distribution ($10^{\text{th}}$, $25^{\text{th}}$, Median, $75^{\text{th}}$, $90^{\text{th}}$ percentiles) of forward trajectories observed in matched historical episodes.
- **Ghost Overlay:** A visual chart projection displaying the actual subsequent path taken by a matched historical episode, anchored to the current price.

## Regulatory Boundaries (SEBI Safe Harbor)

- **Search Engine:** A technical query-and-retrieval system (like reverse image search). Never an advisory system.
- **Descriptive Statistics:** Factual historical reporting of past observations. Never forward predictions, targets, or stop-loss recommendations.
