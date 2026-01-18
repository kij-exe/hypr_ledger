# Hyperliquid Trade Ledger API

A dockerized service providing trade history, position history, and PnL tracking for Hyperliquid.

## Quick Start

```bash
# One-command run with Docker Compose
docker-compose up --build
```

Or without Docker:
```bash
pip install -r requirements.txt
python -m src.main
```

The API will be available at `http://localhost:8000`.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `HYPERLIQUID_API_URL` | `https://api.hyperliquid.xyz` | Hyperliquid API base URL |
| `TARGET_BUILDER` | (none) | Builder address for builder-only mode |

## API Endpoints

### GET /v1/trades
Get normalized trade fills for a user.

**Parameters:**
- `user` (required): User address
- `coin`: Coin filter
- `fromMs`: Start time in milliseconds
- `toMs`: End time in milliseconds  
- `builderOnly`: Filter to builder-attributed trades only (default: false)

**Response:** Array of trades with fields:
- `timeMs`: Timestamp in milliseconds
- `coin`: Coin symbol
- `side`: "Buy" or "Sell"
- `px`: Price
- `sz`: Size
- `fee`: Fee amount
- `closedPnl`: Realized PnL from this trade
- `builder`: Builder address (optional)
- `tainted`: Whether trade is tainted (builder-only mode)

### GET /v1/positions/history
Get position history timeline for a user and coin.

**Parameters:**
- `user` (required): User address
- `coin` (required): Coin to get position history for
- `fromMs`: Start time in milliseconds
- `toMs`: End time in milliseconds
- `builderOnly`: Filter to builder-attributed trades only (default: false)

**Response:** Array of position states with fields:
- `timeMs`: Timestamp in milliseconds
- `netSize`: Net position size (positive=long, negative=short)
- `avgEntryPx`: Average entry price
- `realizedPnl`: Cumulative realized PnL
- `tainted`: Whether position is tainted (builder-only mode)

### GET /v1/pnl
Get PnL metrics for a user.

**Parameters:**
- `user` (required): User address
- `coin`: Coin filter
- `fromMs`: Start time in milliseconds
- `toMs`: End time in milliseconds
- `builderOnly`: Filter to builder-attributed trades only (default: false)
- `maxStartCapital`: Cap for capital normalization

**Response:** PnL result with fields:
- `realizedPnl`: Absolute USD value of realized PnL
- `returnPct`: Relative return percentage
- `feesPaid`: Total fees paid
- `tradeCount`: Number of trades
- `volume`: Total notional volume traded
- `tainted`: Whether result is tainted (builder-only mode)

### GET /v1/leaderboard
Get leaderboard ranking users by specified metric.

**Parameters:**
- `users` (required): Comma-separated list of user addresses
- `coin`: Coin filter
- `fromMs`: Start time in milliseconds
- `toMs`: End time in milliseconds
- `metric`: Ranking metric - `volume`, `pnl`, or `returnPct` (default: pnl)
- `builderOnly`: Filter to builder-attributed trades only (default: false)
- `maxStartCapital`: Cap for capital normalization

**Response:** Array of leaderboard entries with fields:
- `rank`: Ranking position (1 = best)
- `user`: User address
- `metricValue`: Value of the ranking metric
- `tradeCount`: Number of trades
- `tainted`: Whether entry is tainted (builder-only mode)

### GET /v1/deposits (Bonus Feature)
Get deposit tracking information for a user.

**Parameters:**
- `user` (required): User address
- `fromMs`: Start time in milliseconds
- `toMs`: End time in milliseconds

**Response:** Deposit tracking result with fields:
- `totalDeposits`: Total deposited amount in USD
- `depositCount`: Number of deposit transactions
- `deposits[]`: Array of individual deposits with `timeMs`, `amount`, `hash`, `txType`

**Purpose:** Enables filtering users who reloaded capital during competition window.

### GET /health
Health check endpoint.

## Builder-Only Mode

**Status:** Placeholder (flag accepted but not fully implemented)

When `TARGET_BUILDER` is set and `builderOnly=true`:
- Trades are filtered to those attributed to the target builder
- `tainted=true` is set when non-builder activity affects the same position lifecycle

**Limitations:**
- Builder attribution is obtained from the `builderFee` field in fills
- The Hyperliquid public API only returns the most recent 10,000 fills per user
- Historical equity is not available via public API (current equity used as fallback)

## Architecture

```
src/
├── models/          # Pydantic data models
├── datasources/     # Data source abstraction + Hyperliquid implementation
├── services/        # Business logic (trades, positions, pnl, leaderboard)
├── api/             # FastAPI routes and dependencies
├── config.py        # Configuration management
├── app.py           # Application factory
└── main.py          # Entry point
```

### Data Source Abstraction

The `DataSource` abstract class (`src/datasources/base.py`) provides:
- `get_user_fills()`: Retrieve fills for a user
- `get_user_equity()`: Get current account equity
- `get_user_equity_at_time()`: Get historical equity (if available)
- `get_user_deposits()`: Retrieve deposit/withdrawal ledger updates

This abstraction allows swapping to Insilico-HL or HyperServe with minimal changes.

See [BONUS_FEATURES.md](BONUS_FEATURES.md) for detailed bonus feature documentation.

## Bonus Features Implemented

### 1. Deposit Tracking ✅
- **Endpoint:** `GET /v1/deposits`
- **Purpose:** Track deposits to filter users who reloaded capital during competition
- Returns total deposits, deposit count, and individual deposit transactions
- Enables fair competition filtering

### 2. Risk Fields ✅
- **Fields:** `liqPx` (liquidation price), `marginUsed` on position responses
- Optional fields included in position history endpoint
- Note: Currently set to null as margin/liquidation data requires additional API calls

### 3. Partial Closes & Position Flips ✅
- Correctly handles partial position closes
- Properly tracks long → short and short → long transitions
- Average entry price recalculated on position flips
- Implemented in `PositionService._reconstruct_position_history()`

### 4. Multi-Coin Aggregation ✅
- **Portfolio-level PnL:** Omit `coin` parameter to get all-coins aggregate
- **Portfolio leaderboard:** Omit `coin` parameter for cross-asset ranking
- Example: `GET /v1/pnl?user=0x...` returns total PnL across all coins

## Limitations

1. **Fill limit**: Only the 10,000 most recent fills are available per user via public API
2. **Historical equity**: Not available via public API; current equity used as fallback for return % calculations
3. **Builder attribution**: Based on `builderFee` field presence in fills
4. **Risk fields**: `liqPx` and `marginUsed` are included in the schema but set to null (require additional API implementation)

## Examples

```bash
# Get trades for a user
curl "http://localhost:8000/v1/trades?user=0x0e09b56ef137f417e424f1265425e93bfff77e17"

# Get position history for BTC
curl "http://localhost:8000/v1/positions/history?user=0x0e09b56ef137f417e424f1265425e93bfff77e17&coin=BTC"

# Get PnL with time range
curl "http://localhost:8000/v1/pnl?user=0x0e09b56ef137f417e424f1265425e93bfff77e17&fromMs=1704067200000&toMs=1706745600000"

# Get leaderboard
curl "http://localhost:8000/v1/leaderboard?users=0xabc...,0xdef...&metric=pnl"

# Get deposits (bonus feature)
curl "http://localhost:8000/v1/deposits?user=0x0e09b56ef137f417e424f1265425e93bfff77e17&fromMs=1704067200000"

# Get portfolio-level PnL (multi-coin aggregation)
curl "http://localhost:8000/v1/pnl?user=0x0e09b56ef137f417e424f1265425e93bfff77e17"
```
