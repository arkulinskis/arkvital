"""Build the free PDF editions of the books and their cover images.

    python tools/books/build.py            # both books
    python tools/books/build.py hope       # only books whose slug contains "hope"

Reads the manuscripts from ../adds-up-to-180 and ../addicted-to-hope (next to
this repo), typesets them as HTML and prints them to PDF with headless Chrome.
Outputs:
    books/<slug>.pdf                      the download
    assets/img/books/<slug>-cover.webp    cover for the website
    <manuscript folder>/<slug>-cover.png  full-size cover (2.5x)
"""
import html
import re
import shutil
import subprocess
import sys
from pathlib import Path

from markdown_it import MarkdownIt
from PIL import Image
from pypdf import PdfReader, PdfWriter

import covers

HERE = Path(__file__).resolve().parent
SITE = HERE.parents[1]
WORK = HERE.parents[2]
BUILD = HERE / "build"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

AUTHOR = "Vitalijs Arkulinskis"

BOOKS = [
    dict(
        slug="adds-up-to-180",
        src=WORK / "adds-up-to-180" / "Adds-Up-To-180.md",
        title="Adds Up to 180",
        subtitle="Achievement, Appreciation, Hope — and the Big Loud AAH That Holds Them Together",
        author_cover="ARKVITAL",
        accent="#b9512d",
        tagline="Every triangle adds up to 180.<br>So does a life that works.",
        blurb=[
            "Achievement, Appreciation and Hope are the three angles of a good life. Push one too far and it squeezes the other two. Drop one and the whole shape goes flat.",
            "In a library meeting room with folding chairs and a coffee urn that tastes like pennies, five ordinary people learn to draw the triangle: serve the people you like, even before they like you back; say thank you every day, to yourself included; and keep the stubborn belief that you can keep going.",
            "Funny, practical and backed by research that was checked, <i>Adds Up to 180</i> ends with a ten-minute daily routine and one big, loud exhale. AAH.",
        ],
        keywords="self-help, gratitude, hope, achievement, anxiety, Arkvital",
        first_marker="## A Note Before You Start",
    ),
    dict(
        slug="addicted-to-hope",
        src=WORK / "addicted-to-hope" / "Addicted-To-Hope.md",
        title="Addicted to Hope",
        subtitle="Why Dreaming Feels Better Than Doing, and How to Ship Your Life Anyway",
        author_cover="ARKVITAL",
        accent="#23406b",
        tagline="The dream pays out before you've done a thing. That's the problem.",
        blurb=[
            "You have a folder of ideas. Each one looks beautiful in your head, and that's exactly why it never leaves the folder: dreaming gives you the reward up front, and doing only gives you the bugs.",
            "<i>Addicted to Hope</i> is an engineer's guide to breaking the habit. It explains why planning feels like progress, how your upbringing set your default, and which hard truths break the spell. Then it hands you the tools: prototypes, if-then plans, feedback loops, rope teams and kill criteria.",
            "Every chapter ends with a field test you do within 24 hours. Climb along with five people from a Tuesday-night garage workshop as they stop dreaming about the summit and start moving.",
        ],
        keywords="self-help, motivation, procrastination, habits, engineering, Arkvital",
        first_marker="## Before You Start",
    ),
]

ABOUT = """<p><b>Arkvital</b> is Vitalijs Arkulinskis, a mechanical and software engineer turned project and people leader. Over more than twelve years, across more than ten industries, he has coached managers, built tools for teams, and learned to look for the real cause of a problem before choosing the fix.</p>
<p>He writes about people, progress and the quiet work beneath good work at <a href="https://arkvital.com">arkvital.com</a>, and builds small, useful apps through Addanapp.</p>
<p>If something in this book landed for you, or missed, he'd like to hear about it. You can book a short call at <a href="https://tidycal.com/arkvital">tidycal.com/arkvital</a>.</p>"""


# ---------------------------------------------------------------- markdown --

def load_source(b):
    text = b["src"].read_text(encoding="utf-8").replace("\r\n", "\n")
    epigraph = ""
    if b["slug"] == "adds-up-to-180":
        # The title block and Euclid epigraph move to their own pages,
        # and the hand-written Contents is replaced by one with page numbers.
        parts = text.split("\n---\n")
        epigraph = parts[1].strip()
        text = text[text.index(b["first_marker"]):]
        text = re.sub(r"## Contents\n.*?(?=\n## Before We Start)", "", text, flags=re.S)
    else:
        text = text[text.index(b["first_marker"]):]
    # Drop horizontal rules next to headings; page breaks do that job now.
    lines = text.split("\n")
    keep = []
    for i, line in enumerate(lines):
        if line.strip() == "---":
            nxt = next((l for l in lines[i + 1:] if l.strip()), "")
            prv = next((l for l in reversed(keep) if l.strip()), "")
            if nxt.startswith("#") or prv.startswith("#") or not nxt or not prv:
                continue
        keep.append(line)
    return "\n".join(keep), epigraph


def classify(b, level, txt):
    """Return part / chapter / section / sub for a heading."""
    if b["slug"] == "adds-up-to-180":
        if level == 1:
            return "part"
        if level == 2:
            return "chapter"
        return "section" if level == 3 else "sub"
    if level == 2:
        return "part" if txt.startswith("Part ") else "chapter"
    if level == 3:
        return "chapter" if re.match(r"\d+\. ", txt) else "section"
    return "section" if level == 4 else "sub"


def split_label(txt):
    m = re.match(r"Chapter (\d+) — (.+)", txt) or re.match(r"(\d+)\. (.+)", txt)
    if m:
        return f"Chapter {m.group(1)}", m.group(2), m.group(1)
    m = re.match(r"(Part [A-Za-z]+|Part [IVX]+): (.+)", txt)
    if m:
        return m.group(1), m.group(2), None
    m = re.match(r"(Epilogue|Appendix(?: [A-Z])?|Before We Start) ?[—:] (.+)", txt)
    if m:
        return m.group(1), m.group(2), None
    return "", txt, None


def render_body(b, md_text):
    md = MarkdownIt("commonmark", {"html": False, "typographer": True, "breaks": True}).enable(["table", "replacements", "smartquotes"])
    tokens = md.parse(md_text)
    out, buf, toc = [], [], []
    n_part = n_ch = 0
    first_para_next = False
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t.type == "heading_open":
            if buf:
                out.append(md.renderer.render(buf, md.options, {}))
                buf = []
            raw = tokens[i + 1].content
            level = int(t.tag[1])
            kind = classify(b, level, raw)
            if kind == "part":
                n_part += 1
                label, title, _ = split_label(raw)
                hid = f"pt-{n_part}"
                out.append(f'<section class="part-page" id="{hid}"><p class="part-label">{label}</p>'
                           f'<h1 class="part-title">{md.renderInline(title)}<span class="mk">QQ{hid}QQ</span></h1></section>')
                toc.append(("part", hid, label, title))
            elif kind == "chapter":
                n_ch += 1
                label, title, num = split_label(raw)
                hid = f"ch-{n_ch}"
                lab = f'<span class="ch-label">{label}</span>' if label else ""
                out.append(f'<h2 class="chapter" id="{hid}">{lab}<span class="ch-title">{md.renderInline(title)}</span>'
                           f'<span class="mk">QQ{hid}QQ</span></h2>')
                toc.append(("chapter", hid, num or label, title))
                first_para_next = True
            else:
                tag = "h3" if kind == "section" else "h4"
                out.append(f'<{tag} class="{kind}">{md.renderInline(raw)}</{tag}>')
            i += 3
            continue
        if first_para_next and t.type == "paragraph_open" and t.level == 0:
            t.attrSet("class", "opener")
            first_para_next = False
        elif first_para_next and t.type not in ("paragraph_open",) and t.level == 0 and t.nesting == 1:
            first_para_next = False
        buf.append(t)
        i += 1
    if buf:
        out.append(md.renderer.render(buf, md.options, {}))
    return "\n".join(out), toc, n_ch


# -------------------------------------------------------------------- html --

def font_css():
    f = (HERE / "fonts").as_uri()
    return f"""
@font-face{{font-family:Literata;src:url("{f}/Literata.ttf");font-weight:200 900;font-style:normal}}
@font-face{{font-family:Literata;src:url("{f}/Literata-Italic.ttf");font-weight:200 900;font-style:italic}}
@font-face{{font-family:Fraunces;src:url("{f}/Fraunces.ttf");font-weight:100 900;font-style:normal}}
@font-face{{font-family:Fraunces;src:url("{f}/Fraunces-Italic.ttf");font-weight:100 900;font-style:italic}}
@font-face{{font-family:Inter;src:url("{f}/Inter.ttf");font-weight:100 900;font-style:normal}}
"""


def book_css(b):
    css = (HERE / "book.css").read_text(encoding="utf-8")
    return font_css() + covers.COVER_CSS + css.replace("__TITLE__", b["title"]).replace("__ACCENT__", b["accent"])


def toc_html(toc, pages):
    rows = []
    for kind, hid, label, title in toc:
        pg = pages.get(hid, "000")
        if kind == "part":
            rows.append(f'<li class="toc-part"><a href="#{hid}"><span class="t">{label}: {html.escape(title)}</span>'
                        f'<span class="pg">{pg}</span></a></li>')
        else:
            num = f'<span class="n">{label}</span>' if label and label.isdigit() else ""
            name = html.escape(title) if (not label or label.isdigit()) else f"{label}: {html.escape(title)}"
            rows.append(f'<li class="toc-ch"><a href="#{hid}">{num}<span class="t">{name}</span>'
                        f'<span class="dots"></span><span class="pg">{pg}</span></a></li>')
    return f'<section class="front toc-page"><h2 class="front-h">Contents</h2><ol class="toc">{"".join(rows)}</ol></section>'


def book_html(b, other, body, toc, pages, epigraph, with_markers):
    md = MarkdownIt("commonmark", {"typographer": True}).enable(["replacements", "smartquotes"])
    epi = ""
    if epigraph:
        # each quote block: first line is the quote, the rest is who said it
        quotes = []
        for block in re.split(r"\n\s*\n", epigraph):
            lines = [l.lstrip("> ").strip() for l in block.strip().split("\n") if l.strip()]
            quotes.append(f'<blockquote><p class="q">{md.renderInline(lines[0])}</p>'
                          f'<p class="by">{md.renderInline(" ".join(lines[1:]))}</p></blockquote>')
        epi = f'<section class="front epigraph">{"".join(quotes)}</section>'
    year = 2026
    front = f"""
{covers.FRONTS[b['slug']](b)}
<section class="front half-title"><p>{b['title']}</p></section>
<section class="front title-page">
  <h1>{b['title']}</h1>
  <p class="tp-sub">{b['subtitle']}</p>
  <p class="tp-author">Arkvital</p>
  <p class="tp-imprint">arkvital.com</p>
</section>
<section class="front copyright">
  <p><b>{b['title']}</b><br><i>{b['subtitle']}</i></p>
  <p>Copyright © {year} {AUTHOR}. All rights reserved.</p>
  <p>No part of this book may be reproduced or sold in any form without written permission from the author, except for brief quotations in reviews and articles.</p>
  <p>The people in this book are imagined composites. Any resemblance to real persons is coincidental. The research described is real and is listed at the back.</p>
  <p>This book offers general information and personal perspective. It is not medical, psychological, legal or financial advice. If you are struggling, please talk to a qualified professional or, in an emergency, call your local emergency number. In Canada and the US you can call or text 988.</p>
  <p>Free PDF edition, version 1.0, October {year}.<br>Cover design and typesetting by Arkvital.<br>Set in Literata, Fraunces and Inter.</p>
  <p>Published by Arkvital · <a href="https://arkvital.com">arkvital.com</a></p>
</section>
{epi}
{toc_html(toc, pages)}
"""
    back = f"""
<section class="front about"><h2 class="front-h">About the Author</h2>{ABOUT}</section>
<section class="front also">
  <h2 class="front-h">Also by Arkvital</h2>
  <p class="also-title">{other['title']}</p>
  <p class="also-sub"><i>{other['subtitle']}</i></p>
  {''.join(f'<p>{p}</p>' for p in other['blurb'][:2])}
  <p>Free to download at <a href="https://arkvital.com/blogs.html#books">arkvital.com</a>.</p>
</section>
{covers.back_cover(b, other)}
"""
    mk = "" if with_markers else ".mk{display:none}"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{b['title']} — Arkvital</title>
<style>{book_css(b)}{mk}</style></head>
<body class="book-{b['slug']}">{front}<main class="body">{body}</main>{back}</body></html>"""


# ------------------------------------------------------------------ chrome --

def chrome(*args):
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
                    "--allow-file-access-from-files", *args], check=True, capture_output=True, timeout=600)


def print_pdf(html_path, pdf_path):
    if pdf_path.exists():
        pdf_path.unlink()
    chrome("--no-pdf-header-footer", "--generate-pdf-document-outline", "--virtual-time-budget=20000",
           f"--print-to-pdf={pdf_path}", html_path.as_uri())
    return pdf_path


def find_pages(pdf_path):
    pages = {}
    for n, page in enumerate(PdfReader(str(pdf_path)).pages, start=1):
        txt = re.sub(r"\s+", "", page.extract_text() or "")
        for hid in re.findall(r"QQ((?:pt|ch)-\d+)QQ", txt):
            pages.setdefault(hid, str(n))
    return pages


def render_cover_png(b, out_png):
    page = BUILD / f"{b['slug']}-cover.html"
    page.write_text(f"""<!doctype html><html><head><meta charset="utf-8"><style>{font_css()}{covers.COVER_CSS}
html,body{{margin:0;background:#000}}</style></head><body>{covers.FRONTS[b['slug']](b)}</body></html>""", encoding="utf-8")
    chrome("--hide-scrollbars", "--force-device-scale-factor=2.5", "--window-size=576,864",
           "--virtual-time-budget=5000", f"--screenshot={out_png}", page.as_uri())


# -------------------------------------------------------------------- main --

def build(b, other):
    print(f"== {b['title']}")
    md_text, epigraph = load_source(b)
    body, toc, n_ch = render_body(b, md_text)

    tmp = BUILD / f"{b['slug']}.html"
    tmp.write_text(book_html(b, other, body, toc, {}, epigraph, True), encoding="utf-8")
    pass1 = print_pdf(tmp, BUILD / f"{b['slug']}-pass1.pdf")
    pages = find_pages(pass1)
    missing = [hid for _, hid, *_ in toc if hid not in pages]
    if missing:
        print("   ! no page found for", missing)

    tmp.write_text(book_html(b, other, body, toc, pages, epigraph, False), encoding="utf-8")
    raw = print_pdf(tmp, BUILD / f"{b['slug']}-raw.pdf")
    # filling in the page numbers must not change the page count
    assert len(PdfReader(str(raw)).pages) == len(PdfReader(str(pass1)).pages)

    out = SITE / "books" / f"{b['slug']}.pdf"
    out.parent.mkdir(exist_ok=True)
    w = PdfWriter(clone_from=str(raw))
    w.add_metadata({"/Title": f"{b['title']}: {b['subtitle']}", "/Author": f"Arkvital ({AUTHOR})",
                    "/Subject": re.sub("<[^>]+>", "", b["blurb"][0]), "/Keywords": b["keywords"],
                    "/Creator": "Arkvital", "/Producer": "Arkvital"})
    w.page_mode = "/UseOutlines"
    w.compress_identical_objects()
    with open(out, "wb") as fh:
        w.write(fh)
    n_pages = len(PdfReader(str(out)).pages)

    png = b["src"].parent / f"{b['slug']}-cover.png"
    render_cover_png(b, png)
    img = Image.open(png).convert("RGB")
    webdir = SITE / "assets" / "img" / "books"
    webdir.mkdir(parents=True, exist_ok=True)
    img.resize((600, 900), Image.LANCZOS).save(webdir / f"{b['slug']}-cover.webp", quality=88, method=6)
    print(f"   {n_pages} pages, {n_ch} chapters, {out.stat().st_size / 1e6:.1f} MB -> {out.relative_to(SITE)}")
    return n_pages


if __name__ == "__main__":
    BUILD.mkdir(exist_ok=True)
    only = sys.argv[1] if len(sys.argv) > 1 else ""
    for i, b in enumerate(BOOKS):
        if only in b["slug"]:
            build(b, BOOKS[1 - i])
