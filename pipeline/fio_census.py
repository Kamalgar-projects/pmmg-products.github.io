#!/usr/bin/env python3
"""Universe base census: GET /planet/sites/{Planet} for all planets, count company-owned sites.

Owner-counted bases = distinct OwnerIds among sites where OwnerId != PlanetId
(planet-owned rows = COGC/admin/shipyard gov infra, not bases).
Resumable: progress in /tmp/fio_census/progress.json, results appended to sites_dump.jsonl.
"""
import json, os, time, urllib.request, urllib.error, threading

OUT_DIR = "/tmp/fio_census"
SITES_OUT = os.path.join(OUT_DIR, "sites_dump.jsonl")
PROG = os.path.join(OUT_DIR, "progress.json")
PLANETS = os.path.join(OUT_DIR, "planets.json")
HDRS = {"User-Agent": "misspringle", "X-FIO-Application": "misspringle"}

os.makedirs(OUT_DIR, exist_ok=True)

def fetch(path, timeout=30):
    req = urllib.request.Request("https://rest.fnar.net" + path, headers=HDRS)
    return urllib.request.urlopen(req, timeout=timeout).read().decode()

# planets list (cache once)
if not os.path.exists(PLANETS):
    pl = json.loads(fetch("/planet/allplanets", timeout=120))
    ids = [p["PlanetNaturalId"] for p in pl]
    json.dump(ids, open(PLANETS, "w"))
    print("planet list cached:", len(ids))
else:
    ids = json.load(open(PLANETS))

done = set()
if os.path.exists(PROG):
    done = set(json.load(open(PROG)))
if not os.path.exists(SITES_OUT):
    open(SITES_OUT, "w").close()

lock = threading.Lock()
stats = {"ok": 0, "204": 0, "err": 0}

def record(pid, payload, status):
    with lock:
        if status == "ok":
            with open(SITES_OUT, "a") as f:
                f.write(json.dumps({"p": pid, "s": payload}) + "\n")
        done.add(pid)
        stats[status if status in stats else "err"] += 1
        if len(done) % 100 == 0:
            json.dump(sorted(done), open(PROG, "w"))

def worker(queue):
    while True:
        with lock:
            if not queue:
                return
            pid = queue.pop()   # atomic claim: each planet fetched exactly once
        for attempt in range(4):
            try:
                body = fetch(f"/planet/sites/{pid}")
                record(pid, json.loads(body) if body.strip() else [], "ok" if body.strip() else "204")
                break
            except urllib.error.HTTPError as e:
                if e.code == 204:
                    record(pid, [], "204"); break
                if e.code in (429, 500, 502, 503):
                    time.sleep(2 * (attempt + 1)); continue
                record(pid, [], "err"); break
            except Exception:
                time.sleep(2 * (attempt + 1))
        else:
            record(pid, [], "err")
        time.sleep(0.05)

queue = [x for x in ids if x not in done]
threads = [threading.Thread(target=worker, args=(queue,), daemon=True) for _ in range(6)]
for t in threads: t.start()
for t in threads: t.join()

json.dump(sorted(done), open(PROG, "w"))
print("census complete:", stats)
