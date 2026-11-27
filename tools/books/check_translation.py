"""python tools/books/check_translation.py <lang>
Check each ../books-<lang>/chunks/*.<lang>.md against its English chunk: heading levels/numbers,
paragraph counts per section, length ratio, leftover English lines."""
import re, sys
from pathlib import Path
WORK = Path(__file__).resolve().parents[3]
LANG = sys.argv[1] if len(sys.argv) > 1 else "ru"
EN = WORK / "books-en-chunks"
R = WORK / f"books-{LANG}" / "chunks"

def sections(text):
    out, cur = [], ["(start)", []]
    for block in re.split(r"\n\s*\n", text):
        b = block.strip()
        if not b: continue
        if re.match(r"#{1,4} ", b.split("\n")[0]):
            out.append(cur); cur = [b.split("\n")[0], []]
        else: cur[1].append(b)
    out.append(cur); return out

ok = True
for en in sorted(EN.glob("*.md")):
    ru = R / f"{en.stem}.{LANG}.md"
    if not ru.exists(): print(f"{en.name}: MISSING"); ok = False; continue
    e, r = en.read_text(encoding="utf-8"), ru.read_text(encoding="utf-8")
    se, sr = sections(e), sections(r)
    probs = []
    if len(se) != len(sr): probs.append(f"section count {len(se)} vs {len(sr)}")
    for (he, pe), (hr, pr) in zip(se, sr):
        le, lr = he.split(" ")[0], hr.split(" ")[0]
        ne = re.findall(r"\d+", he[:20]); nr = re.findall(r"\d+", hr[:20])
        if le != lr or (ne and nr and ne[0] != nr[0] and ne[0] not in hr): probs.append(f"heading mismatch: {he[:50]!r} / {hr[:50]!r}")
        ce, cr = sum(len(x) for x in pe), sum(len(x) for x in pr)
        if abs(len(pe) - len(pr)) > 1 or (ce > 400 and not 0.7 < cr / max(ce,1) < 1.6):
            probs.append(f"{hr[:45]!r}: paras {len(pe)}->{len(pr)}, chars {ce}->{cr}")
    eng = [l for l in r.split("\n") if len(re.findall(r"\b(?:the|and|you|that|with|this|your|what|was|for|are|have)\b", l, re.I)) > 4 and not re.search(r"\(\d{4}\)|doi|http|\d{4}\.", l)]
    if eng: probs.append(f"{len(eng)} mostly-English lines, e.g. {eng[0][:80]!r}")
    if "\r" in r: probs.append("CR line endings")
    print(f"{ru.name}: {'OK' if not probs else ''} chars {len(e)}->{len(r)}")
    for p in probs: print("   -", p); ok = False
sys.exit(0 if ok else 1)
