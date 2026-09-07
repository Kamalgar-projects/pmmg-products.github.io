#!/usr/bin/env python3
"""Analyze the FIO sites census: universe base count + sanity metrics.

Base definition: a site row whose OwnerId != PlanetId is a COMPANY site (base or gov
infra built by a company). Samuel's 'universe.bases' counts bases; game-wide bases =
distinct (OwnerId) sites of company owners. We report several cut points to compare
against the committed 18,674 (apr26) / 18,028 (mar26).
"""
import json, collections, sys

OUT = "/tmp/fio_census/sites_dump.jsonl"

owners = collections.Counter()      # OwnerId -> site count (company sites only)
owner_names = {}
planet_owned = 0                    # sites owned by the planet itself (COGC etc.)
total_rows = 0
planets_with_sites = 0

seen = {}
for line in open(OUT):
    rec = json.loads(line)
    seen[rec["p"]] = rec.get("s") or []   # dedupe: last record per planet wins
for pid, sites in seen.items():
    if sites:
        planets_with_sites += 1
    for s in sites:
        total_rows += 1
        oid = s.get("OwnerId")
        if oid and oid != s.get("PlanetId"):
            owners[oid] += 1
            if s.get("OwnerName"):
                owner_names[oid] = s["OwnerName"]
        else:
            planet_owned += 1

n_company_sites = sum(owners.values())
n_companies_with_sites = len(owners)
dist = collections.Counter(owners.values())
print(f"total site rows:        {total_rows:,}")
print(f"planet-owned (gov):     {planet_owned:,}")
print(f"company site rows:      {n_company_sites:,}")
print(f"companies with >=1 site:{n_companies_with_sites:,}")
print(f"planets with any sites: {planets_with_sites:,}")
print("\nsites-per-company distribution (top):", dist.most_common(10))
print("\nbiggest landowners:", [(owner_names.get(o, o)[:20], c) for o, c in owners.most_common(8)])

# KC sanity check
kc = [o for o, n in owner_names.items() if n and "Kamalcorp" in n]
print("\nKamalcorp sanity:", [(owner_names[o], owners[o]) for o in kc])
