# Rejected Candidate: crypto_4h_zlmacd_86_85_2_exit36_slen3

Config:

configs/nnfx_crypto/crypto_4h_zlmacd_86_85_2_exit36_slen3_candidate.yml

Status:

Rejected by date-split validation.

Reason:

The system performed well in the development period but failed out-of-sample validation.

Development period:
2018-01-01 to 2022-12-31

Validation period:
2023-01-01 to 2026-05-09

Date-split results:

| Pair | Period | Net PnL % | Max DD % | PF | Positive Months % | Time Underwater % | Status |
|---|---|---:|---:|---:|---:|---:|---|
| BTC-USDT | Development | 84.49 | -19.45 | 1.35 | 56.90 | 98.02 | PASS |
| BTC-USDT | Validation | -21.44 | -25.86 | 0.39 | 2.56 | 99.66 | FAIL |
| ETH-USDT | Development | 146.69 | -10.23 | 1.89 | 68.97 | 96.23 | PASS |
| ETH-USDT | Validation | -21.41 | -24.86 | 0.36 | 5.13 | 99.79 | FAIL |
| SOL-USDT | Development | 47.99 | -15.15 | 1.57 | 66.67 | 97.28 | PASS |
| SOL-USDT | Validation | 29.65 | -17.13 | 1.21 | 48.72 | 98.62 | FAIL / near-pass |

Conclusion:

This 4h structure is overfit to the 2018–2022 regime and should not be promoted as a general multi-pair crypto 4h system.

Next branch:

Validation-period-first research:
- Tune on 2023–2026 first.
- Pairs: BTC-USDT, ETH-USDT, SOL-USDT.
- Goal: PF >= 1.25 on validation period first.
- Then test backward on 2018–2022.
