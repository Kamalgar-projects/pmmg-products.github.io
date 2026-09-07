#!/usr/bin/env python3
"""Generate May/Jun/Jul 3026 backfill months from raylu's raw captures.

Prices: raylu VWAP30D aggregation (his get_prices logic, incl. hardcoded untradeables).
Margins: stable-ratio backfill — margin[t] = ratio[t] * price[t], ratio[t] = median of
         margin/price over committed months (mar25..apr26); untradeable hardcode prices
         get their committed-month margin scaled by price change apr26->now.
Dedupe: may26 duplicate (cat,company) rows -> keep FIRST occurrence in file order
        (Samuel's Jun-1 capture precedes raylu's re-capture); 88 rows, 5 score conflicts.
Universe.bases: board_sum * coverage_ratio(apr26 true/board) — documented estimate.
Universe.companies: distinct PRODUCTION companies (proven exact method).
"""
import csv, json, collections, os, sys

D = "/home/rnadeau/pmmg/revival/pipeline/cache/raylu/"
CACHE = "/home/rnadeau/pmmg/revival/pipeline/cache"
OUT = "/home/rnadeau/pmmg/revival/pipeline/backfill"
DAYS = 30

# ---------- raylu price aggregation (his logic verbatim) ----------
HARDCODED = {'AFP':65638,'ANZ':70601,'BFP':23408,'BSU':605062,'CPU':1426423,'CRU':171386,
'DIS':19583,'GCH':18303,'GNZ':30361,'GWS':9778478,'HAM':4686751,'HNZ':93580,'IMM':101522,
'JUI':0,'NOZ':74525,'PFG':2677222,'PK':1144,'RDS':598170,'SDM':1721027,'SST':5863587,
'SU':157860,'SUD':84327,'TAC':245797,'TOR':540169,'VCB':673713,'VFT':1781416,'VOE':3699358,
'VOR':2547315,'WR':129412}

def raylu_prices(month):
    raw = json.load(open(D+f"{month}-prices.json"))
    vol, trd = collections.defaultdict(float), collections.defaultdict(int)
    for e in raw:
        if e.get("Traded30D") is None or e.get("VWAP30D") is None: continue
        vol[e["MaterialTicker"]] += e["VWAP30D"] * e["Traded30D"]
        trd[e["MaterialTicker"]] += e["Traded30D"]
    prices = {t: vol[t]/trd[t] for t in vol if trd[t] > 0}
    prices.update({t: v for t, v in HARDCODED.items() if t not in prices})
    return prices

# ---------- margin ratios from committed months ----------
CM = ["mar25","apr25","may25","jun25","jul25","aug25","sep25","oct25","nov25","dec25","jan26","feb26","mar26","apr26"]
ratios = collections.defaultdict(list)
for m in CM:
    P = json.load(open(f"{CACHE}/prices_{m}.json"))
    M = json.load(open(f"{CACHE}/margins_{m}.json"))
    for t, mg in M.items():
        if P.get(t, 0) > 0 and mg is not None:
            ratios[t].append(mg / P[t])
RATIO = {t: sorted(v)[len(v)//2] for t, v in ratios.items()}

# ---------- read raylu csv with first-occurrence dedupe ----------
def read_csv(month):
    data, seen = collections.defaultdict(list), set()
    with open(D+month+".csv") as f:
        for row in csv.reader(f):
            if len(row) < 4: continue
            cat, rank, score, eid = row[0], int(row[1]), int(row[2]), row[3]
            key = (cat, eid)
            if key in seen:      # duplicate capture row -> keep first (Samuel's)
                continue
            seen.add(key)
            data[cat].append((rank, score, eid))
    return data

# ---------- build month ----------
def build(month):
    price = raylu_prices(month)
    data = read_csv(month)
    base = {eid: {"bases": s, "rank": r} for r, s, eid in data["BASES"]}
    ship = {eid: {"ships": s, "rank": r} for r, s, eid in data["SHIPS"]}

    ranks = collections.defaultdict(list)   # ticker -> [(rank, score, eid)]
    for cat, rows in data.items():
        if cat.startswith("PRODUCTION_") and cat.endswith("_DAYS_30"):
            t = cat[len("PRODUCTION_"):-len("_DAYS_30")]
            ranks[t].extend(rows)

    prod, individual = {}, collections.defaultdict(dict)
    for t, rows in sorted(ranks.items()):
        amount = sum(s for _r, s, _e in rows) / DAYS
        entry = {"amount": amount}
        if t in price:
            entry["volume"] = amount * price[t]
            mg = RATIO.get(t)
            if mg is not None:
                entry["profit"] = amount * mg * price[t]
        prod[t] = entry
        for r, s, eid in rows:
            a = s / DAYS
            e = {"amount": a, "rank": r}
            if t in price:
                e["volume"] = a * price[t]
                mg = RATIO.get(t)
                if mg is not None:
                    e["profit"] = a * mg * price[t]
            individual[eid][t] = e

    totals = {}
    for eid, mats in individual.items():
        totals[eid] = {"volume": sum(m.get("volume",0.0) for m in mats.values()),
                       "profit": sum(m.get("profit",0.0) for m in mats.values()),
                       "volumeRank": 0, "profitRank": 0}
    for i,(eid,_e) in enumerate(sorted(totals.items(), key=lambda kv:-kv[1]["volume"]),1):
        totals[eid]["volumeRank"] = i
    for i,(eid,_e) in enumerate(sorted(totals.items(), key=lambda kv:-kv[1]["profit"]),1):
        totals[eid]["profitRank"] = i

    # pad truncated base/ship boards (raylu's defaults) so totals-companies all appear
    for eid in totals:
        base.setdefault(eid, {"bases": 1})
        ship.setdefault(eid, {"ships": 2})

    # universe.bases estimate: captured board sum + tail model.
    # Tail anchored on apr26 (Samuel's own committed month): unseen companies ≈
    # producers − captured rows; avg unseen score 1.48 = (18674−15610)/(4344−2275).
    # (A constant board×ratio is wrong here: raylu's captures are deeper than
    # Samuel's, and the unseen tail shrinks with depth.)
    apr_board, apr_true, apr_rows, apr_producers = 15610, 18674, 2275, 4344
    tail_avg = (apr_true - apr_board) / (apr_producers - apr_rows)   # 1.4807
    n_prod = len({e for rows in ranks.values() for _r, _s, e in rows})
    n_bases_rows = len(data["BASES"])
    est_bases = round(sum(s for _r, s, _e in data["BASES"]) + max(0, n_prod - n_bases_rows) * tail_avg)
    universe = {"volume": sum(v.get("volume",0.0) for v in prod.values()),
                "profit": sum(v.get("profit",0.0) for v in prod.values()),
                "bases": est_bases,
                "companies": len(totals)}

    os.makedirs(OUT, exist_ok=True)
    for stem, obj in [("base-data",base), ("ship-data",ship), ("prod-data",prod),
                      ("company-data",{"totals":totals,"individual":dict(individual)}),
                      ("universe-data",universe)]:
        p = f"{OUT}/{stem}-{month}.json"
        json.dump(obj, open(p,"w"), separators=(",",":"))
        print(f"  wrote {p} ({os.path.getsize(p):,} B)")
    print(f"  {month}: universe volume={universe['volume']:,.0f} profit={universe['profit']:,.0f} "
          f"bases~{est_bases:,} companies={universe['companies']:,} materials={len(prod)}")

for m in ["may26","jun26","jul26"]:
    print(f"== {m} ==")
    build(m)
print("\nBackfill staged in", OUT)
