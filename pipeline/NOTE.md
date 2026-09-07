# Pipeline state at end of 2026-09-06 session

## Proven (against Samuel's committed March 3026 outputs)
- base-data / ship-data = pure CSV transforms — EXACT (0 mismatches)
- amount = leaderboard_score / 30 — EXACT
- volume = amount * price[t] (universe-wide price per material) — EXACT (max dev 1.9e-09)
- profit = amount * margin[t, recipe-set of company] — near-exact w/ universe margins (~0.3%);
  per-material margin constants exist per company recipe set (e.g. H2O 26.30 vs univ 25.87).
  Exact margins recoverable from any committed month: margin[t] = profit/amount in prod-data.
- totals = sum(individual) EXACT; universe volume/profit = sum(prod) EXACT (ratio 1.000000)
- Ranks verbatim from CSV — EXACT (0/40988)

## 14-month batch validation (2026-09-06): ALL PASS
- validate_all.py ship-data None-guard FIXED; ran clean mar25..apr26:
  base=OK all 14 months; ship OK where published (feb26+, SKIP before); price+margin
  tables extracted for all 14 months (also in cache/prices_*, cache/margins_*).

## SOLVED 2026-09-06: universe.companies
- = count of distinct companies with ANY PRODUCTION_ row in the CSV. Exact 13/14 months
  (sep25 committed value is 3 LOWER than CSV → source drift in Samuel's own snapshot;
  mar26 4,344 = 4,344 exact, likewise all others).

## SOLVED 2026-09-06: consumed — workforce component (EXACT)
- consumed[t] = Σ_tier workforce[tier] * FIO_workforceneeds[tier][t]  +  recipe inputs
  of producing buildings.
- FIO per-worker/day needs (rest.fnar.net /global/workforceneeds, KB dump 20260901):
  PIO: DW 4, RAT 4, OVE .5, PWO .2, COF .5 | SET: DW 5, RAT 6, KOM/EXO/PT/REP .5 each... (see KB)
- 17/24 workforce materials match EXACTLY (0.00% dev, all 14 months): NST LC VG HSS PDA
  GIN PDA KOM EXO PT REP ALE HMS SCN SC + OVE PWO COF(within-tier) etc.
- Cross-checks exact to the unit: PWO=COF (PIO), KOM=EXO=PT=REP (SET), ALE=HMS=SCN=SC (TEC),
  VG=GIN=HSS=PDA (ENG), and MED = TEC+ENG+SCI exactly every month.
- Universe workforce solved per month (cache/workforce_estimates.json). mar26:
  PIO 68,486 / SET 13,732 / TEC 6,305 / ENG 1,205 / SCI 384 (~4.9 workers/base).
  Ratio PIO:SET:TEC:ENG:SCI ≈ 100:20:9.2:1.76:0.56 — stable across all 14 months.
- Deviations from workforce-only = recipe inputs on top: DW +~800%, MED +~540%,
  RAT +~325%, FIM +~44-89%, WS +~55-72%, PWO/COF +~27-32%, others exact.

## SOLVED 2026-09-06: universe.bases — definition + source (RÉMI'S LEAD)
- universe.bases = TRUE game-wide count of company bases. The CSV BASES board is TRUNCATED
  at the LEAD UI's 25-row page boundary: every month's row count is an exact multiple of 25
  and rows SHRANK 2,950(jan26) -> 2,125(feb26). Earlier "complete/contiguous" reading was
  WRONG (contiguity masked by hundreds of score-1 ties at the bottom).
- Proof of truncation: producers (2,314-4,432/mo) > BASES rows every month — impossible for
  a full board since every producer owns >=1 base. Purge hypothesis REJECTED: 917 companies
  dropped off the board jan26->feb26, but 177 of them still produced in feb26 (only 5 had
  >=5 bases). Gap math: ~2,100 unseen companies x ~1.5 bases ~= committed-vs-CSV gap.
- LIVE SOURCE (FIO): GET /planet/sites/{Planet} per planet (public, no auth); a site row
  with OwnerId != PlanetId = company base (planet-owned rows = COGC/admin/shipyard).
  Census 2026-09-06 over all 4,576 planets (fio_census.py, resumable; analyzer
  analyze_census.py; archive cache/universe_census_20260906.json): 18,848 company sites,
  6,818 companies w/ sites, Kamalcorp = 24 (ground-truth match). vs committed apr26
  18,674 -> +0.93% = 4 months organic growth. DEFINITION CONFIRMED.
- PRUNplanner ruled out (own-empire endpoints only). FIO has no bulk sites endpoint;
  census = ~4.6k GETs (~5 min threaded, fix races: claim planets atomically from a queue).
- Future months: run census on the 1st alongside the LEAD capture.

## SOLVED 2026-09-07: monthly CXOB prices — public source found (extension saga closed)
- **PrUN-Collector-MP v0.9 forensics**: MAIN-world WS wrap (v0.8) + fetch/XHR instrumentation
  (v0.9) proved the game's CX order books and LEAD rows DO NOT flow over the game WebSocket
  anymore (49 raw WS frames during active CX/LEAD browsing = idle baseline; zero market
  types; on-demand queries not visible in page scope either => likely a Worker). Samuel's
  2025-era WS-capture design no longer sees market data in today's client.
- **THE DISCOVERY**: while CX screens are open, the *Refined PrUn* browser extension
  (Rémi has it installed) fetches `https://refined-prun.github.io/refined-prices/all.json`
  — a PUBLIC static snapshot of the ENTIRE COMEX CXOB: 2,214 entries (369 materials x
  6 exchanges AI1/CI1/CI2/IC1/NC1/NC2), full schema (Ask/Bid/PriceAverage/MMBuy/MMSell/
  Supply/Demand/VWAP7D+30D/TWAP7D+30D/Traded7D+30D/Open/Close/High/Low Yesterday/Timestamp).
  Schema is FIELD-IDENTICAL to raylu's *-prices.json files (his source = same frames data).
- **VERIFIED LIVE 2026-09-07T04:11Z**: file regenerated + pushed to GitHub Pages within the
  minute of capture (repo push 04:11:14 == data Timestamps 04:11:12); 9/9 spot checks vs
  Rémi's screen (GAL.NC1 330/221/PA329.25; H.NC1 136/125/125.95; SF.NC1 24.80/24.00/24.80)
  EXACT. 260 entries carry MMBuy (= MM-priced untradeables raylu hardcodes 29 of).
- Archive: pipeline/cache/refined-prices/all-20260907T0411Z.json. Monthly ritual becomes:
  curl all.json on the 1st (no extension dependence for prices), + LEAD capture + census.
- Open questions (non-blocking): who generates refined-prices and from what source (likely
  FIO-adjacent crowd pipeline; ask raylu/Samuel in outreach reply); raylu's LEAD capture
  method (gogs has no README; WS-vs-scraper unresolved; his next push + reply will tell).

## Extracted assets (this dir)
- prices_mar26_extracted.json — price+margin tables for 363 materials (from committed mar26)
- fio_recipes.json — full FIO recipe book (404 recipes / 336 materials)
- pipeline.py — full pipeline (CSV -> all 5 JSONs); `--margins`/`--price` inputs
- validate_all.py — 14-month batch validator — FIXED 2026-09-06, all months PASS
- cache/ — raw CSVs + committed outputs for ALL 14 months (universe_data.json, prod_*,
  prices_*, margins_*, *_base/*_ship, workforce_estimates.json)

## BACKFILL 3026 (may/jun/jul) — GENERATED 2026-09-06 (backfill_26.py -> backfill/)
- Source: raylu's repo `git.raylu.net/raylu/prunstats` rawData/ (gogs; raw path = /raw/main/...;
  API contents needs auth, web scraping works). may26/jun26/jul26.csv = COMPLETE months
  (BASES+SHIPS+PROD, 351-361 materials, deeper boards than Samuel's) + his CXOB snapshots
  (*-prices.json). aug26.csv = BASES+SHIPS only (production pending his Sept push). He also
  has 2424 months (jan-apr24) predating the site archive. Local copies: cache/raylu/.
- raylu's price model (py/prepare.py, published): price = Traded30D-weighted VWAP30D across
  exchanges + 29 hardcoded untradeable prices (ships/gateways). Hardcodes DIVERGE from
  Samuel's (round numbers, x0.33-x2.55) — OPEN DECISION: whose hardcodes to publish.
- margins: NOT recipe-constant across months (recomputed monthly by Samuel); stable-ratio
  backfill used: margin[t] = median(margin/price over committed months) * new price
  (staples H2O/GAL/H ratios stable ~±5%; volatile for near-zero-margin mats — labeled estimate).
- may26 dedupe: 88 duplicate (cat,company) rows from merged captures (Samuel Jun-1 + raylu);
  kept FIRST occurrence (5 score conflicts, e.g. ATA rank 6: 403 vs 402 — captures days apart).
- universe.bases: tail model (board sum + (producers - rows) x 1.4807, tail avg anchored on
  apr26 committed). NOTE: constant board-ratio was WRONG (depth-dependent; double-counted pads).
  may~18,443 jun~18,419 jul~19,136 — coherent with apr26 18,674 and census 18,848 (2026-09-06).
- Schema matches Samuel's committed files exactly except `consumed` absent (expected).
- Continuity apr26->jul26 smooth: universe volume 2.63B -> 2.81B; GAL 3.22M->3.60M/day
  (the 3026 GAL rally), H/RAT easing.
- **PUSHED 2026-09-06 (commit 6db337e) and LIVE-VERIFIED**: reports/data has the 12 files,
  universe-data.json merged (17 months), constants.ts extended, footer note added
  ("margins are estimated... have a better margin model? Open an issue!"), webpack
  rebuilt. Verified on kamalgar-projects.github.io: prod-data-jul26 200, universe keys
  include may/jun/jul26, footer live.
- CXOB price source monthly (RÉMI-CONFIRMED approach): FIO does NOT serve CXOB history
  publicly (/exchange/all = orderbooks only, no VWAP30D/Traded30D; /global/comexexchanges
  = registry only). raylu's prices.json = full COMEX_EXCHANGE_LIST frames captured by his
  game client. Monthly: pull raylu's repo (curl, free) when he pushes; independent
  fallback = extend PrUN-Collector with a COMEX_EXCHANGE_LIST filter (same passive-WS
  mechanism as LEADERBOARD_SCORES) so Rémi's own sessions capture it. Aggregation code
  already in backfill_26.py (raylu's get_prices verbatim).
- For profit EXACTNESS (not backfill): model overshoots real margins ~20-165% => Samuel's
  profit = price - inputs - more terms (wages? depreciation?). Remaining open item.

## Known open items
0. raylu outreach draft ready: ~/pmmg/revival/raylu-outreach-DRAFT.md (long+short versions;
   offers = profit/consumed model + 14mo price/margin tables + universe.bases census +
   duplicate/missing checker + redundant PrUN-Collector capture; asks = push heads-up +
   his eyes on the profit residual). Rémi reviews before sending.
1. consumed recipe-input component: model known (Σ building inputs × producing-building
   counts); building counts must be ESTIMATED (CSV gives per-company material amounts, not
   buildings). Next: least-squares building-count fit vs residuals (FIM/WS/RAT/DW/MED).
2. Backfill months (May-Aug 3026): no committed outputs => margins from recipe model or
   nearest month's extracted tables; volume/rank/amount exact regardless.
3. SITE: needs `reports/src/staticData/constants.ts` months[] update when publishing new months.
4. Monthly ritual: LEAD capture + FIO base census on the 1st.
