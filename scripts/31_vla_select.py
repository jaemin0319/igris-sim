#!/usr/bin/env python3
"""tar -tvf 목록에서 추출 패턴에 해당하는 항목의 실제 크기를 합산해 selection.json으로 기록(추출 전 공간 판단용)."""
import fnmatch, json, sys
root, pats = sys.argv[1], sys.argv[2:]
def parse(path):
    for line in open(path, errors="replace"):
        f = line.rstrip("\n").split(None, 5)
        if len(f) == 6 and f[2].isdigit(): yield int(f[2]), f[5].split(" -> ")[0], f[0][0]
tot = n = sel = seln = 0; per = {p: [0, 0] for p in pats}; big = []
for size, name, typ in parse(f"{root}/snapshot.filelist"):
    tot += size; n += 1
    for p in pats:
        if fnmatch.fnmatch(name, p): per[p][0] += size; per[p][1] += 1; sel += size; seln += 1; big.append((size, name)); break
import os
supp = sum(s for s, _, _ in parse(f"{root}/supplement.filelist")) if os.path.exists(f"{root}/supplement.filelist") else 0
out = {"archive_entries": n, "archive_plain_bytes": tot, "selected_entries": seln, "selected_bytes": sel, "supplement_bytes": supp, "per_pattern": {p: {"bytes": b, "entries": c} for p, (b, c) in per.items()},
       "largest_selected": [{"bytes": b, "name": nm} for b, nm in sorted(big, reverse=True)[:12]]}
json.dump(out, open(f"{root}/selection.json", "w"), indent=1)
print(f"archive: {n} entries, {tot/2**30:.1f} GiB plain | selected: {seln} entries, {sel/2**30:.2f} GiB | supplement: {supp/2**30:.2f} GiB")
for p, (b, c) in per.items(): print(f"  {b/2**20:9.1f} MiB {c:6d}  {p}")
