#!/usr/bin/env python3
"""Batch validation across all 14 months: base/ship pure transforms + price/margin extraction."""
import json, urllib.request, os

BASE = "https://raw.githubusercontent.com/Kamalgar-projects/pmmg-products.github.io/main/reports/data/"
months = ["mar25","apr25","may25","jun25","jul25","aug25","sep25","oct25","nov25","dec25","jan26","feb26","mar26","apr26"]
month_files = {"mar25":"March-2025","apr25":"April-2025","may25":"May-2025","jun25":"June-2025",
               "jul25":"July-2025","aug25":"August-2025","sep25":"September-2025","oct25":"October-2025",
               "nov25":"November-2025","dec25":"December-2025","jan26":"January-2026","feb26":"February-2026",
               "mar26":"March-2026","apr26":"April-2026"}

def fetch(path):
    return urllib.request.urlopen(urllib.request.Request(BASE+path, headers={"User-Agent":"misspringle"}), timeout=90).read().decode()

os.makedirs("/tmp/val", exist_ok=True)
for m in months:
    p = f"/tmp/val/{m}"
    try:
        raw = open(p+".csv").read()
        base_c = json.load(open(p+"_base.json"))
        try:
            ship_c = json.load(open(p+"_ship.json"))
        except FileNotFoundError:
            ship_c = None
        prod_c = json.load(open(p+"_prod.json"))
    except FileNotFoundError:
        raw = fetch(f"rawData/PrUN-LEAD-Data-{month_files[m]}.csv")
        open(p+".csv","w").write(raw)
        base_c = json.loads(fetch(f"base-data-{m}.json")); open(p+"_base.json","w").write(json.dumps(base_c))
        try:
            ship_c = json.loads(fetch(f"ship-data-{m}.json")); open(p+"_ship.json","w").write(json.dumps(ship_c))
        except Exception:
            ship_c = None  # ship-data not published for this month
        prod_c = json.loads(fetch(f"prod-data-{m}.json")); open(p+"_prod.json","w").write(json.dumps(prod_c))
    ship_ok = True
    if ship_c is None:
        ship_ok = None  # not published for this month

    rows = [l.split(",") for l in raw.splitlines() if l]
    my_base = {eid: {"bases": int(v), "rank": int(r)} for c,r,v,eid in rows if c=="BASES"}
    my_ship = {eid: {"ships": int(v), "rank": int(r)} for c,r,v,eid in rows if c=="SHIPS"}

    base_ok = all(base_c.get(k)==v for k,v in my_base.items()) and len(base_c)==len(my_base)
    ship_ok = (all(ship_c.get(k)==v for k,v in my_ship.items()) and len(ship_c)==len(my_ship)) if ship_c is not None else None

    price = {t: round(v["volume"]/v["amount"], 6) for t,v in prod_c.items() if v.get("amount")}
    margin = {t: round(v["profit"]/v["amount"], 6) for t,v in prod_c.items() if v.get("amount")}
    json.dump(price, open(f"/tmp/val/prices_{m}.json","w"))
    json.dump(margin, open(f"/tmp/val/margins_{m}.json","w"))

    ship_len = len(ship_c) if ship_c is not None else 0
    ship_str = "OK" if ship_ok is True else ("SKIP" if ship_ok is None else "MISMATCH")
    print(f"{m}: base={'OK' if base_ok else 'MISMATCH'} ({len(base_c):4}) ship={ship_str} ({ship_len:3}) prod_mats={len(prod_c):3} prices={len(price):3} margins={len(margin):3}")

print("\nDone.")
