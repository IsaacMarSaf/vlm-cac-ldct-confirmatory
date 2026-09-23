"""
Verify that the frozen files in this repository are byte-identical to those of the protocol-freeze commit
807863319893e7df4dc043170ee13723bcb767f5 of the investigators' private repository, without access to that repository.

How it works (standard git object hashing, SHA-1):
  1. provenance/objects/<commit>.commit is the raw commit object. Its SHA-1, computed as sha1(b"commit <len>\\0" + bytes),
     must equal the full commit id cited in the article (807863319893e7df4dc043170ee13723bcb767f5). The object names the
     root tree, the parent commit, and the author and committer time stamps (self-recorded by the investigators' system).
  2. provenance/objects/<tree>.tree are the raw tree objects of the root and of the confirmatory/, data/ and scripts/
     directories. Each must hash to the id listed by its parent (the commit, or the root tree).
  3. Each frozen file present in this repository must hash, as sha1(b"blob <len>\\0" + bytes), to the blob id recorded for
     its path in those trees.
The trees list other files of the private repository by name and hash only; their contents are not published.
The check shows content, not time: the commit time stamps are self-recorded, and this deposit was made public after the reads.
It also checks the SHA-256 of the sorted participant list recorded in the frozen protocol against the public list.
Files not redistributed here (data/Results_NLST.csv; data/confirm_100_pids.csv, which carries its reference values) are
checked too if you place them in data/ (see data/README.md and tools/rehydrate_frozen_sample.py).

Usage: python provenance/verify_freeze.py      (run from the repository root; exit code 0 = all checks passed)
"""
import hashlib
import os
import re
import sys

COMMIT = "807863319893e7df4dc043170ee13723bcb767f5"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OBJ = os.path.join(HERE, "objects")
FROZEN = [  # (path in the frozen commit, path in this repository)
    ("confirmatory/PROTOCOL.md", "confirmatory/PROTOCOL.md"),
    ("confirmatory/DEVIATIONS.md", "provenance/frozen_files/confirmatory/DEVIATIONS.md"),
    ("scripts/02_find_baseline_series.py", "scripts/02_find_baseline_series.py"),
    ("scripts/52_confirm_sample.py", "scripts/52_confirm_sample.py"),
    ("scripts/53_confirm_download.py", "scripts/53_confirm_download.py"),
    ("scripts/54_confirm_render.py", "scripts/54_confirm_render.py"),
    ("scripts/55_confirm_analysis.py", "scripts/55_confirm_analysis.py"),
]
OPTIONAL = [("data/confirm_100_pids.csv", "data/confirm_100_pids.csv"), ("data/Results_NLST.csv", "data/Results_NLST.csv")]
ok = True


def sha1_obj(kind, data): return hashlib.sha1(kind.encode() + b" %d\0" % len(data) + data).hexdigest()


def check(cond, msg):
    global ok
    print(("  OK    " if cond else "  FAIL  ") + msg); ok &= bool(cond)


def read_obj(oid, kind):
    p = os.path.join(OBJ, f"{oid}.{kind}")
    data = open(p, "rb").read()
    check(sha1_obj(kind, data) == oid, f"{kind} object {oid} hashes to its id")
    return data


def parse_tree(data):
    out, i = {}, 0
    while i < len(data):
        sp = data.index(b" ", i); nul = data.index(b"\0", sp)
        mode, name = data[i:sp].decode(), data[sp + 1:nul].decode("utf-8")
        out[name] = (mode, data[nul + 1:nul + 21].hex()); i = nul + 21
    return out


print(f"Commit {COMMIT}")
commit = read_obj(COMMIT, "commit")
text = commit.decode("utf-8")
root_id = re.search(r"^tree ([0-9a-f]{40})$", text, re.M).group(1)
for line in text.splitlines():
    if line.startswith(("tree ", "parent ", "committer ")): print("        " + re.sub(r"<[^>]*>", "<email>", line))
print("        message: " + text.split("\n\n", 1)[1].strip().splitlines()[0])

root = parse_tree(read_obj(root_id, "tree"))
sub = {}
for d in ("confirmatory", "data", "scripts"):
    mode, oid = root[d]; check(mode == "40000", f"root tree lists directory {d}/ as tree {oid}")
    sub[d] = parse_tree(read_obj(oid, "tree"))


def blob_of(path):
    d, name = path.split("/", 1); return sub[d][name][1]


print("Frozen files published in this repository")
for fpath, rpath in FROZEN:
    data = open(os.path.join(ROOT, *rpath.split("/")), "rb").read()
    got, want = sha1_obj("blob", data), blob_of(fpath)
    hint = " (file has CRLF line endings: re-clone with the repository's .gitattributes, or check out without autocrlf)" \
        if got != want and b"\r\n" in data else ""
    check(got == want, f"{rpath}  blob {got} == frozen {want}{hint}")

print("Participant list recorded in the frozen protocol")
proto = open(os.path.join(ROOT, "confirmatory", "PROTOCOL.md"), encoding="utf-8").read()
want = re.search(r"SHA-256 of the sorted PID list `([0-9a-f]{64})`", proto).group(1)
pids = [line.split(",")[0] for line in open(os.path.join(ROOT, "data", "confirm_100_pids.public.csv"), encoding="utf-8").read().splitlines()[1:]]
got = hashlib.sha256(",".join(sorted(pids)).encode()).hexdigest()
check(len(pids) == 100 and got == want, f"data/confirm_100_pids.public.csv: SHA-256 of the sorted PIDs (comma-joined) {got[:12]}... "
      f"== protocol section 3 value {want[:12]}...")

print("Files not redistributed (checked only if present)")
for fpath, rpath in OPTIONAL:
    p = os.path.join(ROOT, *rpath.split("/"))
    if not os.path.exists(p):
        print(f"  --    {rpath}: not present (frozen blob {blob_of(fpath)})"); continue
    data = open(p, "rb").read().replace(b"\r\n", b"\n")
    check(sha1_obj("blob", data) == blob_of(fpath), f"{rpath}  matches frozen blob {blob_of(fpath)} (LF-normalized)")

print("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
sys.exit(0 if ok else 1)
