# Hyperliquid Trade Ledger API

A dockerized service providing trade history, position reconstruction, cumulative PnL tracking, and leaderboards for Hyperliquid — with **optional builder-only mode** for Insilico (or any other builder) competitions.

## How to Run

```bash
docker-compose up --build
```

The API runs at **`http://localhost:8000`**

- **API docs**: http://localhost:8000/docs
- **Competition UI**: http://localhost:8000/competition

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `HYPERLIQUID_API_URL` | `https://api.hyperliquid.xyz` | Hyperliquid API base URL |
| `TARGET_BUILDER` | `0x2868fc0d9786a740b491577a43502259efa78a39` | Builder address for builder-only mode (defaults to Insilico) |

---

## Builder-Only Mode: How It Works

### What It Does

When `builderOnly=true` is passed to any endpoint:
1. **Trades**: Marks fills attributed not to `TARGET_BUILDER` **tainted**
2. **Positions**: Marks position lifecycles as **tainted** if ANY fill was non-builder
3. **PnL/Leaderboard**: Excludes tainted results from aggregates and rankings

### How Builder Attribution Is Obtained

**Source**: Builder-attributed fills are fetched from Hyperliquid's public CSV files:
```
https://stats-data.hyperliquid.xyz/Mainnet/builder_fills/{TARGET_BUILDER}/{YYYYMMDD}.csv.lz4
```

These CSVs contain all fills executed through a specific builder on a given day.

**Matching Algorithm**:
1. Fetch user fills from Hyperliquid Info API
2. Download builder CSVs for the date range
3. Match fills by:
   - User address (exact)
   - Coin (exact)
   - Side (exact)
   - Price (exact)
   - Size (exact)
   - Timestamp (within ±1 second tolerance)

4. Mark matched fills as **builder-attributed**

**Taint Detection** (Position Lifecycle):
- A **position lifecycle** starts when `netSize` moves from `0` → non-zero
- It ends when `netSize` returns to `0` (position closed)
- If **any fill** in the lifecycle is **not builder-attributed**, the entire lifecycle is marked `tainted=true`
- Tainted positions are excluded from builder-only leaderboards and visualizations

This ensures builder-only mode shows **exclusively** builder-executed positions.

### Limitations of Builder Attribution

**1. Inexact Matching**

The matching algorithm relies on heuristics rather than cryptographic proof:
- Matches are based on observable trade parameters (user, coin, side, price, size, timestamp)
- Timestamp tolerance (±1 second) may cause false positives in high-frequency scenarios
- No direct builder field exists in Hyperliquid's public API fills; attribution is inferred by matching against builder CSV data
- Edge cases (e.g., identical concurrent trades) may result in ambiguous attribution

**2. Performance Inefficiency**

Builder attribution requires retrieving and processing the complete builder trade history:
- **Data volume**: All fills executed by the builder for the requested date range must be downloaded (can exceed thousands of trades per day)
- **Decompression overhead**: CSV files are LZ4-compressed and must be decompressed before parsing
- **Filtering step**: The entire builder dataset must be filtered for each user's fills before matching
- **Matching complexity**: Each user fill requires comparison against the full set of builder fills, resulting in O(n × m) operations where n = user fills and m = builder fills for the date range

This approach is suitable for periodic leaderboard computation but may introduce latency for real-time queries with large date ranges.

---

## Competition UI

**`GET /competition`** - Interactive frontend for visualizing position changes and PnL

**Features**:
- **Live animation**: Replays position changes over time with smooth transitions
- **Builder-only toggle**: Exclude tainted positions from visualization
- **Multi-user comparison**: Plot multiple traders on same chart
- **Leaderboard**: Auto-generated rankings after animation completes
- **Charts**: Net position size + cumulative PnL over time

**Why use it**:
- **Demo-ready**: Instantly visualize competition results for judges/stakeholders
- **Validation**: Visually verify position reconstruction logic is correct
- **Exploration**: Quickly test different time ranges and coin filters
- **Builder attribution**: Toggle builder-only mode to see taint detection in action

---

## API Endpoints 

Full description is in the specification, short summary is given below

**Full API documentation / Swagger UI**: http://localhost:8000/docs (interactive OpenAPI)

### Core Endpoints

```
GET /v1/trades?user=&coin=&fromMs=&toMs=&builderOnly=false
GET /v1/positions/history?user=&coin=&fromMs=&toMs=&builderOnly=false
GET /v1/pnl?user=&coin=&fromMs=&toMs=&builderOnly=false&maxStartCapital=
GET /v1/leaderboard?users=&coin=&metric=pnl|volume|returnPct&builderOnly=false&maxStartCapital=
GET /v1/deposits?user=&fromMs=&toMs=  (bonus feature)
GET /health
```
