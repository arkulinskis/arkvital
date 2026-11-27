"""Build the translated PDF + EPUB editions of the books (Russian, French, Latvian).

    python tools/books/translated.py              # every language, both books
    python tools/books/translated.py fr           # one language
    python tools/books/translated.py fr hope      # one language, books whose slug contains "hope"

Translations live next to this repo in ../books-<lang>/chunks/<book>-<n>.<lang>.md (4 chunks per book,
made from the English manuscripts; GLOSSARY.md there holds the style brief and fixed terms). This joins
them into ../books-<lang>/<slug>-<lang>.md and reuses build.py / epub.py / covers.py with the language's
text, labels, covers and front/back matter. Fraunces has no Cyrillic, so Russian uses Lora instead.
Outputs:
    books/<slug>-<lang>.pdf, books/<slug>-<lang>.epub
    assets/img/books/<slug>-<lang>-cover.webp
    ../books-<lang>/<slug>-<lang>-cover.png
"""
import html
import re
import sys
from pathlib import Path

from PIL import Image
from pypdf import PdfReader, PdfWriter

import build
import covers
import epub

HERE = build.HERE
SITE = build.SITE
WORK = build.WORK
BUILD = build.BUILD
YEAR = 2026

# --------------------------------------------------------------- languages --

L = {
    "ru": dict(
        name="Русский", author="Виталий Аркулинский", quotes="«»„“", serif="Lora",
        contents="Содержание", before="Прежде чем начать", contents_h="(?:Содержание|Оглавление)",
        chapter=(r"Глава (\d+) — (.+)", "Глава {n}"), part=r"(Часть [IVX]+|Часть [а-яё]+): (.+)",
        special=r"(Эпилог|Приложение(?: [А-Я])?|Прежде чем начать) ?[—:] (.+)", part_sep=": ",
        back_matter=r"(Эпилог|Приложение|Примечания|Источники)",
        about_h="Об авторе", also_h="Ещё от Arkvital", also_back="Ещё от Arkvital", free_pdf="Бесплатное PDF-издание",
        download="Скачать бесплатно можно на", start="Начать чтение", cover="Обложка", title_page="Титульный лист",
        copyright_h="Авторские права", epigraph_h="Эпиграф", cover_alt="Обложка книги {t}, автор Arkvital",
        rights="Все права защищены.",
        copy=[
            "Никакую часть этой книги нельзя воспроизводить или продавать в любой форме без письменного разрешения автора, кроме коротких цитат в рецензиях и статьях.",
            "Люди в этой книге — собирательные образы. Любое сходство с реальными людьми случайно. Описанные исследования настоящие, их список — в конце книги.",
            "Эта книга — общая информация и личный взгляд автора. Это не медицинская, психологическая, юридическая или финансовая консультация. Если тебе тяжело, поговори со специалистом, а в экстренной ситуации звони в местную службу экстренной помощи. В Канаде и США можно позвонить или написать на номер 988.",
        ],
        edition="Бесплатное {fmt}-издание на русском языке, версия 1.0, ноябрь {y}.<br>Перевод с английского. Обложка и вёрстка — Arkvital.",
        fonts_line="Набрано шрифтами Literata, Lora и Inter.", publisher="Издатель — Arkvital",
        about="""<p><b>Arkvital</b> — это Виталий Аркулинский, инженер-механик и программист, который стал руководителем проектов и команд. Больше двенадцати лет, в десятке с лишним отраслей, он обучал менеджеров, делал инструменты для команд и научился сначала искать настоящую причину проблемы, а уже потом выбирать решение.</p>
<p>Он пишет о людях, прогрессе и тихой работе, на которой держится хорошая работа, на <a href="https://arkvital.com/ru/">arkvital.com</a> и делает небольшие полезные приложения через Addanapp.</p>
<p>Если что-то в этой книге отозвалось — или наоборот, не попало, — он будет рад узнать. Короткий созвон можно забронировать на <a href="https://tidycal.com/arkvital">tidycal.com/arkvital</a>.</p>""",
        books={
            "180": dict(
                title="В сумме 180",
                subtitle="Достижение, Благодарность, Надежда — и громкое «А-А-Ах», которое держит их вместе",
                tagline="Углы любого треугольника в сумме дают 180.<br>Как и жизнь, которая работает.",
                blurb=[
                    "Достижение, Благодарность и Надежда — три угла хорошей жизни. Если раздуть один, он сжимает два других. Если потерять один, вся фигура складывается.",
                    "В библиотечной комнате со складными стульями и кофе, который отдаёт монетками, пятеро обычных людей учатся рисовать этот треугольник: служить тем, кто тебе нравится, даже пока они не ответили взаимностью; каждый день говорить «спасибо», в том числе себе; и упрямо верить, что можно идти дальше.",
                    "Смешная и практичная книга, опирающаяся на проверенные исследования. В конце — ежедневный ритуал на десять минут и один большой, громкий выдох. А-А-Ах.",
                ],
                keywords="самопомощь, благодарность, надежда, достижения, тревога, Arkvital",
                first_marker="## Пара слов перед началом",
                cover=dict(kicker="Достижение · Благодарность · Надежда", l1="В <i>сумме</i>", letters="ДБН",
                           css=".cv180 .cv-kicker{letter-spacing:.2em}.cv180 .cv-title .l1{font-size:56px}"),
            ),
            "hope": dict(
                title="Зависимость от надежды",
                subtitle="Почему мечтать приятнее, чем делать, — и как всё-таки запустить свою жизнь",
                tagline="Мечта платит тебе ещё до того, как ты что-то сделал. В этом и проблема.",
                blurb=[
                    "У тебя есть папка с идеями. Каждая выглядит в голове прекрасно — и именно поэтому никогда не покидает папку: мечта выдаёт награду сразу, а работа приносит только баги.",
                    "«Зависимость от надежды» — инженерное руководство по тому, как сломать эту привычку. Почему планирование ощущается как прогресс, как воспитание задало тебе настройки по умолчанию и какие жёсткие истины снимают чары. А потом — инструменты: прототипы, планы «если — то», петли обратной связи, связки и критерии остановки.",
                    "Каждая глава заканчивается полевым испытанием, которое ты делаешь в течение 24 часов. Поднимайся вместе с пятью людьми из вторничной мастерской в гараже — они перестают мечтать о вершине и начинают двигаться.",
                ],
                keywords="самопомощь, мотивация, прокрастинация, привычки, инженерия, Arkvital",
                first_marker="## Прежде чем начать",
                cover=dict(l1="Зависимость", l2="от <i>надежды</i>",
                           sub="Почему мечтать приятнее, чем делать, —<br>и как всё-таки запустить свою жизнь",
                           css=".cvhope .cv-title .l1{font-size:64px}.cvhope .cv-title .l2{font-size:58px}.cvhope .cv-sub{top:244px}"),
            ),
        },
    ),
    "fr": dict(
        name="Français", author="Vitalijs Arkulinskis", quotes=["« ", " »", "“", "”"], serif="Fraunces",
        contents="Table des matières", before="Avant de commencer", contents_h="Table des matières",
        chapter=(r"Chapitre (\d+) — (.+)", "Chapitre {n}"), part=r"(Partie [0-9IVX]+) ?: (.+)",
        special=r"(Épilogue|Annexe(?: [A-Z])?|Avant de commencer) ?[—:] (.+)", part_sep=" : ",
        back_matter=r"(Épilogue|Annexe|Notes|Sources)",
        about_h="À propos de l'auteur", also_h="Du même auteur", also_back="Du même auteur", free_pdf="Édition PDF gratuite",
        download="Téléchargement gratuit sur", start="Commencer la lecture", cover="Couverture", title_page="Page de titre",
        copyright_h="Droits d'auteur", epigraph_h="Épigraphe", cover_alt="Couverture de {t}, par Arkvital",
        rights="Tous droits réservés.",
        copy=[
            "Aucune partie de ce livre ne peut être reproduite ou vendue, sous quelque forme que ce soit, sans l'autorisation écrite de l'auteur, sauf de courtes citations dans des critiques et des articles.",
            "Les personnes de ce livre sont des personnages composites imaginaires. Toute ressemblance avec des personnes réelles est une coïncidence. Les recherches citées sont réelles et listées à la fin.",
            "Ce livre propose des informations générales et un point de vue personnel. Ce n'est pas un avis médical, psychologique, juridique ou financier. Si tu traverses un moment difficile, parle à un professionnel qualifié ou, en cas d'urgence, appelle le numéro d'urgence local. Au Canada et aux États-Unis, tu peux appeler ou texter le 988.",
        ],
        edition="Édition {fmt} gratuite en français, version 1.0, novembre {y}.<br>Traduit de l'anglais. Couverture et mise en page : Arkvital.",
        fonts_line="Composé en Literata, Fraunces et Inter.", publisher="Publié par Arkvital",
        about="""<p><b>Arkvital</b>, c'est Vitalijs Arkulinskis, ingénieur mécanique et logiciel devenu responsable de projets et d'équipes. Pendant plus de douze ans, dans plus de dix secteurs, il a accompagné des gestionnaires, créé des outils pour des équipes et appris à chercher la vraie cause d'un problème avant de choisir la solution.</p>
<p>Il écrit sur les gens, le progrès et le travail discret qui se cache sous le bon travail sur <a href="https://arkvital.com/fr/">arkvital.com</a>, et crée de petites applications utiles avec Addanapp.</p>
<p>Si quelque chose dans ce livre t'a parlé, ou t'a laissé de glace, il aimerait le savoir. Tu peux réserver un court appel sur <a href="https://tidycal.com/arkvital">tidycal.com/arkvital</a>.</p>""",
        books={
            "180": dict(
                title="Ça fait 180",
                subtitle="Accomplissement, Appréciation, Espoir — et le grand AAH qui les tient ensemble",
                tagline="Les angles d'un triangle font toujours 180.<br>Une vie qui marche aussi.",
                blurb=[
                    "L'Accomplissement, l'Appréciation et l'Espoir sont les trois angles d'une bonne vie. Si tu en pousses un trop loin, il écrase les deux autres. Si tu en perds un, toute la forme s'effondre.",
                    "Dans une salle de bibliothèque, avec des chaises pliantes et un café qui goûte la monnaie, cinq personnes ordinaires apprennent à dessiner le triangle : servir les gens qu'elles aiment, même avant d'être aimées en retour ; dire merci chaque jour, à elles-mêmes aussi ; et garder la conviction têtue qu'on peut continuer.",
                    "Drôle, pratique et appuyé par des recherches vérifiées, <i>Ça fait 180</i> se termine par une routine quotidienne de dix minutes et une grande expiration bien sonore. AAH.",
                ],
                keywords="développement personnel, gratitude, espoir, accomplissement, anxiété, Arkvital",
                first_marker="## Un mot avant de commencer",
                cover=dict(kicker="Accomplissement · Appréciation · Espoir", l1="Ça <i>fait</i>", letters="AAE",
                           css=".cv180 .cv-kicker{letter-spacing:.2em}"),
            ),
            "hope": dict(
                title="Accro à l'espoir",
                subtitle="Pourquoi rêver fait plus de bien qu'agir — et comment lancer ta vie quand même",
                tagline="Le rêve te paie avant que tu aies fait quoi que ce soit. C'est bien ça, le problème.",
                blurb=[
                    "Tu as un dossier plein d'idées. Chacune est magnifique dans ta tête, et c'est justement pour ça qu'aucune n'en sort : le rêve te donne la récompense tout de suite, et l'action ne te donne que des bogues.",
                    "<i>Accro à l'espoir</i> est un guide d'ingénieur pour casser cette habitude. Pourquoi planifier donne l'impression d'avancer, comment ton enfance a réglé tes paramètres par défaut, et quelles vérités dures rompent le charme. Puis les outils : prototypes, plans « si… alors », boucles de rétroaction, cordées et critères d'arrêt.",
                    "Chaque chapitre se termine par un test sur le terrain à faire dans les 24 heures. Grimpe avec cinq personnes d'un atelier du mardi soir, dans un garage, qui arrêtent de rêver au sommet et se mettent en marche.",
                ],
                keywords="développement personnel, motivation, procrastination, habitudes, ingénierie, Arkvital",
                first_marker="## Avant de commencer",
                cover=dict(l1="Accro", l2="à <i>l'espoir</i>",
                           sub="Pourquoi rêver fait plus de bien qu'agir,<br>et comment lancer ta vie quand même", css=""),
            ),
        },
    ),
    "lv": dict(
        name="Latviešu", author="Vitālijs Arkulinskis", quotes="„”‚‘", serif="Fraunces",
        contents="Saturs", before="Pirms sākam", contents_h="Saturs",
        chapter=(r"(\d+)\. nodaļa — (.+)", "{n}. nodaļa"), part=r"(\d+\. daļa|[IVX]+ daļa): (.+)",
        special=r"(Epilogs|[A-Z] pielikums|Pielikums|Pirms sākam) ?[—:] (.+)", part_sep=": ",
        back_matter=r"(Epilogs|[A-Z] pielikums|Pielikums|Piezīmes|Avoti)",
        about_h="Par autoru", also_h="Vēl no Arkvital", also_back="Vēl no Arkvital", free_pdf="Bezmaksas PDF izdevums",
        download="Lejupielādē bez maksas vietnē", start="Sākt lasīt", cover="Vāks", title_page="Titullapa",
        copyright_h="Autortiesības", epigraph_h="Epigrāfs", cover_alt="Grāmatas „{t}” vāks, autors Arkvital",
        rights="Visas tiesības aizsargātas.",
        copy=[
            "Nevienu šīs grāmatas daļu nedrīkst pavairot vai pārdot nekādā veidā bez autora rakstiskas atļaujas, izņemot īsus citātus recenzijās un rakstos.",
            "Cilvēki šajā grāmatā ir izdomāti, salikti no daudzu cilvēku iezīmēm. Jebkura līdzība ar reāliem cilvēkiem ir nejauša. Pieminētie pētījumi ir īsti, un to saraksts ir grāmatas beigās.",
            "Šī grāmata sniedz vispārīgu informāciju un autora personīgo skatījumu. Tā nav medicīniska, psiholoģiska, juridiska vai finanšu konsultācija. Ja tev ir grūti, parunā ar speciālistu, bet ārkārtas situācijā zvani vietējam ārkārtas palīdzības numuram (Latvijā — 112). Kanādā un ASV var zvanīt vai rakstīt uz 988.",
        ],
        edition="Bezmaksas {fmt} izdevums latviešu valodā, versija 1.0, {y}. gada novembris.<br>Tulkots no angļu valodas. Vāks un makets — Arkvital.",
        fonts_line="Burtu saimes: Literata, Fraunces un Inter.", publisher="Izdevējs — Arkvital",
        about="""<p><b>Arkvital</b> ir Vitālijs Arkulinskis — mašīnbūves un programmatūras inženieris, kurš kļuva par projektu un komandu vadītāju. Vairāk nekā divpadsmit gadus, vairāk nekā desmit nozarēs, viņš ir apmācījis vadītājus, veidojis rīkus komandām un iemācījies vispirms meklēt problēmas īsto cēloni un tikai tad izvēlēties risinājumu.</p>
<p>Viņš raksta par cilvēkiem, progresu un kluso darbu, uz kura balstās labs darbs, vietnē <a href="https://arkvital.com/lv/">arkvital.com</a> un ar Addanapp veido nelielas, noderīgas lietotnes.</p>
<p>Ja kaut kas šajā grāmatā tevi uzrunāja — vai tieši otrādi —, viņš labprāt to uzzinātu. Īsu sarunu vari pieteikt vietnē <a href="https://tidycal.com/arkvital">tidycal.com/arkvital</a>.</p>""",
        books={
            "180": dict(
                title="Kopā 180",
                subtitle="Sasniegums, Pateicība, Cerība — un skaļais AAH, kas tos tur kopā",
                tagline="Jebkura trijstūra leņķi kopā ir 180.<br>Tāpat kā dzīve, kas darbojas.",
                blurb=[
                    "Sasniegums, Pateicība un Cerība ir trīs labas dzīves leņķi. Ja vienu uzpūt par lielu, tas saspiež pārējos divus. Ja vienu pazaudē, visa figūra saplok.",
                    "Bibliotēkas telpā ar saliekamiem krēsliem un kafiju, kas garšo pēc monētām, pieci parasti cilvēki mācās uzzīmēt šo trijstūri: kalpot tiem, kas tev patīk, pat pirms viņi atbild ar to pašu; katru dienu teikt „paldies”, arī sev; un spītīgi ticēt, ka vari iet tālāk.",
                    "Smieklīga, praktiska un balstīta pārbaudītos pētījumos, <i>Kopā 180</i> beidzas ar desmit minūšu ikdienas rutīnu un vienu lielu, skaļu izelpu. AAH.",
                ],
                keywords="pašpalīdzība, pateicība, cerība, sasniegumi, trauksme, Arkvital",
                first_marker="## Daži vārdi pirms sākuma",
                cover=dict(kicker="Sasniegums · Pateicība · Cerība", l1="<i>Kopā</i>", letters="SPC", css=""),
            ),
            "hope": dict(
                title="Atkarība no cerības",
                subtitle="Kāpēc sapņot ir patīkamāk nekā darīt — un kā tomēr palaist savu dzīvi",
                tagline="Sapnis tev samaksā, pirms tu vēl kaut ko esi izdarījis. Tieši tā ir problēma.",
                blurb=[
                    "Tev ir mape ar idejām. Katra galvā izskatās brīnišķīga — un tieši tāpēc tā nekad netiek ārā no mapes: sapnis atlīdzību dod uzreiz, bet darīšana dod tikai kļūdas.",
                    "<i>Atkarība no cerības</i> ir inženiera ceļvedis, kā salauzt šo ieradumu. Kāpēc plānošana šķiet kā progress, kā audzināšana iestatīja tavus noklusējumus un kuras skarbās patiesības lauž burvestību. Un tad rīki: prototipi, „ja — tad” plāni, atgriezeniskās saites cilpas, saites komandas un apstāšanās kritēriji.",
                    "Katra nodaļa beidzas ar lauka testu, ko izdari 24 stundu laikā. Kāp kopā ar pieciem cilvēkiem no otrdienas vakara garāžas darbnīcas, kuri beidz sapņot par virsotni un sāk kustēties.",
                ],
                keywords="pašpalīdzība, motivācija, atlikšana, ieradumi, inženierija, Arkvital",
                first_marker="## Pirms sākam",
                cover=dict(l1="Atkarība", l2="no <i>cerības</i>",
                           sub="Kāpēc sapņot ir patīkamāk nekā darīt —<br>un kā tomēr palaist savu dzīvi",
                           css=".cvhope .cv-title .l1{font-size:70px}"),
            ),
        },
    ),
}

BASE = {"180": dict(slug="adds-up-to-180", accent="#b9512d", chapters=30),
        "hope": dict(slug="addicted-to-hope", accent="#23406b", chapters=41)}

CUR = {}          # the language being built (the overrides below read it)


def books_for(lang):
    lg = L[lang]
    out = []
    for kind in ("180", "hope"):
        b = dict(BASE[kind], **lg["books"][kind], kind=kind, lang=lang, author_cover="ARKVITAL")
        b["en_slug"] = b["slug"]
        b["slug"] = f"{b['en_slug']}-{lang}"
        b["folder"] = WORK / f"books-{lang}"
        out.append(b)
    return out


def assemble(b):
    parts = sorted(b["folder"].glob(f"chunks/{b['kind']}-*.{b['lang']}.md"))
    assert len(parts) == 4, f"{b['lang']}: expected 4 translated chunks for {b['kind']}, found {len(parts)}"
    text = "\n\n".join(p.read_bytes().decode("utf-8").replace("\r\n", "\n").strip("\n") for p in parts) + "\n"
    b["src"] = b["folder"] / f"{b['slug']}.md"
    b["src"].write_bytes(text.encode("utf-8"))


# ------------------------------------------------------ parser overrides --

_MD = build.MarkdownIt


def md_lang(preset="commonmark", options=None, *a, **k):
    options = dict(options or {})
    options["quotes"] = CUR["quotes"]
    return _MD(preset, options, *a, **k)


def load_source(b):
    text = b["src"].read_text(encoding="utf-8").replace("\r\n", "\n")
    epigraph = ""
    if b["kind"] == "180":
        epigraph = text.split("\n---\n")[1].strip()
        text = text[text.index(b["first_marker"]):]
        text = re.sub(rf"## {CUR['contents_h']}\n.*?(?=\n## {CUR['before']})", "", text, flags=re.S)
    else:
        text = text[text.index(b["first_marker"]):]
    lines, keep = text.split("\n"), []
    for i, line in enumerate(lines):
        if line.strip() == "---":
            nxt = next((l for l in lines[i + 1:] if l.strip()), "")
            prv = next((l for l in reversed(keep) if l.strip()), "")
            if nxt.startswith("#") or prv.startswith("#") or not nxt or not prv:
                continue
        keep.append(line)
    return "\n".join(keep), epigraph


def classify(b, level, txt):
    if b["kind"] == "180":
        return {1: "part", 2: "chapter", 3: "section"}.get(level, "sub")
    if level == 2:
        return "part" if re.match(CUR["part"], txt) else "chapter"
    if level == 3:
        return "chapter" if re.match(r"\d+\. ", txt) and not re.match(CUR["part"], txt) else "section"
    return "section" if level == 4 else "sub"


def split_label(txt):
    rx, fmt = CUR["chapter"]
    m = re.match(rx, txt) or re.match(r"(\d+)\. (.+)", txt)
    if m:
        return fmt.format(n=m.group(1)), m.group(2), m.group(1)
    m = re.match(CUR["part"], txt)
    if m:
        return m.group(1), m.group(2), None
    m = re.match(CUR["special"], txt)
    if m:
        return m.group(1), m.group(2), None
    return "", txt, None


build.MarkdownIt = md_lang
build.load_source = load_source
build.classify = classify
build.split_label = split_label

# ------------------------------------------------------------- styling --


def font_css():
    f = (HERE / "fonts").as_uri()
    return build.font_css() + f"""
@font-face{{font-family:Lora;src:url("{f}/Lora.ttf");font-weight:400 700;font-style:normal}}
@font-face{{font-family:Lora;src:url("{f}/Lora-Italic.ttf");font-weight:400 700;font-style:italic}}
"""


def serif(css):
    return css.replace("Fraunces", CUR["serif"]) if CUR["serif"] != "Fraunces" else css


READABLE = "body{font-size:10.8pt;line-height:1.6}p{margin-bottom:8pt}"


def cover_css(b):
    return serif(covers.COVER_CSS) + b["cover"].get("css", "")


def book_css(b):
    css = (HERE / "book.css").read_text(encoding="utf-8")
    return font_css() + cover_css(b) + serif(css).replace("__TITLE__", b["title"]).replace("__ACCENT__", b["accent"]) + READABLE


# -------------------------------------------------------------- covers --


def front(b):
    c = b["cover"]
    if b["kind"] == "180":
        letters = iter(c["letters"])
        art = re.sub(r'(class="cv180-angle" fill="[^"]+">)[AH](</text>)', lambda m: m.group(1) + next(letters) + m.group(2), covers.art_180())
        art = art.replace("A + A + H = 180°", " + ".join(c["letters"]) + " = 180°")
        return f'''<div class="cover cv180">{art}
  <div class="cv-copy">
    <p class="cv-kicker">{c['kicker']}</p>
    <h1 class="cv-title"><span class="l1">{c['l1']}</span><span class="l2">180<sup>°</sup></span></h1>
    <p class="cv-author">{b['author_cover']}</p>
  </div>
</div>'''
    return f'''<div class="cover cvhope">{covers.art_hope()}
  <div class="cv-copy">
    <h1 class="cv-title"><span class="l1">{c['l1']}</span><span class="l2">{c['l2']}</span></h1>
    <p class="cv-sub">{c['sub']}</p>
    <p class="cv-author">{b['author_cover']}</p>
  </div>
</div>'''


def back_cover(b, other):
    s = covers.back_cover(dict(b, slug=b["en_slug"]), other)
    return s.replace(f"Also by {b['author_cover'].title()}", CUR["also_back"]).replace("Free PDF edition", CUR["free_pdf"])


# ----------------------------------------------------------------- pdf --


def num_of(label):
    return re.search(r"\d+", label).group()


def toc_html(toc, pages):
    rows = []
    for kind, hid, label, title in toc:
        pg = pages.get(hid, "000")
        if kind == "part":
            rows.append(f'<li class="toc-part"><a href="#{hid}"><span class="t">{label}{CUR["part_sep"]}{html.escape(title)}</span>'
                        f'<span class="pg">{pg}</span></a></li>')
        else:
            num = f'<span class="n">{num_of(label)}</span>' if label and re.search(r"\d", label) else ""
            name = html.escape(title) if (not label or re.search(r"\d", label)) else f"{label}{CUR['part_sep']}{html.escape(title)}"
            rows.append(f'<li class="toc-ch"><a href="#{hid}">{num}<span class="t">{name}</span>'
                        f'<span class="dots"></span><span class="pg">{pg}</span></a></li>')
    return f'<section class="front toc-page"><h2 class="front-h">{CUR["contents"]}</h2><ol class="toc">{"".join(rows)}</ol></section>'


def epigraph_html(epigraph):
    md = _MD("commonmark", {"typographer": True}).enable(["replacements"])
    quotes = []
    for block in re.split(r"\n\s*\n", epigraph):
        lines = [l.lstrip("> ").strip() for l in block.strip().split("\n") if l.strip()]
        quotes.append(f'<blockquote><p class="q">{md.renderInline(lines[0])}</p>'
                      f'<p class="by">{md.renderInline(" ".join(lines[1:]))}</p></blockquote>')
    return "".join(quotes)


def copyright_html(b, fmt, br="<br>"):
    paras = "".join(f"<p>{p}</p>" for p in CUR["copy"])
    edition = CUR["edition"].format(fmt=fmt, y=YEAR).replace("<br>", br)
    fonts = f"{br}{CUR['fonts_line']}" if fmt == "PDF" else ""
    return f"""<p><b>{b['title']}</b>{br}<i>{b['subtitle']}</i></p>
<p>Copyright © {YEAR} {CUR['author']}. {CUR['rights']}</p>
{paras}
<p>{edition}{fonts}</p>
<p>{CUR['publisher']} · <a href="https://arkvital.com/{b['lang']}/">arkvital.com</a></p>"""


def also_html(other, br=""):
    return f"""<h2 class="front-h">{CUR['also_h']}</h2>
<p class="also-title">{other['title']}</p>
<p class="also-sub"><i>{other['subtitle']}</i></p>
{''.join(f'<p>{p}</p>' for p in other['blurb'][:2])}
<p>{CUR['download']} <a href="https://arkvital.com/{other['lang']}/blogs.html#books">arkvital.com</a>.</p>"""


def book_html(b, other, body, toc, pages, epigraph, with_markers):
    epi = f'<section class="front epigraph">{epigraph_html(epigraph)}</section>' if epigraph else ""
    frontm = f"""
{front(b)}
<section class="front half-title"><p>{b['title']}</p></section>
<section class="front title-page">
  <h1>{b['title']}</h1>
  <p class="tp-sub">{b['subtitle']}</p>
  <p class="tp-author">Arkvital</p>
  <p class="tp-imprint">arkvital.com</p>
</section>
<section class="front copyright">{copyright_html(b, "PDF")}</section>
{epi}
{toc_html(toc, pages)}
"""
    back = f"""
<section class="front about"><h2 class="front-h">{CUR['about_h']}</h2>{CUR['about']}</section>
<section class="front also">{also_html(other)}</section>
{back_cover(b, other)}
"""
    mk = "" if with_markers else ".mk{display:none}"
    return f"""<!doctype html><html lang="{b['lang']}"><head><meta charset="utf-8">
<title>{b['title']} — Arkvital</title>
<style>{book_css(b)}{mk}</style></head>
<body class="book-{b['en_slug']}">{frontm}<main class="body">{body}</main>{back}</body></html>"""


def make_pdf(b, other):
    print(f"== {b['title']} (PDF)")
    md_text, epigraph = load_source(b)
    body, toc, n_ch = build.render_body(b, md_text)
    tmp = BUILD / f"{b['slug']}.html"
    tmp.write_text(book_html(b, other, body, toc, {}, epigraph, True), encoding="utf-8")
    pass1 = build.print_pdf(tmp, BUILD / f"{b['slug']}-pass1.pdf")
    pages = build.find_pages(pass1)
    missing = [hid for _, hid, *_ in toc if hid not in pages]
    if missing:
        print("   ! no page found for", missing)
    tmp.write_text(book_html(b, other, body, toc, pages, epigraph, False), encoding="utf-8")
    raw = build.print_pdf(tmp, BUILD / f"{b['slug']}-raw.pdf")
    assert len(PdfReader(str(raw)).pages) == len(PdfReader(str(pass1)).pages)
    out = SITE / "books" / f"{b['slug']}.pdf"
    w = PdfWriter(clone_from=str(raw))
    w.add_metadata({"/Title": f"{b['title']}: {b['subtitle']}", "/Author": f"Arkvital ({CUR['author']})",
                    "/Subject": re.sub("<[^>]+>", "", b["blurb"][0]), "/Keywords": b["keywords"],
                    "/Creator": "Arkvital", "/Producer": "Arkvital", "/Lang": b["lang"]})
    w.page_mode = "/UseOutlines"
    w.compress_identical_objects()
    with open(out, "wb") as fh:
        w.write(fh)
    # cover: full-size png next to the translation, web copy for the site
    page = BUILD / f"{b['slug']}-cover.html"
    page.write_text(f"""<!doctype html><html lang="{b['lang']}"><head><meta charset="utf-8"><style>{font_css()}{cover_css(b)}
html,body{{margin:0;background:#000}}</style></head><body>{front(b)}</body></html>""", encoding="utf-8")
    png = b["folder"] / f"{b['slug']}-cover.png"
    build.chrome("--hide-scrollbars", "--force-device-scale-factor=2.5", "--window-size=576,864",
                 "--virtual-time-budget=5000", f"--screenshot={png}", page.as_uri())
    Image.open(png).convert("RGB").resize((600, 900), Image.LANCZOS).save(
        SITE / "assets" / "img" / "books" / f"{b['slug']}-cover.webp", quality=88, method=6)
    n = len(PdfReader(str(out)).pages)
    print(f"   {n} pages, {n_ch} chapters, {out.stat().st_size / 1e6:.1f} MB -> {out.relative_to(SITE)}")
    return n


# ---------------------------------------------------------------- epub --

_page, _opf, _nav = epub.page, epub.opf, epub.nav_xhtml


def e_page(title, body, **kw):
    s = _page(title, body, **kw).replace('lang="en" xml:lang="en"', f'lang="{CUR["code"]}" xml:lang="{CUR["code"]}"')
    return re.sub(r'alt="Cover of (.*?) by Arkvital"', lambda m: 'alt="%s"' % CUR["cover_alt"].format(t=m.group(1)), s)


def e_opf(*a, **k):
    s = _opf(*a, **k).replace('xml:lang="en"', f'xml:lang="{CUR["code"]}"')
    s = s.replace("<dc:language>en</dc:language>", f"<dc:language>{CUR['code']}</dc:language>")
    return s.replace(f"{build.AUTHOR}. All rights reserved.", f"{CUR['author']}. {CUR['rights']}")


def e_nav(*a, **k):
    return _nav(*a, **k).replace(">Contents<", f">{CUR['contents']}<").replace(">Start reading<", f">{CUR['start']}<") \
        .replace(">Cover<", f">{CUR['cover']}<").replace("— Contents</title>", f"— {CUR['contents']}</title>")


def e_front(b, epigraph):
    pages = [("title", CUR["title_page"], f"""<section class="front title-page" epub:type="titlepage">
<h1>{b['title']}</h1>
<p class="tp-sub">{b['subtitle']}</p>
<p class="tp-author">Arkvital</p>
<p>arkvital.com</p>
</section>"""),
             ("copyright", CUR["copyright_h"], f'<section class="front copyright" epub:type="copyright-page">{copyright_html(b, "EPUB", "<br />")}</section>')]
    if epigraph:
        pages.append(("epigraph", CUR["epigraph_h"], f'<section class="front epigraph" epub:type="epigraph">{epigraph_html(epigraph)}</section>'))
    return pages


def e_back(b, other):
    return [("about", CUR["about_h"], f'<section class="front about"><h2 class="front-h">{CUR["about_h"]}</h2>{CUR["about"]}</section>'),
            ("also", CUR["also_h"], f'<section class="front also">{also_html(other)}</section>')]


def e_tree(toc, files):
    tree = []
    for kind, hid, label, title in toc:
        name = epub.plain(title)
        if label and re.search(r"\d", label):
            name = f"{num_of(label)}. {name}"
        elif label:
            name = f"{label}{CUR['part_sep']}{name}"
        item = dict(href=files[hid], name=name, kids=[])
        if kind == "part":
            item["part"] = True
            tree.append(item)
        elif tree and tree[-1].get("part") and not re.match(CUR["back_matter"], name):
            tree[-1]["kids"].append(item)
        else:
            tree.append(item)
    return tree


epub.page, epub.opf, epub.nav_xhtml = e_page, e_opf, e_nav
epub.front_pages, epub.back_pages, epub.nav_tree = e_front, e_back, e_tree
epub.CSS = epub.CSS.replace("text-align: justify;", "text-align: left;")
_cover_jpeg = epub.cover_jpeg
epub.cover_jpeg = lambda b: _cover_jpeg(dict(b, src=b["folder"] / "x.md"))   # png lives in ../books-<lang>/


def run(lang, only=""):
    CUR.clear()
    CUR.update(L[lang], code=lang)
    books = books_for(lang)
    for b in books:
        if only in b["slug"]:
            assemble(b)
    for i, b in enumerate(books):
        if only in b["slug"]:
            make_pdf(b, books[1 - i])
            epub.make_epub(b, books[1 - i])


if __name__ == "__main__":
    BUILD.mkdir(exist_ok=True)
    langs = [a for a in sys.argv[1:] if a in L] or list(L)
    only = next((a for a in sys.argv[1:] if a not in L), "")
    for lang in langs:
        run(lang, only)
