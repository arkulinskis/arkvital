"""Translated copies of arkvital.com: /fr/, /ru/, /lv/, /es/. Run after tools/seo.py (which builds the English pages).

    python tools/i18n.py extract      list every English text that needs translating -> tools/i18n/strings.json
                                      (and "missing" counts per language)
    python tools/i18n.py build        write <lang>/<page>.html for every page, with hreflang links on every version

Translations live in tools/i18n/<lang>.json: {"English text": "translation"}. Texts are the page's text nodes and the
alt / aria-label / title / meta description / share-tag texts, whitespace collapsed. A text with no translation stays
in English (the build lists how many). English stays at the root (arkvital.com/page.html); the books, CV and images are
shared (links point back to the root copies).
"""
import html
import json
import pathlib
import re
import sys
from html.parser import HTMLParser

HERE = pathlib.Path(__file__).resolve().parent.parent
DIR = HERE / "tools" / "i18n"
SITE = "https://arkvital.com"
LANGS = {"en": ("English", "EN", "en_CA"), "fr": ("Français", "FR", "fr_CA"), "es": ("Español", "ES", "es_ES"),
         "ru": ("Русский", "RU", "ru_RU"), "lv": ("Latviešu", "LV", "lv_LV")}
PAGES = ["index.html", "services.html", "projects.html", "apps.html", "blogs.html", "blog_1.html", "blog_2.html",
         "blog_3.html", "privacy.html", "404.html"]
ATTRS = ("alt", "aria-label", "title", "placeholder")
META_NAMES = ("description", "og:title", "og:description", "twitter:title", "twitter:description")
SKIP_TAGS = ("script", "style")
LETTER = re.compile(r"[A-Za-z]")


def norm(s):
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


class Texts(HTMLParser):
    """Collects translatable texts in document order."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip = [], 0

    def add(self, s):
        s = norm(s)
        if s and LETTER.search(s):
            self.out.append(s)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in SKIP_TAGS:
            self.skip += 1
        for k in ATTRS:
            if a.get(k):
                self.add(a[k])
        if tag == "meta" and (a.get("name") in META_NAMES or a.get("property") in META_NAMES) and a.get("content"):
            self.add(a["content"])
        if tag in ("span", "h1") and a.get("data-topics"):
            for t in a["data-topics"].split("|"):
                self.add(t)

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.add(data)

    def handle_entityref(self, name):
        pass

    def handle_charref(self, name):
        pass


def no_switcher(text):
    return re.sub(r'<li class="lang-menu">.*?</details></li>', "", text, flags=re.S)


def no_french_section(text):
    """privacy.html carries its own French section; translated pages translate the English part instead."""
    text = re.sub(r'\s*<a href="#fr" lang="fr">.*?</a>', "", text, flags=re.S)
    return re.sub(r'<h2 id="fr" lang="fr">.*?</div>\s*(?=</div></article>)', "", text, flags=re.S)


def texts_of(text):
    """Texts in a page, including the app picks JSON on the home page."""
    text = no_french_section(no_switcher(text))
    # entity refs are parsed as separate events above; unescape first so texts stay whole
    p = Texts()
    p.feed(re.sub(r"&(?!lt;|gt;)([a-z]+|#\d+|#x[0-9a-f]+);", lambda m: html.unescape(m.group(0)), text, flags=re.I))
    out = p.out
    m = re.search(r'<script type="application/json" id="app-picks-data">(.*?)</script>', text, re.S)
    if m:
        for a in json.loads(m.group(1).replace("<\\/", "</")):
            out += [a["description"], a["group"]]
    return out


def load(lang):
    f = DIR / (lang + ".json")
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def extract():
    seen, order = {}, []
    for p in PAGES:
        for s in texts_of((HERE / p).read_text(encoding="utf-8")):
            if s not in seen:
                seen[s] = p
                order.append(s)
    DIR.mkdir(exist_ok=True)
    (DIR / "strings.json").write_text(json.dumps([{"text": s, "page": seen[s]} for s in order], ensure_ascii=False, indent=0),
                                      encoding="utf-8", newline="\n")
    words = sum(len(s.split()) for s in order)
    print("%d texts, %d words" % (len(order), words))
    for lang in LANGS:
        if lang != "en":
            have = load(lang)
            miss = [s for s in order if s not in have and not keep(s)
                    and not (re.search(r"\d+", s) and re.sub(r"\d+", "{n}", s, count=1) in have)]
            print("  %s: %d missing (%d words)" % (lang, len(miss), sum(len(s.split()) for s in miss)))
    return order


# ------------------------------------------------------------------------------------------------- build
def url_of(lang, page):
    base = SITE + "/" if lang == "en" else "%s/%s/" % (SITE, lang)
    return base if page == "index.html" else base + page


def hreflang_tags(page):
    tags = ['<link rel="alternate" hreflang="%s" href="%s">' % (l, url_of(l, page)) for l in LANGS]
    tags.append('<link rel="alternate" hreflang="x-default" href="%s">' % url_of("en", page))
    return "".join(tags)


def switcher(lang, page):
    """Language menu for the header: a <details> list, works without JavaScript."""
    items = []
    for l, (name, short, _) in LANGS.items():
        href = ("" if lang == "en" else "../") + ("" if l == "en" else l + "/") + page
        cur = ' aria-current="true"' if l == lang else ""
        items.append('<li><a href="%s" hreflang="%s" lang="%s"%s>%s</a></li>' % (href, l, l, cur, name))
    label = {"en": "Language", "fr": "Langue", "es": "Idioma", "ru": "Язык", "lv": "Valoda"}[lang]
    return ('<li class="lang-menu"><details><summary aria-label="%s: %s"><span aria-hidden="true">%s</span></summary>'
            '<ul>%s</ul></details></li>' % (label, LANGS[lang][0], LANGS[lang][1], "".join(items)))


def add_switcher(text, lang, page):
    text = re.sub(r'<li class="lang-menu">.*?</details></li>', "", text, flags=re.S)
    return text.replace('<li><a class="btn btn-ghost btn-cv"', switcher(lang, page) + '<li><a class="btn btn-ghost btn-cv"', 1)


def add_hreflang(text, page):
    text = re.sub(r'<link rel="alternate" hreflang="[^"]*" href="[^"]*">', "", text)
    if page == "404.html":
        return text
    return re.sub(r'(<link rel="canonical" href="[^"]*">)', lambda m: m.group(1) + hreflang_tags(page), text, count=1)


def keep(s):
    """Texts that stay as they are in every language: app names, web addresses, initials, the owner's name."""
    if s in KEEP or s.endswith(" ↗") and "." in s and " " not in s[:-2] or (len(s) <= 3 and s.isupper()):
        return True
    return s in app_names()


KEEP = {"Beat Saber: Faster Songs on Expert+, episode 1",  # YouTube video titles stay as published
        "Just For Laughs Gags: Priest Gets Drunk On Holy Wine, Psychic Reading In Bathroom, Cannonball Prank",
        "Vitalijs Arkulinskis", "LinkedIn ↗", "arkvital@outlook.com", "LinkedIn", "Adds Up to 180", "Addicted to Hope"}
_NAMES = []


def app_names():
    if not _NAMES:
        sys.path.insert(0, str(HERE / "tools"))
        import seo
        _NAMES.extend(a["name"] for a in seo.app_list())
        _NAMES.extend(["MonShop", "CityCrossers", "Varnote", "FunToPlan", "BusyBun", "DoremiRoad", "PoundFighter",
                       "Parapeet", "CAF Guide", "OScreenplay", "PlanPlate", "Adorable Science"])
    return _NAMES


class Translator:
    def __init__(self, lang):
        self.lang, self.d, self.missing = lang, load(lang), set()

    def t(self, s):
        k = norm(s)
        if not k or not LETTER.search(k):
            return s
        v = self.d.get(k)
        if v is None:
            # counts that change ("See all 55 apps") are stored with {n}
            m = re.search(r"\d+", k)
            tpl = m and self.d.get(k[:m.start()] + "{n}" + k[m.end():])
            if tpl:
                v = tpl.replace("{n}", m.group(0))
            elif keep(k):
                return s
            else:
                self.missing.add(k)
                return s
        lead = s[:len(s) - len(s.lstrip())]
        trail = s[len(s.rstrip()):]
        return lead + v + trail


def translate_html(text, tr):
    """Swap text nodes and the translatable attributes; leaves markup, scripts and styles alone."""
    out, pos = [], 0
    for m in re.finditer(r"<(script|style)\b.*?</\1>|<[^>]+>", text, re.S | re.I):
        chunk = text[pos:m.start()]
        if chunk.strip():
            chunk = html.escape(tr.t(html.unescape(chunk)), quote=False) if LETTER.search(chunk) else chunk
        out.append(chunk)
        tag = m.group(0)
        if not tag.lower().startswith(("<script", "<style")):
            def attr(am):
                name, val = am.group(1), am.group(2)
                return '%s="%s"' % (name, html.escape(tr.t(html.unescape(val)), quote=True))
            tag = re.sub(r'\b(alt|aria-label|title|placeholder)="([^"]*)"', attr, tag)
            if tag.startswith("<meta") and re.search(r'(name|property)="(%s)"' % "|".join(META_NAMES), tag):
                tag = re.sub(r'\b(content)="([^"]*)"', attr, tag)
            if "data-topics=" in tag:
                tag = re.sub(r'data-topics="([^"]*)"', lambda am: 'data-topics="%s"' % html.escape(
                    "|".join(tr.t(html.unescape(x)) for x in am.group(1).split("|")), quote=True), tag)
        elif 'id="app-picks-data"' in tag:
            body = re.search(r">(.*)</script>", tag, re.S).group(1)
            data = json.loads(body.replace("<\\/", "</"))
            for a in data:
                a["description"], a["group"] = tr.t(a["description"]), tr.t(a["group"])
            tag = tag.replace(body, json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
        out.append(tag)
        pos = m.end()
    out.append(text[pos:])
    return "".join(out)


SHARED = ("assets/", "books/", "cv/")


def relink(text, lang):
    """Inside /<lang>/: shared files point to the root copies; page links stay relative (same language)."""
    def fix(m):
        attr, q, url = m.group(1), m.group(2), m.group(3)
        if url.startswith(SHARED):
            url = "../" + url
        return "%s=%s%s%s" % (attr, q, url, q)
    return re.sub(r'\b(href|src|srcset)=(["\'])([^"\']*)\2', fix, text)


def build_page(page, lang):
    src = no_switcher((HERE / page).read_text(encoding="utf-8"))
    if lang == "en":
        out = add_hreflang(add_switcher(src, "en", page), page)
        return out, set()
    tr = Translator(lang)
    out = translate_html(no_french_section(src), tr)
    out = relink(out, lang)
    out = re.sub(r'<html lang="[^"]*"', '<html lang="%s"' % lang, out, count=1)
    out = re.sub(r'<link rel="canonical" href="[^"]*">', '<link rel="canonical" href="%s">' % url_of(lang, page), out, count=1)
    out = re.sub(r'<meta property="og:url" content="[^"]*">', '<meta property="og:url" content="%s">' % url_of(lang, page), out, count=1)
    loc = '<meta property="og:locale" content="%s">' % LANGS[lang][2]
    out = re.sub(r'<meta property="og:locale" content="[^"]*">', "", out)
    out = out.replace('<meta property="og:site_name"', loc + '<meta property="og:site_name"', 1)
    # structured data stays on the English pages (the entity lives there); hreflang ties the versions together
    out = re.sub(r'<script type="application/ld\+json">.*?</script>\n?', "", out, flags=re.S)
    out = add_hreflang(add_switcher(out, lang, page), page)
    return out, tr.missing


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.read_text(encoding="utf-8") if path.exists() else None
    if old != text:
        path.write_text(text, encoding="utf-8", newline="\n")
        print("wrote", path.relative_to(HERE).as_posix())


def build():
    missing = {}
    for lang in LANGS:
        for page in PAGES:
            out, miss = build_page(page, lang)
            write(HERE / page if lang == "en" else HERE / lang / page, out)
            missing.setdefault(lang, set()).update(miss)
    for lang, m in missing.items():
        if m:
            print("%s: %d texts still in English, e.g. %s" % (lang, len(m), sorted(m)[:3]))


if __name__ == "__main__":
    {"extract": extract, "build": build}[sys.argv[1] if len(sys.argv) > 1 else "build"]()
