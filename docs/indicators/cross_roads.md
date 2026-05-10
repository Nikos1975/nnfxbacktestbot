# Cross Roads Indicator

## Overview
Cross Roads is a two-line confirmation indicator and exit signal used in the NNFX system. It draws two weighted-moving-average-style lines (Green and Magenta) over the price. 

**Important:** This documentation describes a manual Python approximation of the Cross Roads indicator based entirely on public descriptions, visible settings, and screenshots. **No EX4 decompilation or reverse-engineering of compiled binaries was performed.**

## Source-Derived Facts
- **Role:** Confirmation indicator / Exit indicator.
- **Type:** Chart overlay.
- **Sub-type:** Two-line cross.
- **Testing context:** Daily timeframe, 3 years span. Risk profile: 2%, BTC/USD stop loss: ATR x 1.25. Beginning balance: $100,000.
- **Signal Rules:**
  - **Long Signal (+1):** Green line crosses *above* Magenta line.
  - **Short Signal (-1):** Green line crosses *below* Magenta line.

## Visible Settings & Constraints
1. **`StartLen`**:
   - Default: `2`
   - Purpose: Ignores the most recent N bars to filter out immediate price noise.
   - Constraints: Must be `>= 0` and `< LOOKBACK_period`.
2. **`LOOKBACK_period`**:
   - Default: `24`
   - Purpose: The primary rolling window for the calculations.
   - Constraints: Must be `>= 2`.

## Current Approximation Logic (v0)
Because the proprietary exact formula is unknown, the current implementation uses a WMA logic filter:
1. Shift the price back by `StartLen` periods.
2. Calculate the highest and lowest shifted prices over `LOOKBACK_period`.
3. Apply a Weighted Moving Average (WMA) to the highest prices to approximate the **Green** line.
4. Apply an Inverse Weighted Moving Average (Inv-WMA) to the lowest prices to approximate the **Magenta** line.

## Unknown Formula Limitations
- The exact proprietary filter used to generate the lines in the EX4 file is hidden.
- Our WMA/Inv-WMA approximation may not match exactly tick-for-tick. 
- Validation against MT4 exported values is **required** before claiming this indicator is fully accurate.
