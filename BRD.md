# Business Requirements Document (BRD)
## Project: NSE Historical Pattern Search Engine (`dtwmagic`)
**Category:** Financial Data Analytics & Quantitative Historical Search Engine  
**Author:** Pair Engineering Team  
**Architecture Philosophy:** Kailash Nadh (Radical Simplicity, Frugal Infrastructure, Zero Cloud Bloat)  
**Target Market:** Indian Retail & Prop Traders (NSE Equities & Indices)  
**Regulatory Position:** 100% Non-Advisory Technology Provider (Safe Harbor under SEBI Regulations)  
**Status:** Architecture & Requirements Specification (Final v1.1)  

---

## 1. Executive Summary & Product Positioning

### 1.1 Product Definition: The Reverse Search Engine for Candlestick Charts
`dtwmagic` is a **specialized search engine for financial time-series**. 

Just as Google Reverse Image Search takes an image and finds identical or visually similar images across the web, `dtwmagic` takes a specified candlestick pattern (e.g., the last 10 sessions of NIFTY 50 or any NSE stock) and searches 15+ years of historical market data to find the closest matching historical episodes under analogous market regimes.

### 1.2 Clear Boundary: Search Engine vs. Advisory Platform

To maintain strict compliance with SEBI regulations and serve serious traders, the platform maintains a hard boundary:

| What This Platform IS (The Search Engine) | What This Platform IS NOT (Forbidden Advisory) |
| :--- | :--- |
| **A Historical Search Engine:** Finds historical chart shapes mathematically similar to the query window. | **NOT an Investment Advisor:** Does not advise to Buy, Sell, Hold, Enter, or Exit. |
| **Descriptive Historical Statistics:** Displays what price did *in the past* during matched episodes. | **NOT a Prediction Engine:** Zero predictive modeling, zero machine-learning black boxes, zero price targets. |
| **User-Driven Research Tool:** The user inputs the query (stock, timeframe, lookback) and draws their own conclusions. | **NOT a Tip / Signal Service:** No "hot stock" watchlists, no automated trading calls. |
| **Objective Volatility Context:** Reports historical Maximum Adverse Excursion (MAE) observed in past matches. | **NOT a Stop-Loss Calculator:** Does not tell the user where to place risk stops. |

### 1.3 Why Serious Traders Pay for a Historical Search Engine
Discretionary traders routinely make decisions influenced by **recency bias** and **selective memory** (*"I remember a consolidation like this rallied hard last year"*). 
Manual chart scrolling across 15 years of daily data for 500+ stocks is humanly impossible.
`dtwmagic` provides **instant historical precedent**:
- "Has this geometrical shape occurred before under a similar Trend & Volatility regime?"
- "In those past episodes, how did the market behave over the subsequent 1 to 10 sessions?"
- "What was the range of historical drawdowns and run-ups observed during those past episodes?"

---

## 2. Target Personas & Monetization Model

### 2.1 Target Personas
1. **The Discretionary Swing / Options Trader:**
   - Needs empirical precedent to sanity-check setups before risking capital. Eliminates guesswork.
   - Willingness to pay: ₹999 – ₹1,999 / month.
2. **The Quantitative / Systematic Trader:**
   - Wants programmatic access and screener filters to identify stocks whose current price action matches historical fractal clusters.
   - Willingness to pay: ₹2,999 – ₹4,999 / month.
3. **Proprietary Desks & Financial Analysts:**
   - Research tool to audit historical market analogues across 2,000+ NSE equities for scenario analysis.
   - Willingness to pay: ₹15,000 – ₹25,000 / month.

### 2.2 Freemium Subscription Tiers (Technology Access Only)
- **Free Tier (Lead Gen):**
  - Universe: NIFTY 50 Index only.
  - Lookback: Fixed 10-day pattern window.
  - Results: Top 3 historical analogs with basic historical return distribution.
  - Updates: Daily End-of-Day (EOD).
- **Pro Tier (₹1,499 / month):**
  - Universe: All Nifty 500 stocks + sectoral indices.
  - Lookback: Flexible 5 to 60-day query windows.
  - Results: Top 10 historical analogs + full historical outcome cone (T+1 to T+10).
  - Metrics: Historical Observed MAE / MFE excursion profiles + historical ghost overlays.
  - Screener: User-configured mathematical similarity screener across Nifty 500.
- **Elite Tier (₹3,499 / month):**
  - Universe: Complete 2,000+ NSE cash equities database.
  - Multi-Timeframe: Daily, 1-hour, and 15-minute search queries.
  - Custom Alerts: User-defined in-app technical threshold alerts (e.g., *"Pattern distance < 0.15"*).
  - Export: Bulk historical research data download (CSV/JSON).

---

## 3. Feature Catalog with Explicit End-User Value & Monetization Rationale

Per project mandate, **every single feature must have an explicit end-user value proposition and monetization justification**:

| # | Feature Name | Quantitative Search Mechanics | End-User Value Proposition (Why Users Pay) | Monetization Tier |
|---|---|---|---|---|
| **F-01** | **Multi-Horizon Pattern Query Engine** | Z-score normalized Euclidean distance + Sakoe-Chiba constrained DTW across Short (5–15 bars) and Medium/Long (20–60 bars) windows. | **Eliminates confirmation bias & chart hunting.** Saves 2–3 hours daily of scanning charts. Gives instant mathematical proof of whether a chart setup has historical precedent. | Free (10-bar only) / Pro (Custom 5–60 bars) |
| **F-02** | **2-Factor Regime Conditioning Filter** | Categorizes market state into 4 quadrants: Trend (EMA 50/200 slope) $\times$ Volatility (ATR percentile). Matches only against historical episodes sharing identical market regime. | **Prevents false historical analogies.** Comparing a bull-market consolidation with a bear-market crash leads to invalid conclusions. Filtering by regime ensures apples-to-apples historical comparison. | Free (Current regime only) / Pro (Custom regime filters) |
| **F-03** | **Historical Outcome Distribution Cone (T+1 to T+10)** | Quantile distribution ($10^{\text{th}}$, $25^{\text{th}}$, Median, $75^{\text{th}}$, $90^{\text{th}}$ percentiles) of returns observed across matched historical episodes. | **Contextualizes historical follow-through.** Shows empirical distribution of how past instances unfolded, helping traders understand historical baseline volatility and dispersion. | Free (Median only) / Pro (Full Quantile Cone) |
| **F-04** | **Historical Excursion Profiler (Observed MAE / MFE)** | Computes historical Maximum Adverse Excursion (deepest drawdown) and Maximum Favorable Excursion (peak run-up) of matched analogs. | **Empirical Volatility Context.** Displays historical price oscillation ranges observed in past analogs, giving traders factual data to assess volatility depth before a move completed. | Pro Feature (Key conversion driver) |
| **F-05** | **Historical Analog Ghost Chart Overlay** | Overlays top 3–5 matched historical price trajectories directly on top of the live candle chart, labeled with exact historical dates. | **Visual historical audit.** Retail traders are visual. Seeing the exact historical chart from Oct 2020 or Jun 2022 overlaid gives immediate clarity and transparency into past market action. | Free (Top 1) / Pro (Top 5 + Ghost paths) |
| **F-06** | **Nifty 500 Pattern Query Screener** | Batch scanner running EOD allowing users to filter stocks by user-selected mathematical similarity thresholds and sample size. | **Saves hours of manual scanning.** Instantly surfaces stocks currently exhibiting high mathematical similarity to historical setups based on user-defined criteria. | Pro / Elite only |
| **F-07** | **Candlestick Wick & Volume Shape Weighting** | Multi-channel vector distance: Close trajectory (60%) + Wick rejection ratio (20%) + Normalized Volume profile (20%). | **Refined geometrical matching.** Enables nuanced multi-attribute shape matching incorporating wick dynamics and volume distribution. | Elite Feature |

---

## 4. The "Kailash Nadh" Architecture Blueprint (Scale to 2,000+ Stocks)

### 4.1 Kailash Nadh Principles Applied
1. **Radical Simplicity:** No Kubernetes clusters, no Kafka event buses, no microservice sprawl, no cloud vendor lock-in.
2. **Frugal Cost Footprint:** The entire compute and serving pipeline for 2,000+ stocks runs on a **single $10–$20/month Hetzner/Linode VPS** with 4 vCPUs and 8GB RAM. Zero recurring AWS enterprise bills.
3. **Pre-computation over Live Computation:** Markets close at 3:30 PM IST. 99% of swing research happens after 4:00 PM. We compute all 2,000 stocks in a single nightly batch job taking **< 90 seconds**, dump results to flat files/SQLite, and serve static JSON.
4. **Boring, Rock-Solid Data Formats:** Apache Parquet for raw OHLCV time-series + SQLite for indexed pattern analogs and pre-computed stats.
5. **Ultra-Fast Edge Serving:** A tiny Go or Python (FastAPI/Uvicorn) backend serves cached JSON with sub-10ms latency. The frontend is a static single-page app (SPA) with zero heavy framework bloat.

### 4.2 System Architecture Diagram

```
+-----------------------------------------------------------------------------------+
|                            DATA INGESTION (EOD Batch)                             |
|  - NSE Bhavcopy ZIP (Free, official, daily at 4:30 PM IST)                        |
|  - Fallback: yfinance / Kite Connect Daily Historical API                         |
|  - Clean & store raw OHLCV into local Parquet partitions: data/parquet/{symbol}   |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                        QUANT COMPUTE ENGINE (Python / NumPy)                       |
|  - Runtime: < 90 seconds for 2,000 stocks (Multiprocessing across 4 cores)        |
|  1. Compute 2-Factor Regimes (Trend EMA + ATR Quantiles)                          |
|  2. Z-Score normalize sliding windows (10-bar, 20-bar, 30-bar)                    |
|  3. Fast Matrix Dot-Product Distance / Sakoe-Chiba DTW against history            |
|  4. Extract Top-5 historical analogs + forward paths (T+1 to T+10)                |
|  5. Compute Observed MAE, MFE, Return Distribution, Match Quality Score           |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                          STORAGE & CACHE (Local & Lean)                           |
|  - SQLite database (analogs.db) ~ 50 MB total                                     |
|  - Static JSON snapshots: /static/api/v1/{symbol}.json                            |
|  - Can be served straight off Nginx or Cloudflare CDN for $0 egress cost          |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                        DELIVERY LAYER (Web Dashboard)                             |
|  - High-performance, lightweight UI (Vanilla JS / Canvas / TradingView library)   |
|  - Institutional Dark Mode aesthetic (Dark slate, clean gridlines)                |
|  - Zero heavy React hydration lag; instantaneous load times (< 200ms)             |
|  - Non-predictive display: Pure search results, ghost overlays & historical stats  |
+-----------------------------------------------------------------------------------+
```

### 4.3 Computational Complexity & Optimization
- **Data size for 2,000 stocks:**
  - 15 years daily data $\approx 3,750$ bars per stock.
  - 2,000 stocks $\times 3,750$ bars $\times 5$ floats (OHLCV) $\approx 150 \text{ MB}$ raw data.
  - Fits entirely into RAM in seconds.
- **Pattern Matching Speed:**
  - Finding the closest 10-bar pattern across 3,750 historical bars:
    - Naive DTW: $3,750 \times 10^2 = 3.75 \times 10^5$ operations (slow if unvectorized).
    - **Vectorized Z-normalized Euclidean Distance:** Sliding window dot-product using NumPy strides takes **< 1.5 milliseconds per stock**.
    - For 2,000 stocks: $2,000 \times 1.5\text{ ms} = 3.0\text{ seconds}$ total compute on a single modern CPU!
  - We use Fast Vectorized Euclidean distance to filter to Top 50 candidates, then refine with Sakoe-Chiba DTW on just those 50 candidates in 5ms. Total run time per stock: **under 10ms**.

---

## 5. Mathematical & Quantitative Formulation

### 5.1 Trajectory Normalization (Z-Score of Cumulative Percentage)
Raw prices cannot be compared across different index levels or eras (e.g. Nifty at 6,000 vs 25,000).
For any window $W = [p_0, p_1, \dots, p_L]$:
1. Compute relative trajectory:
   $$r_t = \frac{p_t}{p_0} - 1 \quad \text{for } t = 0, \dots, L$$
2. Compute Z-score normalization:
   $$\mu_W = \frac{1}{L+1} \sum_{t=0}^L r_t, \quad \sigma_W = \sqrt{\frac{1}{L+1} \sum_{t=0}^L (r_t - \mu_W)^2}$$
   $$z_t = \frac{r_t - \mu_W}{\sigma_W + \epsilon}$$

### 5.2 Distance Function
- **Primary Fast Filter:** Z-Normalized Euclidean Distance:
  $$D_{\text{Euc}}(Q, H) = \sqrt{\sum_{t=0}^L (z_{Q,t} - z_{H,t})^2}$$
- **Secondary Refinement:** Constrained Dynamic Time Warping (Sakoe-Chiba Band with window $w = \max(1, \lfloor 0.15 \times L \rfloor)$). Prevents temporal over-warping.

### 5.3 2-Factor Regime Classification
Every historical date $t$ is mapped into a regime state $R_t = (T_t, V_t)$:
1. **Trend Factor ($T_t$):**
   - $\text{Bullish}$: $\text{Close}_t > \text{EMA50}_t$ and $\text{EMA50}_t > \text{EMA200}_t$
   - $\text{Bearish}$: $\text{Close}_t < \text{EMA50}_t$ and $\text{EMA50}_t < \text{EMA200}_t$
   - $\text{Neutral/Consolidation}$: Any other configuration.
2. **Volatility Factor ($V_t$):**
   - Normalized ATR: $\text{NATR}_t = \frac{\text{ATR}_{14,t}}{\text{Close}_t}$
   - Percentile rank over rolling 252 trading days:
     - Low: $0\text{--}33^{\text{rd}}$ percentile
     - Normal: $33^{\text{rd}}\text{--}66^{\text{th}}$ percentile
     - High: $66^{\text{th}}\text{--}100^{\text{th}}$ percentile
3. **Filtering Rule:** Only historical windows matching today's Trend and Volatility bin are included in the analog candidate pool.

### 5.4 Historical Forward Excursion Statistics ($H = 1, 3, 5, 10$ bars)
For the top $K$ analogs, where historical pattern ends at index $\tau_k$:
- **Historical Forward Return:** $R_{k, h} = \frac{p_{\tau_k + h}}{p_{\tau_k}} - 1$
- **Historical Maximum Adverse Excursion (MAE):**
  $$\text{MAE}_{k, h} = \min_{1 \le j \le h} \left( \frac{\text{Low}_{\tau_k + j}}{p_{\tau_k}} - 1 \right)$$
- **Historical Maximum Favorable Excursion (MFE):**
  $$\text{MFE}_{k, h} = \max_{1 \le j \le h} \left( \frac{\text{High}_{\tau_k + j}}{p_{\tau_k}} - 1 \right)$$
- **Historical Positive Return Frequency:** Proportion of matched historical instances that closed positive at horizon $H$ (e.g. 7 out of 10 matches).
- **Match Quality Score:** Mathematical index based on Z-score Euclidean distance and regime alignment (Scale: 0–100%).

---

## 6. Web Visualization Dashboard Requirements

### 6.1 Design Language
- **Theme:** Dark mode, institutional trading terminal (dark slate background `#0d1117`, clean gridlines, emerald green `#26a69a` and crimson red `#ef5350` candles, high contrast metrics).
- **Zero Distraction:** Clean hierarchy. No promotional gimmicks, "hot picks", or flashing lights.

### 6.2 Key Screen Components
1. **Search Query Header & Context Bar:**
   - Active Symbol (e.g. `NIFTY 50`, `RELIANCE.NS`)
   - Historical Regime Tag (e.g. `HISTORICAL REGIME: BULLISH TREND | LOW VOLATILITY (22nd %ile)`)
   - Pattern Window Selector (5d, 10d, 15d, 30d)
2. **Interactive Chart View (Pure Historical Comparison):**
   - Left side: Current candlestick pattern window (last $N$ bars).
   - Right side: Historical Ghost Overlays (Top 3 historical patterns projected forward from current price).
   - Historical Empirical Distribution Cone showing 25th–75th percentile forward paths of matched dates.
3. **Historical Statistics Summary Table (Descriptive Past):**
   - Historical Sample Positive Frequency at T+3, T+5, T+10
   - Historical Median Forward Return (+X.X%)
   - Historical Observed MAE (80th percentile historical drawdown)
   - Historical Observed MFE (Median peak move)
4. **Historical Matches Drawer:**
   - Cards showing each matched date (e.g., `24-Nov-2020`, `12-May-2021`).
   - Mathematical similarity score (e.g., `94.2% match`).
   - Observed historical outcome (`+3.4% in 5 days`, Max Drawdown `-0.4%`).
   - Contextual data: Macro/VIX conditions on that historical date.
5. **Mandatory Persistent Compliance Footer:**
   - Explicit disclaimer and technology platform declaration visible on every page.

---

## 7. Delivery Roadmap & Non-Functional Requirements

### 7.1 Performance Benchmarks (SLAs)
- **Batch Processing Time:** $\le 90$ seconds for 2,000 NSE stocks on a 4-core machine.
- **API Response Latency:** $\le 15$ milliseconds for any symbol endpoint.
- **Frontend Page Load:** $\le 300$ milliseconds first meaningful paint (under 100 KB total bundle).

### 7.2 Implementation Phases
- **Phase 1 (Current Scope):** Core quantitative pattern retrieval engine on NIFTY 50 (`^NSEI`) + standalone interactive web dashboard.
- **Phase 2:** Automated EOD pipeline for NIFTY 500 stocks + SQLite database + configurable technical pattern screener.
- **Phase 3:** Full 2,000+ NSE universe, user authentication, subscription billing, and in-app/email technical threshold alerts.

---

## 8. SEBI Regulatory Compliance & Safe Harbor Architecture

To operate publicly and charge commercial subscriptions without requiring registration as a SEBI Registered Investment Adviser (RIA) or Research Analyst (RA), the platform is architected under the **Technology Platform & Data Analytics Safe Harbor** (identical to Chartink, TradingView, and Screener.in):

### 8.1 Forbidden Features & Language (Strictly Barred from UI & Marketing)
1. **No Recommendations / Trade Calls:** Never use words such as "Buy", "Sell", "Hold", "Entry", "Exit", "Call", or "Tip".
2. **No Target Prices or Stop-Losses:** Never provide "Suggested Stop-Loss" or "Suggested Target". All risk metrics are labeled strictly as historical observations: *"Historical 80th %ile Adverse Excursion (MAE)"*.
3. **No Predictions or Future Guarantees:** The tool makes zero forward predictions. It is strictly a historical pattern retrieval search engine.
4. **No External Broadcast Groups:** No automated Telegram/WhatsApp channels blasting trade setups. Notifications are strictly user-configured in-app technical alerts.

### 8.2 Mandatory Statutory Disclaimers

#### A. Persistent Global Footer (Visible on Every Page)
> **Statutory Disclosure & Disclaimer:**  
> *`dtwmagic` is an independent financial technology and data analytics platform designed strictly for educational, research, and historical pattern search purposes. We are NOT registered with SEBI as an Investment Adviser (RIA) or Research Analyst (RA). This platform does not provide investment advice, buy/sell recommendations, price targets, stop-loss levels, or financial guidance of any kind. All information displayed represents historical mathematical pattern similarities and past descriptive price data. Past historical pattern frequencies and price movements do not guarantee, indicate, or predict future market movements. All trading and investment decisions are the sole responsibility of the user. Securities trading involves substantial risk of financial loss.*

#### B. Onboarding Terms of Service Acceptance Modal
Users must actively check the box before accessing the tool:
- [ ] *I acknowledge that `dtwmagic` is a technical search engine for historical chart data and does not offer trading advice, stock recommendations, or price predictions.*
- [ ] *I understand that historical pattern occurrences are purely descriptive and do not guarantee future performance.*

#### C. In-App Metric Tooltips (Contextual Safe Harbor)
- **Observed MAE Tooltip:** *"Maximum Adverse Excursion (MAE) reflects the deepest historical drawdown observed in this matched historical sample between T+0 and T+10. This is historical empirical data, NOT a recommended stop-loss."*
- **Observed MFE Tooltip:** *"Maximum Favorable Excursion (MFE) reflects the peak historical gain reached in this matched historical sample. This is historical empirical data, NOT a target price."*
- **Positive Frequency Tooltip:** *"Displays the historical proportion of matched episodes where price closed positive at horizon T+H. This represents past sample frequency, NOT a future win probability."*
