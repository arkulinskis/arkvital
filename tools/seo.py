"""Search-engine and AI-assistant files for arkvital.com. Re-run after adding a page, a book or a live app.

    python tools/seo.py

Writes robots.txt, sitemap.xml and llms.txt at the site root, and adds share tags (Open Graph + Twitter card) to
pages that don't have them yet, plus Person / Organization structured data on the home page. The app list in
llms.txt comes from APP_MAKER/apps.json (live address) and APP_MAKER/seo/apps/<key>.json (description).
"""
import datetime
import html
import json
import pathlib
import re

SITE = "https://arkvital.com"
HERE = pathlib.Path(__file__).resolve().parent.parent
MAKER = HERE.parent / "APP_MAKER"
TODAY = datetime.date.today().isoformat()
PAGES = ["index.html", "services.html", "projects.html", "blogs.html", "blog_1.html", "blog_2.html", "blog_3.html", "privacy.html"]
AI_BOTS = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "Claude-User", "PerplexityBot",
           "Perplexity-User", "Google-Extended", "Applebot-Extended", "Amazonbot", "meta-externalagent", "DuckAssistBot",
           "MistralAI-User", "CCBot"]


def read(p):
    return (HERE / p).read_text(encoding="utf-8")


def meta(text, pat):
    m = re.search(pat, text, re.S | re.I)
    return html.unescape(m.group(1).strip()) if m else ""


def url_of(page):
    return SITE + "/" if page == "index.html" else SITE + "/" + page


def robots():
    lines = ["# robots.txt for arkvital.com. Search engines and AI assistants are welcome to read and cite this site.",
             "User-agent: *", "Allow: /", "", "# AI search and answer engines, named so it's clear they are welcome too"]
    lines += ["User-agent: %s" % b for b in AI_BOTS] + ["Allow: /", "", "Sitemap: %s/sitemap.xml" % SITE, ""]
    return "\n".join(lines)


def sitemap():
    rows = []
    for p in PAGES:
        rows.append("<url><loc>%s</loc><lastmod>%s</lastmod><priority>%s</priority></url>"
                    % (url_of(p), TODAY, "1.0" if p == "index.html" else "0.7"))
    for pdf in sorted((HERE / "books").glob("*.pdf")):
        rows.append("<url><loc>%s/books/%s</loc><lastmod>%s</lastmod><priority>0.6</priority></url>" % (SITE, pdf.name, TODAY))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(rows) + "\n</urlset>\n")


def apps():
    out = []
    try:
        reg = json.loads((MAKER / "apps.json").read_text(encoding="utf-8"))["apps"]
    except OSError:
        return out
    for key, a in sorted(reg.items(), key=lambda kv: kv[1]["name"].lower()):
        f = MAKER / "seo" / "apps" / (key + ".json")
        if not a.get("url") or not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        out.append("- [%s](%s/): %s" % (a["name"], a["url"].rstrip("/"), d["description"]))
    return out


def llms():
    idx = read("index.html")
    desc = meta(idx, r'<meta name="description" content="([^"]*)"')
    out = ["# Vitalijs Arkulinskis (Arkvital)", "", "> " + desc, "",
           "Arkvital is the Montreal studio of Vitalijs Arkulinskis. It publishes the web apps below; each one has an /about page and an /llms.txt with more detail.", "",
           "## Pages", ""]
    for p in PAGES:
        t = meta(read(p), r"<title>(.*?)</title>")
        out.append("- [%s](%s)" % (t, url_of(p)))
    books = sorted((HERE / "books").glob("*.pdf"))
    if books:
        out += ["", "## Free books", ""] + ["- [%s](%s/books/%s)" % (b.stem.replace("-", " ").title(), SITE, b.name) for b in books]
    a = apps()
    if a:
        out += ["", "## Apps by Arkvital", ""] + a
    out += ["", "Contact: arkvital@outlook.com", ""]
    return "\n".join(out)


def share_tags(page, text):
    if 'property="og:image"' in text:
        return text
    title = meta(text, r"<title>(.*?)</title>")
    desc = meta(text, r'<meta name="description" content="([^"]*)"')
    e = lambda s: html.escape(s, quote=True)
    tags = ('<meta property="og:title" content="%s"><meta property="og:description" content="%s">'
            '<meta property="og:image" content="%s/assets/img/og.jpg"><meta property="og:url" content="%s">'
            '<meta property="og:type" content="%s"><meta property="og:site_name" content="Arkvital">'
            '<meta name="twitter:card" content="summary_large_image">'
            % (e(title), e(desc), SITE, url_of(page), "article" if page.startswith("blog_") else "website"))
    return re.sub(r'(<link rel="canonical" href="[^"]*">)', lambda m: m.group(1) + tags, text, count=1)


def person_ld(text):
    if "application/ld+json" in text:
        return text
    desc = meta(text, r'<meta name="description" content="([^"]*)"')
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "Person", "@id": SITE + "/#person", "name": "Vitalijs Arkulinskis", "url": SITE + "/",
         "image": SITE + "/assets/img/og.jpg", "description": desc, "worksFor": {"@id": SITE + "/#org"},
         "address": {"@type": "PostalAddress", "addressLocality": "Montreal", "addressRegion": "QC", "addressCountry": "CA"}},
        {"@type": "Organization", "@id": SITE + "/#org", "name": "Arkvital", "url": SITE, "email": "arkvital@outlook.com",
         "founder": {"@id": SITE + "/#person"}},
        {"@type": "WebSite", "@id": SITE + "/#site", "url": SITE + "/", "name": "Arkvital", "publisher": {"@id": SITE + "/#person"}}]}
    tag = '<script type="application/ld+json">%s</script>' % json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")
    return text.replace("</head>", tag + "\n</head>", 1)


def write(p, text):
    path = HERE / p
    old = path.read_text(encoding="utf-8") if path.exists() else None
    if old != text:
        path.write_text(text, encoding="utf-8", newline="\n")
        print("wrote", p)


if __name__ == "__main__":
    write("robots.txt", robots())
    write("sitemap.xml", sitemap())
    write("llms.txt", llms())
    for p in PAGES:
        t = read(p)
        t2 = share_tags(p, t)
        if p == "index.html":
            t2 = person_ld(t2)
        if t2 != t:
            write(p, t2)
