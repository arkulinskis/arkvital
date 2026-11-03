"""Build the free EPUB editions of the books.

    python tools/books/epub.py            # both books
    python tools/books/epub.py hope       # only books whose slug contains "hope"

Uses the same manuscripts and Markdown handling as build.py (the PDF builder),
so the EPUB and the PDF always have the same text. Run build.py first if the
cover changed: the EPUB reuses <manuscript folder>/<slug>-cover.png.
Output: books/<slug>.epub (EPUB 3, with an EPUB 2 table of contents for older readers).
"""
import html
import io
import re
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from xml.dom import minidom

from PIL import Image

import build
from build import ABOUT, AUTHOR, BOOKS, SITE

YEAR = 2026

CSS = """
body { margin: 0 4%; font-family: Georgia, "Times New Roman", serif; line-height: 1.5; color: #211d1a; }
a { color: __ACCENT__; text-decoration: none; }
p { margin: 0; text-indent: 1.3em; text-align: justify; }
h1 + p, h2 + p, h3 + p, h4 + p, p.opener, p.first, blockquote + p, table + p, ul + p, ol + p, hr + p,
.front p, td p, li p, blockquote p { text-indent: 0; }
p.opener { margin-top: 0; }
p.opener::first-letter { font-size: 2.6em; line-height: 0.9; float: left; margin: 0.05em 0.08em 0 0; color: __ACCENT__; font-weight: bold; }

.part-page { text-align: center; margin-top: 30%; }
.part-label { text-transform: uppercase; letter-spacing: 0.3em; font-size: 0.8em; color: __ACCENT__; margin: 0 0 1em; text-indent: 0; text-align: center; }
h1.part-title { font-size: 1.8em; font-weight: normal; line-height: 1.2; margin: 0; }

h2.chapter { margin: 2em 0 1.4em; font-weight: normal; text-align: left; page-break-after: avoid; }
.ch-label { display: block; text-transform: uppercase; letter-spacing: 0.25em; font-size: 0.55em; color: __ACCENT__; margin-bottom: 0.5em; }
.ch-title { display: block; font-size: 1.15em; line-height: 1.2; }
h3.section { font-size: 1.15em; margin: 1.6em 0 0.5em; page-break-after: avoid; }
h4.sub { font-size: 0.8em; text-transform: uppercase; letter-spacing: 0.12em; margin: 1.3em 0 0.4em; color: #4a433d; page-break-after: avoid; }

blockquote { margin: 1em 1.2em; padding-left: 0.8em; border-left: 3px solid __ACCENT__; font-style: italic; }
blockquote p { margin: 0 0 0.4em; }
ul, ol { margin: 0.6em 0 0.6em 1.4em; padding: 0; }
li { margin: 0 0 0.3em; }
hr { border: 0; text-align: center; margin: 1.4em 0; height: 1em; }
hr::after { content: "\\2022  \\2022  \\2022"; color: __ACCENT__; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; font-size: 0.85em; line-height: 1.35; }
th, td { border-bottom: 1px solid #c9bfb4; padding: 0.35em 0.4em; text-align: left; vertical-align: top; }
th { border-bottom: 2px solid __ACCENT__; }

.front h1, .front-h { font-weight: normal; }
.front-h { font-size: 1.5em; margin: 1em 0 1em; }
.front p { margin: 0 0 0.8em; text-align: left; }
.title-page { text-align: center; margin-top: 20%; }
.title-page h1 { font-size: 2.2em; color: __ACCENT__; margin: 0 0 0.6em; line-height: 1.1; }
.title-page p { text-align: center; }
.tp-sub { font-style: italic; }
.tp-author { text-transform: uppercase; letter-spacing: 0.35em; margin-top: 3em !important; font-weight: bold; }
.copyright p { font-size: 0.8em; }
.epigraph { margin-top: 25%; }
.epigraph .q { font-style: italic; }
.epigraph .by { font-size: 0.85em; color: #6f665e; margin-bottom: 2em; }
.also-title { font-size: 1.4em; color: __ACCENT__; margin-bottom: 0.2em !important; }

nav#toc ol { list-style: none; margin: 0; padding: 0; }
nav#toc li { margin: 0.3em 0; }
nav#toc li.part { margin-top: 1em; font-weight: bold; }
nav#toc ol ol { margin-left: 1.2em; }
nav#toc li.part li { font-weight: normal; }
nav#landmarks { display: none; }

.cover { margin: 0; padding: 0; text-align: center; }
.cover img { max-width: 100%; max-height: 100%; }
"""

VOID = re.compile(r"<(br|hr|img|col|input|wbr)(\s[^<>]*?)?\s*/?>")


def xhtml(body):
    """markdown-it gives HTML; EPUB needs XHTML (self-closed void tags)."""
    body = VOID.sub(lambda m: f"<{m.group(1)}{m.group(2) or ''} />", body)
    return body.replace("&nbsp;", "&#160;")


def page(title, body, css=True, body_class="", epub_type=""):
    link = '<link rel="stylesheet" type="text/css" href="style.css" />' if css else ""
    cls = f' class="{body_class}"' if body_class else ""
    et = f' epub:type="{epub_type}"' if epub_type else ""
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en" xml:lang="en">
<head><meta charset="utf-8" /><title>{html.escape(title)}</title>{link}</head>
<body{cls}{et}>
{xhtml(body)}
</body>
</html>
"""


def split_body(body):
    """Split the rendered body into one chunk per part page and per chapter."""
    body = re.sub(r'<span class="mk">QQ[^<]*QQ</span>', "", body)
    starts = [m.start() for m in re.finditer(r'<section class="part-page"|<h2 class="chapter"', body)]
    if not starts or starts[0] != 0:
        starts = [0] + starts
    chunks = []
    for a, b in zip(starts, starts[1:] + [len(body)]):
        chunk = body[a:b].strip()
        m = re.search(r'id="((?:pt|ch)-\d+)"', chunk[:300])
        chunks.append((m.group(1) if m else f"pre-{len(chunks)}", chunk))
    return chunks


def plain(s):
    md = build.MarkdownIt("commonmark", {"typographer": True}).enable(["replacements", "smartquotes"])
    return html.unescape(re.sub("<[^>]+>", "", md.renderInline(s)))


def front_pages(b, epigraph):
    md = build.MarkdownIt("commonmark", {"typographer": True}).enable(["replacements", "smartquotes"])
    pages = [("title", "Title Page", f"""<section class="front title-page" epub:type="titlepage">
<h1>{b['title']}</h1>
<p class="tp-sub">{b['subtitle']}</p>
<p class="tp-author">Arkvital</p>
<p>arkvital.com</p>
</section>"""),
             ("copyright", "Copyright", f"""<section class="front copyright" epub:type="copyright-page">
<p><b>{b['title']}</b><br /><i>{b['subtitle']}</i></p>
<p>Copyright © {YEAR} {AUTHOR}. All rights reserved.</p>
<p>No part of this book may be reproduced or sold in any form without written permission from the author, except for brief quotations in reviews and articles.</p>
<p>The people in this book are imagined composites. Any resemblance to real persons is coincidental. The research described is real and is listed at the back.</p>
<p>This book offers general information and personal perspective. It is not medical, psychological, legal or financial advice. If you are struggling, please talk to a qualified professional or, in an emergency, call your local emergency number. In Canada and the US you can call or text 988.</p>
<p>Free EPUB edition, version 1.0, November {YEAR}.<br />Cover design by Arkvital.</p>
<p>Published by Arkvital · <a href="https://arkvital.com">arkvital.com</a></p>
</section>""")]
    if epigraph:
        quotes = []
        for block in re.split(r"\n\s*\n", epigraph):
            lines = [l.lstrip("> ").strip() for l in block.strip().split("\n") if l.strip()]
            quotes.append(f'<blockquote><p class="q">{md.renderInline(lines[0])}</p>'
                          f'<p class="by">{md.renderInline(" ".join(lines[1:]))}</p></blockquote>')
        pages.append(("epigraph", "Epigraph", f'<section class="front epigraph" epub:type="epigraph">{"".join(quotes)}</section>'))
    return pages


def back_pages(b, other):
    return [("about", "About the Author",
             f'<section class="front about"><h2 class="front-h">About the Author</h2>{ABOUT}</section>'),
            ("also", "Also by Arkvital", f"""<section class="front also">
<h2 class="front-h">Also by Arkvital</h2>
<p class="also-title">{other['title']}</p>
<p><i>{other['subtitle']}</i></p>
{''.join(f'<p>{p}</p>' for p in other['blurb'][:2])}
<p>Free to download at <a href="https://arkvital.com/blogs.html#books">arkvital.com</a>.</p>
</section>""")]


def nav_tree(toc, files):
    """Parts hold their chapters; chapters before the first part sit at the top."""
    tree = []
    for kind, hid, label, title in toc:
        name = plain(title)
        if label and not label.isdigit() and kind == "chapter":
            name = f"{label}: {name}"
        elif label and label.isdigit():
            name = f"{label}. {name}"
        elif kind == "part":
            name = f"{label}: {name}"
        item = dict(href=files[hid], name=name, kids=[])
        if kind == "part":
            tree.append(item)
        elif tree and tree[-1].get("part") and not re.match(r"(Epilogue|Appendix|Notes|Sources|Field Guide|A Last|Afterword)", name):
            tree[-1]["kids"].append(item)
        else:
            tree.append(item)
        if kind == "part":
            item["part"] = True
    return tree


def nav_xhtml(b, tree, cover_file):
    def ol(items):
        rows = []
        for it in items:
            cls = ' class="part"' if it.get("part") else ""
            sub = ol(it["kids"]) if it["kids"] else ""
            rows.append(f'<li{cls}><a href="{it["href"]}">{html.escape(it["name"])}</a>{sub}</li>')
        return f"<ol>{''.join(rows)}</ol>"
    first = tree[0]["href"] if tree else "title.xhtml"
    body = f"""<nav epub:type="toc" id="toc"><h2 class="front-h">Contents</h2>{ol(tree)}</nav>
<nav epub:type="landmarks" id="landmarks" hidden="hidden"><ol>
<li><a epub:type="cover" href="{cover_file}">Cover</a></li>
<li><a epub:type="toc" href="nav.xhtml">Contents</a></li>
<li><a epub:type="bodymatter" href="{first}">Start reading</a></li>
</ol></nav>"""
    return page(f"{b['title']} — Contents", body, body_class="front")


def ncx(b, uid, tree):
    n = [0]

    def points(items):
        out = []
        for it in items:
            n[0] += 1
            out.append(f'<navPoint id="np{n[0]}" playOrder="{n[0]}"><navLabel><text>{html.escape(it["name"])}</text></navLabel>'
                       f'<content src="{it["href"]}" />{points(it["kids"])}</navPoint>')
        return "".join(out)
    pts = points(tree)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
<head><meta name="dtb:uid" content="{uid}" /><meta name="dtb:depth" content="2" />
<meta name="dtb:totalPageCount" content="0" /><meta name="dtb:maxPageNumber" content="0" /></head>
<docTitle><text>{html.escape(b['title'])}</text></docTitle>
<navMap>{pts}</navMap>
</ncx>
"""


def opf(b, uid, items, spine):
    modified = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    desc = html.escape(" ".join(re.sub("<[^>]+>", "", p) for p in b["blurb"]))
    subjects = "".join(f"<dc:subject>{html.escape(k.strip())}</dc:subject>" for k in b["keywords"].split(",") if k.strip() != "Arkvital")
    manifest = "\n".join(f'<item id="{i}" href="{h}" media-type="{t}"{f" properties={chr(34)}{p}{chr(34)}" if p else ""} />'
                         for i, h, t, p in items)
    sp = "\n".join(f'<itemref idref="{i}"{"" if lin else " linear=" + chr(34) + "no" + chr(34)} />' for i, lin in spine)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid" xml:lang="en">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="bookid">{uid}</dc:identifier>
<dc:title id="t1">{html.escape(b['title'])}</dc:title>
<meta refines="#t1" property="title-type">main</meta>
<dc:title id="t2">{html.escape(b['subtitle'])}</dc:title>
<meta refines="#t2" property="title-type">subtitle</meta>
<dc:creator id="au">Arkvital</dc:creator>
<meta refines="#au" property="role" scheme="marc:relators">aut</meta>
<meta refines="#au" property="file-as">Arkulinskis, Vitalijs</meta>
<dc:language>en</dc:language>
<dc:publisher>Arkvital</dc:publisher>
<dc:rights>Copyright © {YEAR} {AUTHOR}. All rights reserved.</dc:rights>
<dc:date>{YEAR}-10</dc:date>
<dc:description>{desc}</dc:description>
{subjects}
<meta property="dcterms:modified">{modified}</meta>
<meta name="cover" content="cover-image" />
</metadata>
<manifest>
{manifest}
</manifest>
<spine toc="ncx">
{sp}
</spine>
</package>
"""


CONTAINER = """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml" /></rootfiles>
</container>
"""


def cover_jpeg(b):
    png = b["src"].parent / f"{b['slug']}-cover.png"
    img = Image.open(png).convert("RGB")
    if img.width > 1600:
        img = img.resize((1600, round(img.height * 1600 / img.width)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88, optimize=True, progressive=True)
    return buf.getvalue(), img.size


def make_epub(b, other):
    print(f"== {b['title']}")
    md_text, epigraph = build.load_source(b)
    body, toc, n_ch = build.render_body(b, md_text)
    uid = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, 'https://arkvital.com/books/' + b['slug'])}"
    docs = {}            # filename -> xhtml
    items = []           # (id, href, media-type, properties)
    spine = []           # (id, linear)

    def add(fid, name, content, linear=True, props=""):
        docs[name] = content
        items.append((fid, name, "application/xhtml+xml", props))
        spine.append((fid, linear))

    jpg, (w, h) = cover_jpeg(b)
    add("cover", "cover.xhtml", page(b["title"], f'<div class="cover"><img src="cover.jpg" alt="Cover of {html.escape(b["title"])} by Arkvital" /></div>',
                                     body_class="cover", epub_type="cover"), props="")
    for key, title, content in front_pages(b, epigraph):
        add(key, f"{key}.xhtml", page(title, content))
    nav_at = len(spine)          # Contents comes after the front matter

    files = {}
    chapters = []
    for n, (hid, chunk) in enumerate(split_body(body), start=1):
        name = f"text{n:02d}.xhtml"
        files[hid] = name
        m = re.search(r'<span class="ch-title">(.*?)</span>|<h1 class="part-title">(.*?)</h1>', chunk)
        title = html.unescape(re.sub("<[^>]+>", "", (m.group(1) or m.group(2)) if m else b["title"]))
        kind = "part" if chunk.startswith("<section") else "chapter"
        chapters.append((f"t{n:02d}", name, page(title, chunk, epub_type="bodymatter" if n == 1 else "")))
    for key, title, content in back_pages(b, other):
        chapters.append((key, f"{key}.xhtml", page(title, content)))

    tree = nav_tree(toc, files)
    docs["nav.xhtml"] = nav_xhtml(b, tree, "cover.xhtml")
    items.append(("nav", "nav.xhtml", "application/xhtml+xml", "nav"))
    spine.insert(nav_at, ("nav", True))
    for fid, name, content in chapters:
        add(fid, name, content)

    items += [("css", "style.css", "text/css", ""),
              ("cover-image", "cover.jpg", "image/jpeg", "cover-image"),
              ("ncx", "toc.ncx", "application/x-dtbncx+xml", "")]

    out = SITE / "books" / f"{b['slug']}.epub"
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w") as z:
        # mimetype must be first and stored uncompressed
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", CONTAINER, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/content.opf", opf(b, uid, items, spine), compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/toc.ncx", ncx(b, uid, tree), compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/style.css", CSS.replace("__ACCENT__", b["accent"]), compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/cover.jpg", jpg, compress_type=zipfile.ZIP_STORED)
        for name, content in docs.items():
            z.writestr(f"OEBPS/{name}", content, compress_type=zipfile.ZIP_DEFLATED)
    check(out)
    words = len(re.sub("<[^>]+>", " ", body).split())
    print(f"   {n_ch} chapters, ~{words:,} words, {out.stat().st_size / 1e6:.1f} MB -> {out.relative_to(SITE)}")
    return out


def check(path):
    """Basic structural checks (epubcheck needs Java, which isn't installed)."""
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        first = z.infolist()[0]
        assert first.filename == "mimetype" and first.compress_type == zipfile.ZIP_STORED, "mimetype must be first, uncompressed"
        for n in names:
            if n.endswith((".xhtml", ".opf", ".ncx", ".xml")):
                try:
                    minidom.parseString(z.read(n))
                except Exception as e:
                    raise SystemExit(f"   ! {n} is not well-formed XML: {e}")
        opf_doc = minidom.parseString(z.read("OEBPS/content.opf"))
        hrefs = {i.getAttribute("href") for i in opf_doc.getElementsByTagName("item")}
        missing = [h for h in hrefs if f"OEBPS/{h}" not in names]
        assert not missing, f"manifest lists missing files: {missing}"
        for n in names:
            if n.endswith(".xhtml"):
                for link in re.findall(r'(?:href|src)="([^"#]+)', z.read(n).decode("utf-8")):
                    if ":" in link:
                        continue          # web or mailto link
                    assert link in hrefs, f"{n} links to {link}, which is not in the book"


if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv) > 1 else ""
    for i, b in enumerate(BOOKS):
        if only in b["slug"]:
            make_epub(b, BOOKS[1 - i])
