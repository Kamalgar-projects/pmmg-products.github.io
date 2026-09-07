#!/usr/bin/env python3
"""Condense the raw /tmp census dump into a permanent archive: per-planet company site counts."""
import json, collections

seen = {}
for line in open("/tmp/fio_census/sites_dump.jsonl"):
    rec = json.loads(line)
    seen[rec["p"]] = rec.get("s") or []

archive = {}
owners = collections.Counter()
names = {}
for pid, sites in seen.items():
    comp = [s for s in sites if s.get("OwnerId") and s["OwnerId"] != s.get("PlanetId")]
    archive[pid] = {"total": len(sites), "company": len(comp)}
    for s in comp:
        owners[s["OwnerId"]] += 1
        if s.get("OwnerName"):
            names[s["OwnerId"]] = s["OwnerName"]

import os
OUT = "/home/rnadeau/pmmg/revival/pipeline/cache/universe_census_20260906.json"
json.dump({
    "captured": "2026-09-06",
    "planets": len(archive),
    "company_sites_total": sum(owners.values()),
    "companies_with_sites": len(owners),
    "note": "company site = OwnerId != PlanetId (company base, 1/planet/company). "
            "Committed universe.bases apr26=18674; live census 18848 (+0.9% organic growth). "
            "Kamalcorp=24 (matches doctrine). Source of future universe.bases.",
    "per_planet": archive,
    "per_owner_sites": {names.get(o, o): c for o, c in owners.most_common()},
}, open(OUT, "w"))
print("archived:", OUT)
print("planets:", len(archive), "| company sites:", sum(owners.values()), "| companies:", len(owners))
