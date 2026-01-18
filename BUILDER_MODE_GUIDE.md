# Builder-Only Mode - Taint Detection Guide

## Overview

Builder-only mode identifies which position lifecycles contain non-builder fills and marks them as "tainted". Tainted positions are excluded from builder-only visualizations and leaderboards.

## How Taint Detection Works

### Position Lifecycle
- **Starts**: When `netSize` moves from `0` → non-zero
- **Active**: While position is open (netSize ≠ 0)
- **Ends**: When `netSize` returns to `0`

### Taint Rule
A position lifecycle is **tainted** if it contains **any** fill that is NOT attributed to the target builder.

### Taint Values
- `tainted=False`: Clean lifecycle - all fills are builder-attributed
- `tainted=True`: Tainted lifecycle - contains at least one non-builder fill
- `tainted=None`: Cannot determine - no builder data available for this user

## Expected Behavior

### Scenario 1: User trades through target builder
**Example**: `0xb9e18a24143a1ad1b2a0a38a74b553733c0fdbb8` on Dec 22, 2025
```
✓ Found 85 builder fills in CSV
✓ Matched 17/24 fills (70.8%)
✓ Result: 10 clean, 14 tainted positions
```
**Interpretation**: 
- This user trades through the builder
- Some lifecycles are 100% builder → `tainted=False`
- Some lifecycles have mixed fills → `tainted=True`

### Scenario 2: User does NOT trade through target builder
**Example**: `0x0e09b56ef137f417e424f1265425e93bfff77e17` on Dec 22, 2025
```
✓ Found 0 builder fills in CSV
✓ Matched 0/2 fills (0%)
✓ Result: All positions have tainted=None
```
**Interpretation**:
- This user doesn't use the target builder
- Cannot determine taint status (no builder data)
- `tainted=None` is correct - not "all tainted"

### Scenario 3: All positions tainted
```
⚠ Found 50 builder fills in CSV
⚠ Matched 30/40 fills (75%)
⚠ Result: ALL positions tainted
```
**Interpretation**:
- User trades through builder, but every lifecycle has at least one non-builder fill
- Each lifecycle mixes builder and non-builder fills
- This is a valid scenario (user uses multiple execution venues)

## Frontend Filtering

When `builderOnly` mode is enabled:

1. **Position History**: Filters `tainted !== false`
   ```javascript
   if (builderOnly) {
       positions = positions.filter(p => p.tainted === false);
   }
   ```

2. **Leaderboard**: Filters `tainted !== false`
   ```javascript
   if (builderOnly) {
       data = data.filter(entry => entry.tainted === false);
   }
   ```

**Important**: Only positions with `tainted=false` are shown. This excludes:
- Tainted positions (`tainted=true`)
- Unknown status (`tainted=null`)

## Testing

Run the test script to verify taint detection:
```bash
python test_taint_logic.py
```

The script will:
1. Test with a known builder user
2. Show match rates and taint statistics
3. Explain the results

## Common Issues

### Issue: "All positions show as tainted"
**Diagnosis**:
- Check if builder fills were found (log: "Found X builder fills from CSV")
- Check match rate (log: "Matched X/Y fills")
- If 0 builder fills → should be `tainted=None`, not `tainted=True`
- If high match rate but all tainted → check lifecycle logic

**Fix**: 
- Ensure `builder_fill_indices` is `None` when no builder data exists
- Check that lifecycle tracking resets when position closes

### Issue: "User has builder fills but all show tainted=None"
**Diagnosis**:
- Builder service might not be passed to position service
- Check if `builder_only=True` parameter is set

**Fix**:
- Verify API endpoint receives `builderOnly=true`
- Verify `BuilderService` is instantiated and passed

## Configuration

Set the target builder in `.env`:
```bash
TARGET_BUILDER=0x2868fc0d9786a740b491577a43502259efa78a39
```

Default builder is already configured if not specified.

## Logging

Enable debug logging to trace taint detection:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

You'll see:
- Builder CSV fetching
- Fill matching statistics
- Lifecycle taint decisions
