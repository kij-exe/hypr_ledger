# Understanding Trade vs Position Taint

## The Key Difference

### Individual Trades (Fill-level)
- **`tainted=false`**: This specific trade **IS** attributed to the target builder
- **`tainted=true`**: This specific trade is **NOT** attributed to the target builder

### Position States (Lifecycle-level)
- **`tainted=false`**: The entire position lifecycle contains **ONLY** builder-attributed trades
- **`tainted=true`**: The position lifecycle contains **AT LEAST ONE** non-builder trade
- **`tainted=null`**: Cannot determine (no builder data available)

## Why They're Different

A position lifecycle can span multiple trades. The lifecycle is tainted if **any** trade in it is non-builder.

### Example Scenario

User opens a BTC long position with 3 trades:

```
Trade 1: Buy 1 BTC @ $90,000  → Builder-attributed (tainted=false)
Trade 2: Buy 1 BTC @ $90,500  → Builder-attributed (tainted=false)  
Trade 3: Buy 1 BTC @ $91,000  → NOT builder (different execution venue) (tainted=true)
```

**Individual Trade View** (`/v1/trades?builderOnly=true`):
- Shows only Trade 1 and Trade 2 (filters out tainted trades)
- Both have `tainted=false`

**Position View** (`/v1/positions/history?builderOnly=true`):
- All position states show `tainted=true`
- Why? Because the **lifecycle** contains Trade 3 (non-builder)
- The entire lifecycle is marked tainted, even at timestamps before Trade 3

## Visual Example

```
Timeline of Position Lifecycle:
├─ t1: Trade 1 (builder) → Position @ t1: tainted=TRUE (lifecycle will contain non-builder)
├─ t2: Trade 2 (builder) → Position @ t2: tainted=TRUE (lifecycle will contain non-builder)  
├─ t3: Trade 3 (NOT builder) → Position @ t3: tainted=TRUE (lifecycle contains non-builder)
└─ t4: Close position → Lifecycle ends

Individual Trades when builderOnly=true:
├─ Trade 1: tainted=FALSE ✓ (included)
├─ Trade 2: tainted=FALSE ✓ (included)
└─ Trade 3: tainted=TRUE ✗ (excluded from results)
```

## API Behavior

### `/v1/trades?builderOnly=true`
1. Fetches all fills
2. Matches each fill against builder CSV
3. Marks each fill individually:
   - `tainted=false` if matched
   - `tainted=true` if not matched
4. **Filters out** trades with `tainted=true`
5. Returns only builder-attributed trades

### `/v1/positions/history?builderOnly=true`
1. Fetches all fills
2. Matches fills against builder CSV
3. Reconstructs position lifecycles
4. For each lifecycle:
   - If **any** fill is non-builder → mark **entire lifecycle** `tainted=true`
   - If **all** fills are builder → mark lifecycle `tainted=false`
5. Returns all position states with taint flag
6. **Frontend filters** positions with `tainted !== false`

## Why This Makes Sense

Builder-only mode wants to answer: **"Show me positions that were executed EXCLUSIVELY through the target builder"**

- A single non-builder trade in a lifecycle "taints" the entire position
- This prevents partial attribution (lifecycle mixing multiple venues)
- Ensures clean builder-only metrics

## Testing

Compare the two endpoints:

```bash
# Get individual trades (builder-only)
curl "http://localhost:8000/v1/trades?user=0xb9e18a24143a1ad1b2a0a38a74b553733c0fdbb8&coin=BTC&fromMs=1766361600000&builderOnly=true"

# Get positions (builder-only)  
curl "http://localhost:8000/v1/positions/history?user=0xb9e18a24143a1ad1b2a0a38a74b553733c0fdbb8&coin=BTC&fromMs=1766361600000&builderOnly=true"
```

You'll see:
- **Trades**: Only builder-attributed fills (all `tainted=false`)
- **Positions**: Some have `tainted=true` if their lifecycle mixes builder and non-builder trades
