"""Remove em dashes (—) and en dashes (–) from the book manuscripts, in every language.

    python tools/books/dashes.py count                 dashes left per book and language
    python tools/books/dashes.py extract [size]        write work batches (default 140 lines each) to ../_dashes/
    python tools/books/dashes.py check <name>          validate <name>.out.json without touching the files
    python tools/books/dashes.py apply                 put every finished batch (<name>.out.json) back into the files
    python tools/books/dashes.py join                  rebuild ../adds-up-to-180/Adds-Up-To-180.md from its edited chunks

A batch is <name>.json: [{"id": "...", "file": "...", "line": n, "before": "...", "after": "...", "text": "..."}],
"text" being the line to rewrite and before/after the neighbouring lines for context. An editor (a person or an
agent) writes <name>.out.json: {"<id>": "<rewritten line>", ...}. apply checks each rewrite (one line, no dash, same
heading level, the line still matches what was extracted) and refuses the batch otherwise.
Files: English 180 = ../books-en-chunks/180-*.md (joined back into the master by `join`; English Hope has no dashes),
translations = ../books-<lang>/chunks/<book>-<n>.<lang>.md.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE.parents[2]
OUT = WORK / "_dashes"
DASH = re.compile("[—–]")
URL = re.compile(r"https?://\S+|`[^`]*`")


def files():
    out = {("en", "180"): sorted((WORK / "books-en-chunks").glob("180-*.md"))}
    for lang in ("ru", "fr", "lv"):
        for book in ("180", "hope"):
            out[(lang, book)] = sorted((WORK / f"books-{lang}" / "chunks").glob(f"{book}-*.{lang}.md"))
    return out


def lines_of(p):
    return p.read_bytes().decode("utf-8").split("\n")


def has_dash(line):
    return bool(DASH.search(URL.sub("", line)))


def count():
    total = 0
    for (lang, book), fs in files().items():
        n = sum(len(DASH.findall(URL.sub("", l))) for f in fs for l in lines_of(f))
        total += n
        print(f"{lang}/{book:5} {n}")
    print("total", total)
    return total


def extract(size=140):
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.json"):
        if not old.name.endswith(".out.json"):
            old.unlink()
    for (lang, book), fs in files().items():
        items = []
        for f in fs:
            ls = lines_of(f)
            for i, l in enumerate(ls):
                if has_dash(l):
                    prev = next((x for x in reversed(ls[:i]) if x.strip()), "")
                    nxt = next((x for x in ls[i + 1:] if x.strip()), "")
                    items.append(dict(id=f"{f.stem}:{i + 1}", file=str(f.relative_to(WORK)).replace("\\", "/"),
                                      line=i + 1, before=prev[:400], after=nxt[:400], text=l))
        for k in range(0, len(items), size):
            name = f"{lang}-{book}-{k // size + 1:02d}"
            (OUT / f"{name}.json").write_bytes(json.dumps(items[k:k + size], ensure_ascii=False, indent=1).encode())
            print(name, len(items[k:k + size]), "lines")


def heading_level(s):
    m = re.match(r"(#{1,6}) ", s)
    return len(m.group(1)) if m else 0


def apply(only=None, dry=False):
    done = 0
    for out in sorted(OUT.glob(f"{only or '*'}.out.json")):
        batch = json.loads((OUT / out.name.replace(".out.json", ".json")).read_text(encoding="utf-8"))
        new = json.loads(out.read_text(encoding="utf-8"))
        errors, edits = [], {}
        for it in batch:
            v = new.get(it["id"])
            if v is None:
                errors.append(f"{it['id']}: missing")
                continue
            if "\n" in v or has_dash(v):
                errors.append(f"{it['id']}: {'newline' if chr(10) in v else 'still has a dash'}: {v[:90]}")
            elif heading_level(v) != heading_level(it["text"]):
                errors.append(f"{it['id']}: heading level changed")
            edits.setdefault(it["file"], []).append((it["line"], it["text"], v))
        if errors:
            print(f"{out.name}: NOT OK, {len(errors)} problems:", *errors[:12], sep="\n   ")
            continue
        if dry:
            print(f"{out.name}: OK, {len(batch)} lines ready (nothing written)")
            continue
        for rel, es in edits.items():
            p = WORK / rel
            ls = lines_of(p)
            for line, old, v in es:
                if ls[line - 1] == old:
                    ls[line - 1] = v
                elif ls[line - 1] != v:
                    raise SystemExit(f"{rel}:{line} changed since extract")
            p.write_bytes("\n".join(ls).encode("utf-8"))
        done += 1
        out.rename(out.with_suffix(".applied"))
        print(f"{out.name}: applied {len(batch)} lines")
    print(done, "batches applied")


def join():
    parts = [p.read_bytes().decode("utf-8") for p in sorted((WORK / "books-en-chunks").glob("180-*.md"))]
    (WORK / "adds-up-to-180" / "Adds-Up-To-180.md").write_bytes("\n".join(parts).encode("utf-8"))
    print("wrote adds-up-to-180/Adds-Up-To-180.md")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "count"
    if cmd == "extract":
        extract(int(sys.argv[2]) if len(sys.argv) > 2 else 140)
    elif cmd == "check":
        apply(sys.argv[2], dry=True)
    else:
        {"count": count, "apply": apply, "join": join}[cmd]()
