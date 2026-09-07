# PMMG reports pipeline (revival)

This is the reverse-engineered post-processing pipeline behind the reports in
`reports/data/` — the piece Samuel lost with his machine. Written by Miss Pringle
(Kamalgar's AI partner), validated against Samuel's committed outputs for every
month the original site published (mar25 → apr26).

**Formulas first** — this is what was missing from the repo (sorry, raylu — it lived
on our box and was never pushed):

## The model

| Quantity | Formula | Validation vs Samuel's outputs |
|---|---|---|
| `amount` | `leaderboard_score / 30` | EXACT, all months |
| `volume` | `amount × universe_price[t]` | EXACT (max dev 1.9e-09) |
| `profit` | `amount × margin[t, company's recipe-set]` | exact when per-company margins known; universe margins → ~0.3% off |
| `consumed` | `Σ_tier workforce[tier] × FIO_workforceneeds[tier][t] + recipe inputs of producing buildings` | 17/24 workforce materials EXACT to the unit across all 14 months; cross-checks exact (PWO=COF, KOM=EXO=PT=REP, MED=TEC+ENG+SCI) |
| `universe.bases` | true game-wide base count = FIO census: `GET /planet/sites/{Planet}` over all 4,576 planets, count sites with `OwnerId != PlanetId` | 18,848 measured (2026-09-06) vs 18,674 committed apr26 = +0.93% organic growth |
| `universe.companies` | count of distinct companies with ≥1 PRODUCTION row | EXACT 13/14 months (sep25 source drift in Samuel's own snapshot) |
| `prices` | Traded30D-weighted VWAP30D across exchanges (raylu's model, confirmed independent re-derivation) + MM prices for untradeables. We now source daily snapshots from `refined-prun.github.io/refined-prices/all.json` (public, full CXOB, schema identical to CXOB frames) | 364 materials priced; `DIS`/`WR` now have real market data where raylu hardcodes |
| `margin[t]` (per material) | NOT recipe-constant — Samuel recomputed monthly. Recoverable from any committed month: `margin[t] = profit/amount` per company, or `cache/margins_*.json` | extracted for all 14 committed months |

**Known open residual:** the profit model overshoots real margins ~20–165% for some
materials if computed as `price − inputs` — wages/depreciation terms are missing.
Samuel's exact margins are recoverable from his committed months; stable-ratio
estimation fills backfill months (labeled "estimated" in the site footer).

## Files

- `pipeline.py` — CSV → all 5 report JSONs (Samuel's schema, byte-compatible)
- `backfill_26.py` — may/jun/jul 3026 backfill generator (source: raylu's rawData + stable-ratio margins)
- `validate_all.py` — 14-month batch validator against Samuel's committed outputs (ALL PASS)
- `fio_census.py` / `analyze_census.py` / `archive_census.py` — universe.bases ground truth
- `NOTE.md` — full working notes: proofs, dead ends, open items
- `fio_recipes.json` — FIO recipe book (404 recipes / 336 materials)
- `prices_mar26_extracted.json` — Samuel's price+margin tables, extracted

The working cache (raw CSVs for all 14 months + Samuel's committed outputs + raylu
rawData mirror + refined-prices archive) is ~20 MB and lives off-repo; happy to
sync it on request.

## Provenance & credits

- Original site, data format, and capture method: **Samuel (PiBoy314)** — MIT, revived
  with his blessing ("free to use any tools I built for PrUn in any form").
- Backfill raw data + price model: **raylu** (`git.raylu.net/raylu/prunstats`).
- CXOB snapshots: refined-prun project (public `all.json`), spot-verified against
  live in-game order books.
- LEAD CSVs: captured in-game via the `__LEAD__` Top Ranks export (players × 30d boards).
