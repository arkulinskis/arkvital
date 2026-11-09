"""Search-engine and AI-assistant files for arkvital.com. Re-run after adding a page, a book or a live app.

    python tools/seo.py

Writes robots.txt, sitemap.xml, llms.txt and apps.html (the "All apps" directory) at the site root, adds share tags
(Open Graph + Twitter card) to pages that don't have them yet, Person / Organization structured data on the home page,
and an "All apps" link in every footer and on Selected work. The app list comes from APP_MAKER/apps.json (live
address) and APP_MAKER/seo/apps/<key>.json (description, category).

Why: every app links back to arkvital.com and names "Arkvital" as its publisher. The directory links back to each app
and the structured data uses the same @id, so search engines can join the apps and the studio into one entity.
"""
import datetime
import html
import json
import pathlib
import re
import subprocess

SITE = "https://arkvital.com"
HERE = pathlib.Path(__file__).resolve().parent.parent
MAKER = HERE.parent / "APP_MAKER"
TODAY = datetime.date.today().isoformat()
LINKEDIN = "https://www.linkedin.com/in/vitalijsarkulinskis/"
GITHUB = "https://github.com/arkulinskis"
# Apps left out of the public directory: Addanapp is the parent company (linked on its own), Image Enhancer is a
# private API. Apps with "board": false in apps.json are left out too.
SKIP_APPS = {"addanapp", "imageenhancer"}
# Public address when it differs from apps.json (planplate.com runs the live PlanPlate business).
PUBLIC_URL = {"restres": "https://planplate.com"}
GROUPS = [
    ("Run a business", ["BusinessApplication", "FinanceApplication", "ShoppingApplication", "DeveloperApplication"]),
    ("Learn something", ["EducationalApplication", "ReferenceApplication"]),
    ("Make music, video and art", ["MultimediaApplication", "DesignApplication"]),
    ("Health and everyday life", ["HealthApplication", "LifestyleApplication", "SportsApplication", "SocialNetworkingApplication"]),
    ("Games and fun", ["GameApplication", "EntertainmentApplication"]),
    ("Handy tools", ["UtilitiesApplication", None]),
]
PAGES = ["index.html", "services.html", "projects.html", "apps.html", "blogs.html", "blog_1.html", "blog_2.html", "blog_3.html", "privacy.html"]
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


def changed(p):
    """Last commit date of a file, so lastmod only moves when the page really changes (today if uncommitted)."""
    try:
        dirty = subprocess.run(["git", "-C", str(HERE), "status", "--porcelain", "--", p], capture_output=True, text=True).stdout.strip()
        day = subprocess.run(["git", "-C", str(HERE), "log", "-1", "--format=%cs", "--", p], capture_output=True, text=True).stdout.strip()
    except OSError:
        return TODAY
    return TODAY if dirty or not day else day


LANGS = ["en", "fr", "es", "ru", "lv"]  # translated copies in /<lang>/ come from tools/i18n.py


def lang_url(lang, p):
    return url_of(p) if lang == "en" else SITE + "/%s/" % lang + ("" if p == "index.html" else p)


def sitemap():
    rows = []
    for p in PAGES:
        alts = "".join('<xhtml:link rel="alternate" hreflang="%s" href="%s"/>' % (l, lang_url(l, p)) for l in LANGS)
        alts += '<xhtml:link rel="alternate" hreflang="x-default" href="%s"/>' % url_of(p)
        pri = "1.0" if p == "index.html" else "0.8" if p == "apps.html" else "0.7"
        for l in LANGS:
            if l != "en" and not (HERE / l / p).exists():
                continue
            day = changed(p) if l == "en" else max(changed(p), changed(l + "/" + p))
            rows.append("<url><loc>%s</loc><lastmod>%s</lastmod><priority>%s</priority>%s</url>"
                        % (lang_url(l, p), day, pri if l == "en" else "%.1f" % (float(pri) - 0.1), alts))
    for pdf in sorted((HERE / "books").glob("*.pdf")):
        rows.append("<url><loc>%s/books/%s</loc><lastmod>%s</lastmod><priority>0.6</priority></url>" % (SITE, pdf.name, changed("books/" + pdf.name)))
        epub = pdf.with_suffix(".epub")
        if epub.exists():
            rows.append("<url><loc>%s/books/%s</loc><lastmod>%s</lastmod><priority>0.5</priority></url>" % (SITE, epub.name, changed("books/" + epub.name)))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            + "\n".join(rows) + "\n</urlset>\n")


def app_list():
    """Live public apps: dicts with key, name, url, host, tagline, description, category, free."""
    out = []
    try:
        reg = json.loads((MAKER / "apps.json").read_text(encoding="utf-8"))["apps"]
    except OSError:
        return out
    for key, a in sorted(reg.items(), key=lambda kv: kv[1]["name"].lower()):
        f = MAKER / "seo" / "apps" / (key + ".json")
        if not a.get("url") or not f.exists() or key in SKIP_APPS or a.get("board") is False:
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        url = PUBLIC_URL.get(key, a["url"]).rstrip("/") + "/"
        out.append({"key": key, "name": a["name"], "url": url, "host": url.split("//", 1)[1].rstrip("/"),
                    "tagline": d.get("tagline", ""), "description": d["description"],
                    "category": d.get("category"), "free": d.get("free") is True})
    return out


def apps():
    return ["- [%s](%s): %s" % (a["name"], a["url"], a["description"]) for a in app_list()]


def llms():
    idx = read("index.html")
    desc = meta(idx, r'<meta name="description" content="([^"]*)"')
    out = ["# Vitalijs Arkulinskis (Arkvital)", "", "> " + desc, "",
           "Arkvital is the Montreal studio of Vitalijs Arkulinskis. Its parent company is Addanapp (https://addanapp.com). Arkvital publishes the web apps below; each one has an /about page and an /llms.txt with more detail.", "",
           "The site is in English, with full translations in French (%s/fr/), Spanish (%s/es/), Russian (%s/ru/) and Latvian (%s/lv/)." % (SITE, SITE, SITE, SITE), "",
           "## Pages", ""]
    for p in PAGES:
        t = meta(read(p), r"<title>(.*?)</title>")
        out.append("- [%s](%s)" % (t, url_of(p)))
    books = sorted((HERE / "books").glob("*.pdf"))
    if books:
        out += ["", "## Free books", ""]
        for b in books:
            name = b.stem.replace("-", " ").title()
            out.append("- [%s](%s/books/%s)" % (name, SITE, b.name))
            if b.with_suffix(".epub").exists():
                out.append("- [%s (EPUB)](%s/books/%s)" % (name, SITE, b.with_suffix(".epub").name))
    a = apps()
    if a:
        out += ["", "## Apps by Arkvital", "", "The same list as a web page: %s/apps.html" % SITE, ""] + a
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


def ld_tag(ld):
    return '<script type="application/ld+json">%s</script>' % json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")


ORG = {"@type": "Organization", "@id": SITE + "/#org", "name": "Arkvital", "url": SITE + "/", "email": "arkvital@outlook.com",
       "logo": SITE + "/assets/img/logo-ark.svg", "founder": {"@id": SITE + "/#person"},
       "address": {"@type": "PostalAddress", "addressLocality": "Montreal", "addressRegion": "QC", "addressCountry": "CA"},
       "parentOrganization": {"@type": "Organization", "@id": "https://addanapp.com/#org", "name": "Addanapp",
                              "url": "https://addanapp.com/", "sameAs": ["https://www.youtube.com/@addanapp"]},
       "sameAs": [GITHUB]}


def person_ld(text):
    """Person + Organization + WebSite on the home page. Rewritten every run so it stays current."""
    desc = meta(text, r'<meta name="description" content="([^"]*)"')
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "Person", "@id": SITE + "/#person", "name": "Vitalijs Arkulinskis", "alternateName": ["Arkvital", "Виталий Аркулинский", "Vitālijs Arkulinskis"],
         "url": SITE + "/", "image": SITE + "/assets/img/og.jpg", "description": desc,
         "worksFor": {"@id": SITE + "/#org"}, "sameAs": [LINKEDIN, GITHUB],
         "jobTitle": "Project and people leader; mechanical and software engineer",
         "knowsAbout": ["Product management", "Leadership coaching", "Change management", "Internal tools",
                        "Data analytics", "Automation", "Software engineering"],
         "address": {"@type": "PostalAddress", "addressLocality": "Montreal", "addressRegion": "QC", "addressCountry": "CA"}},
        ORG,
        {"@type": "WebSite", "@id": SITE + "/#site", "url": SITE + "/", "name": "Arkvital", "inLanguage": LANGS,
         "publisher": {"@id": SITE + "/#org"}}]}
    text = re.sub(r'<script type="application/ld\+json">.*?</script>\n?', "", text, flags=re.S)
    return text.replace("</head>", ld_tag(ld) + "\n</head>", 1)


def slug(label):
    return re.sub(r"[^a-z]+", "-", label.lower()).strip("-")


def group_of(a):
    for label, cats in GROUPS:
        if a["category"] in cats:
            return label
    return GROUPS[-1][0]


HOME_START, HOME_END = "<!-- apps:start -->", "<!-- apps:end -->"
HOME_OLD = '  <section class="section"><div class="wrap"><div class="section-head"><p class="kicker">My work through Addanapp</p>'


def home_picks(text, apps):
    """Home page: three apps (random in the browser via site.js; a fixed three for crawlers and no-JS), Shuffle, See all."""
    e = lambda x: html.escape(x, quote=True)
    if HOME_START not in text:
        i = text.index(HOME_OLD)
        j = text.index("</section>", i) + len("</section>")
        text = text[:i] + "  " + HOME_START + HOME_END + text[j:]
    have = [a for a in apps if (HERE / "assets" / "img" / "apps" / (a["key"] + ".webp")).exists()]
    n = datetime.date.today().toordinal()
    first = [have[(n * 7 + k * 19) % len(have)] for k in range(3)] if len(have) >= 3 else have
    cards = "".join(
        '<a class="project app-pick" data-key="%s" href="%s" target="_blank" rel="noopener">'
        '<img src="assets/img/apps/%s.webp" alt="" width="720" height="450" loading="lazy">'
        '<div><span class="project-type">%s</span><h3>%s</h3><p>%s</p><span class="project-link">%s ↗</span></div></a>'
        % (e(a["key"]), e(a["url"]), e(a["key"]), e(group_of(a)), e(a["name"]), e(a["description"]), e(a["host"])) for a in first)
    data = json.dumps([{"key": a["key"], "name": a["name"], "url": a["url"], "host": a["host"], "description": a["description"],
                        "group": group_of(a)} for a in have], ensure_ascii=False).replace("</", "<\\/")
    block = ('<section class="section home-apps" aria-labelledby="home-apps-h"><div class="wrap"><div class="section-head">'
             '<p class="kicker">My work through Addanapp</p><h2 id="home-apps-h">From restaurant bookings to music theory games.</h2>'
             '<p class="lead">I’ve built %d live apps for businesses, learners, families and creators. Here are three, picked at random.</p></div>'
             '<div class="projects" data-app-picks>%s</div>'
             '<div class="section-end apps-actions"><button class="btn btn-ghost" type="button" data-app-shuffle hidden>Shuffle <span aria-hidden="true">↻</span></button>'
             '<a class="btn btn-primary" href="apps.html">See all %d apps <span aria-hidden="true">→</span></a>'
             '<a class="text-link" href="projects.html">Selected work <span aria-hidden="true">→</span></a>'
             '<span class="visually-hidden" id="app-picks-status" aria-live="polite"></span></div></div>'
             '<script type="application/json" id="app-picks-data">%s</script></section>' % (len(apps), cards, len(apps), data))
    i, j = text.index(HOME_START) + len(HOME_START), text.index(HOME_END)
    return text[:i] + block + text[j:]


def apps_page(apps):
    """apps.html: every live app grouped by kind, with links back and SoftwareApplication data tied to Arkvital."""
    e = lambda x: html.escape(x, quote=True)
    shell = read("projects.html")
    header = shell[shell.index("<body"):shell.index('<main id="main">')]
    header = header.replace('class="page-projects"', 'class="page-projects page-apps"')
    header = header.replace(' aria-current="page" href="projects.html"', ' href="projects.html"')
    footer = shell[shell.index("</main>") + len("</main>"):]
    head = shell[:shell.index("<body")]
    title = "All apps by Arkvital — Vitalijs Arkulinskis"
    desc = ("%d web apps made by Vitalijs Arkulinskis (Arkvital, Montreal): business tools, learning apps, "
            "music and video studios, games and everyday helpers." % len(apps))
    head = re.sub(r'<meta name="description" content="[^"]*">', lambda m: '<meta name="description" content="%s">' % e(desc), head)
    head = re.sub(r"<title>.*?</title>", lambda m: "<title>%s</title>" % e(title), head)
    head = re.sub(r'<link rel="canonical".*?<meta name="twitter:card"[^>]*>', "", head, flags=re.S)
    tags = ('<link rel="canonical" href="{s}/apps.html"><meta property="og:title" content="{t}"><meta property="og:description" content="{d}">'
            '<meta property="og:image" content="{s}/assets/img/og.jpg"><meta property="og:url" content="{s}/apps.html">'
            '<meta property="og:type" content="website"><meta property="og:site_name" content="Arkvital">'
            '<meta name="twitter:card" content="summary_large_image">').format(s=SITE, t=e(title), d=e(desc))
    head = head.replace('<link rel="icon"', tags + '<link rel="icon"', 1)
    head = re.sub(r'\s*<script type="application/ld\+json">.*?</script>', "", head, flags=re.S)

    by_group, seen = [], set()
    for label, cats in GROUPS:
        items = [a for a in apps if a["category"] in cats]
        seen.update(a["key"] for a in items)
        by_group.append((label, items))
    rest = [a for a in apps if a["key"] not in seen]
    if rest:
        by_group[-1] = (by_group[-1][0], by_group[-1][1] + rest)
    by_group = [(l, i) for l, i in by_group if i]

    parts = []
    for label, items in by_group:
        g = slug(label)
        cards = []
        for a in items:
            free = '<span class="app-free">Free</span>' if a["free"] else ""
            shot = ('<img class="app-shot" src="assets/img/apps/%s.webp" alt="" width="720" height="450" loading="lazy">' % e(a["key"])
                    if (HERE / "assets" / "img" / "apps" / (a["key"] + ".webp")).exists() else "")
            cards.append('<li class="app-card">%s<div class="app-body"><h3><a href="%s" target="_blank" rel="noopener">%s</a></h3><p>%s</p>'
                         '<span class="app-host">%s ↗</span>%s</div></li>' % (shot, e(a["url"]), e(a["name"]), e(a["description"]), e(a["host"]), free))
        parts.append('<section class="app-group" id="%s" aria-labelledby="%s-h"><h2 id="%s-h">%s <span>%d</span></h2><ul class="app-dir">%s</ul></section>'
                     % (g, g, g, e(label), len(items), "".join(cards)))
    jump = "".join('<a href="#%s">%s</a>' % (slug(l), e(l)) for l, i in by_group)

    main = ('<main id="main">\n'
            '  <section class="page-hero page-hero-projects photo-band"><figure class="band-media projects-hero-media" data-parallax="band" aria-hidden="true">'
            '<img src="assets/img/sofa.webp" alt="" fetchpriority="high"></figure><div class="wrap narrow"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="index.html">Home</a>'
            '<span aria-hidden="true">/</span><a href="projects.html">Selected work</a><span aria-hidden="true">/</span><span aria-current="page">All apps</span></nav>'
            '<p class="kicker">All apps · Arkvital</p><h1>Every app I’ve built and published.</h1>'
            '<p class="lead">%d live web apps, made by Arkvital in Montreal. They all run in the browser, with nothing to install. Open any of them to try it.</p>'
            '<nav class="app-jump" aria-label="App groups">%s</nav></div></section>\n'
            '  <section class="section section-tint apps-section"><div class="wrap">%s</div></section>\n'
            '  <section class="section"><div class="wrap split-callout"><div><p class="kicker">Want one of these for your team?</p><h2>Let’s talk about what you need.</h2></div>'
            '<div><p>Most of these started as one person’s problem. If you have a process that breaks down, or an idea you keep coming back to, tell me about it.</p>'
            '<a class="btn btn-primary" href="https://tidycal.com/arkvital" target="_blank" rel="noopener">Talk with me ↗</a></div></div></section>\n'
            '</main>' % (len(apps), jump, "\n".join(parts)))

    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "CollectionPage", "@id": SITE + "/apps.html#page", "url": SITE + "/apps.html", "name": title, "description": desc,
         "isPartOf": {"@id": SITE + "/#site"}, "about": {"@id": SITE + "/#org"}, "mainEntity": {"@id": SITE + "/apps.html#list"},
         "breadcrumb": {"@type": "BreadcrumbList", "itemListElement": [
             {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
             {"@type": "ListItem", "position": 2, "name": "Selected work", "item": SITE + "/projects.html"},
             {"@type": "ListItem", "position": 3, "name": "All apps", "item": SITE + "/apps.html"}]}},
        {"@type": "ItemList", "@id": SITE + "/apps.html#list", "name": "Apps by Arkvital", "numberOfItems": len(apps),
         "itemListElement": [{"@type": "ListItem", "position": i + 1, "item": {
             "@type": "SoftwareApplication", "@id": a["url"] + "#app", "name": a["name"], "url": a["url"], "description": a["description"],
             "applicationCategory": a["category"] or "UtilitiesApplication", "operatingSystem": "Web browser",
             "publisher": {"@id": SITE + "/#org"}, "author": {"@id": SITE + "/#person"}}} for i, a in enumerate(apps)]},
        ORG]}
    head = head.replace("</head>", ld_tag(ld) + "\n</head>", 1)
    import i18n  # same language menu and hreflang links the translation build adds
    return i18n.add_hreflang(i18n.add_switcher(head + header + main + footer, "en", "apps.html"), "apps.html")


FOOTER_FROM = '<a href="projects.html">Selected work</a><a href="blogs.html">'
FOOTER_TO = '<a href="projects.html">Selected work</a><a href="apps.html">All apps</a><a href="blogs.html">'
PROJECTS_FROM = '<a class="text-link" href="https://addanapp.com/#work" target="_blank" rel="noopener">See the full portfolio on Addanapp ↗</a>'
GRID_END = '  </div></div></section>\n  <section class="section"><div class="wrap split-callout">'


def links(page, text, n):
    """'All apps' in the footer of every page, and on Selected work under the intro and after the grid."""
    if FOOTER_TO not in text:
        text = text.replace(FOOTER_FROM, FOOTER_TO, 1)
    if page == "projects.html":
        text = re.sub(r'<p class="apps-more">.*?</p>', "", text)
        text = re.sub(r'<a class="text-link apps-link"[^>]*>.*?</a> ', "", text)
        text = text.replace(PROJECTS_FROM, '<a class="text-link apps-link" href="apps.html">See all %d apps →</a> ' % n + PROJECTS_FROM, 1)
        text = text.replace(GRID_END, '  </div><p class="apps-more"><a class="btn btn-ghost" href="apps.html">Browse all %d apps →</a></p></div></section>\n'
                                      '  <section class="section"><div class="wrap split-callout">' % n, 1)
    return text


def write(p, text):
    path = HERE / p
    old = path.read_text(encoding="utf-8") if path.exists() else None
    if old != text:
        path.write_text(text, encoding="utf-8", newline="\n")
        print("wrote", p)


if __name__ == "__main__":
    app_rows = app_list()
    write("apps.html", apps_page(app_rows))
    for p in PAGES + ["404.html"]:
        t = read(p)
        t2 = links(p, t, len(app_rows))
        if p in PAGES and p != "apps.html":
            t2 = share_tags(p, t2)
        if p == "index.html":
            t2 = person_ld(home_picks(t2, app_rows))
        if t2 != t:
            write(p, t2)
    write("robots.txt", robots())
    write("sitemap.xml", sitemap())
    write("llms.txt", llms())
    # translated copies (/fr/ /es/ /ru/ /lv/) are rebuilt from the English pages just written
    import i18n
    i18n.build()
