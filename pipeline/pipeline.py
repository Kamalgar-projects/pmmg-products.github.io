#!/usr/bin/env python3
"""
PMMG Financial Reports — post-processing pipeline (community revival)
Rebuilds Samuel's monthly data files from a raw PrUN-LEAD-Data CSV.

Model reverse-engineered from committed outputs (2026-09):
  amount     = leaderboard_score / 30          (30-day cumulative -> per-day)
  ranks      = verbatim from CSV
  volume     = amount * price[t]               (universe-wide price per material)
  profit     = amount * margin[t, company]     (recipe-derived; see margin source)
  totals     = sum of individual               (exact)
  universe   = sum of prod / counts            (exact)
  base/ship  = pure CSV transforms             (exact)

Margin sources, in priority order:
  1. --margins file (extracted from prior committed data, or a recipe model output)
  2. --margins none  -> profit omitted (site still renders volume/rank/amount charts)

Usage:
  python3 pipeline.py --csv PrUN-LEAD-Data-March-2026.csv --month mar26 \
      --margins prices_mar26.json --outdir reports/data [--dry-run]
"""
import argparse, collections, csv, json, os, sys

DAYS = 30
PROD_PREFIX, PROD_SUFFIX = "PRODUCTION_", "_DAYS_30"


def parse_leads(csv_path):
    """Return (ranks, base, ship): ranks[(ticker,id)]=(rank,score); base/ship[id]=(rank,score)."""
    ranks, base, ship = {}, {}, {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) < 4:
                continue
            cat, rank, score, eid = row[0], int(row[1]), float(row[2]), row[3]
            if cat.startswith(PROD_PREFIX) and cat.endswith(PROD_SUFFIX):
                ranks[(cat[len(PROD_PREFIX):-len(PROD_SUFFIX)], eid)] = (rank, score)
            elif cat == "BASES":
                base[eid] = (rank, int(score))
            elif cat == "SHIPS":
                ship[eid] = (rank, int(score))
            # ARC_LEVEL is not published by the site
    return ranks, base, ship


def build(ranks, base, ship, price, margin):
    # base-data / ship-data: pure transforms
    base_data = {eid: {"bases": s, "rank": r} for eid, (r, s) in base.items()}
    ship_data = {eid: {"ships": s, "rank": r} for eid, (r, s) in ship.items()}

    # prod-data: amount per material; volume/profit when price/margin available
    amount = collections.defaultdict(float)
    for (t, _eid), (_r, score) in ranks.items():
        amount[t] += score / DAYS
    prod_data = {}
    for t, a in amount.items():
        entry = {"amount": a}
        if t in price:
            entry["volume"] = a * price[t]
        if t in margin:
            entry["profit"] = a * margin[t]
        if t in margin and t in price:
            entry["consumed"] = a * (price[t] - margin[t]) / max(price[t], 1e-9)
        prod_data[t] = entry

    # individual: per company per material
    individual = collections.defaultdict(dict)
    for (t, eid), (r, score) in ranks.items():
        a = score / DAYS
        e = {"amount": a, "rank": r}
        if t in price:
            e["volume"] = a * price[t]
        if t in margin:
            e["profit"] = a * margin[t]
        individual[eid][t] = e

    # totals per company
    totals = {}
    for eid, mats in individual.items():
        totals[eid] = {
            "volume": sum(m.get("volume", 0.0) for m in mats.values()),
            "profit": sum(m.get("profit", 0.0) for m in mats.values()),
            "volumeRank": 0,
            "profitRank": 0,
        }
    for i, (eid, _e) in enumerate(sorted(totals.items(), key=lambda kv: -kv[1]["volume"]), 1):
        totals[eid]["volumeRank"] = i
    for i, (eid, _e) in enumerate(sorted(totals.items(), key=lambda kv: -kv[1]["profit"]), 1):
        totals[eid]["profitRank"] = i

    # universe
    universe = {
        "volume": sum(v.get("volume", 0.0) for v in prod_data.values()),
        "profit": sum(v.get("profit", 0.0) for v in prod_data.values()),
        "bases": sum(s for _r, s in base.values()),
        "companies": len(base),
    }
    return {
        "base-data": base_data,
        "ship-data": ship_data,
        "prod-data": prod_data,
        "company-data": {"totals": totals, "individual": dict(individual)},
        "universe-data": universe,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--month", required=True, help="e.g. mar26")
    ap.add_argument("--price", help="JSON {ticker: price} (universe-wide)")
    ap.add_argument("--margins", help="JSON {ticker: margin} or {ticker: {price, margin}}")
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    price, margin = {}, {}
    if args.margins:
        m = json.load(open(args.margins))
        for t, v in m.items():
            if isinstance(v, dict):
                price[t] = v["price"]; margin[t] = v["margin"]
            else:
                margin[t] = v
    if args.price:
        price.update(json.load(open(args.price)))

    ranks, base, ship = parse_leads(args.csv)
    out = build(ranks, base, ship, price, margin)

    if args.dry_run:
        print(json.dumps({k: (f"<{len(v)} entries>" if isinstance(v, (dict,)) else v)
                          for k, v in out.items()}, indent=1))
        return

    os.makedirs(args.outdir, exist_ok=True)
    for stem, data in out.items():
        path = os.path.join(args.outdir, f"{stem}-{args.month}.json")
        with open(path, "w") as f:
            json.dump(data, f, separators=(",", ":"))
        print(f"wrote {path} ({os.path.getsize(path):,} bytes)")


if __name__ == "__main__":
    main()
