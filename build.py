"""Builds the static site from src/ into the repo root.

python3 build.py          -> draft build (draft banner, notes, noindex)
python3 build.py --live   -> production build
"""
import json, os, re, shutil, sys

LIVE = '--live' in sys.argv
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'src')
SITE = 'https://tomizs.com'
WEBHOOK = os.environ.get('TOMIZ_WEBHOOK', open(os.path.join(SRC, 'webhook.txt')).read().strip() if os.path.exists(os.path.join(SRC, 'webhook.txt')) else '')

read = lambda p: open(os.path.join(SRC, p), encoding='utf-8').read()
ARTICLES = json.loads(read('articles.json'))

# page name -> (url path, title, description, nav key)
PAGES = {
    'home': ('/', 'TomiZ · עיצוב למידה והעברת ידע', 'סדנאות, תהליכי הדרכה והרצאות מעשיות על AI, למידה והעברת ידע, לארגונים, לקהילות ולבעלי מקצוע.', ''),
    'orgs': ('/orgs/', 'לארגונים · TomiZ', 'Unboxing, Train-the-Trainer, מיפוי פערי מיומנויות והטמעת AI לצוותי L&D ומשאבי אנוש.', 'orgs'),
    'experts': ('/experts/', 'למומחים · TomiZ', 'הידע שלך יכול להפוך למוצר: סדנה, קורס, מוצר דיגיטלי או כל פורמט אחר.', 'experts'),
    'talks': ('/talks/', 'הרצאות · TomiZ', 'למידה שמחזיקה מים: הרצאה לכנסים, ימי עיון, צוותי הדרכה ומשאבי אנוש.', 'talks'),
    'about': ('/about/', 'אודות · TomiZ', 'שקד וולוז\'ינסקי לנס, מעצבת חוויות למידה, מנחת סדנאות ומרצה, מייסדת TomiZ.', 'about'),
    'blog': ('/blog/', 'משתמשים בבינה בתבונה · TomiZ', 'טיפים קצרים על AI, העברת ידע והדרכה, שאפשר ליישם כבר מחר בבוקר.', 'blog'),
    'en': ('/en/', 'TomiZ · Learning design & knowledge transfer', 'Turning expert knowledge into training that works, for L&D and Customer Education teams.', 'en'),
    'ai-dictionary': ('/ai-dictionary/', 'מילון AI למומחים · TomiZ', '8 מונחים שכל מומחה ואיש מקצוע צריך להכיר, ואיך משתמשים בכל אחד כבר מחר בבוקר. מדריך חינמי.', ''),
    'privacy': ('/privacy/', 'מדיניות פרטיות · TomiZ', 'מדיניות הפרטיות של האתר tomizs.com.', ''),
    'accessibility': ('/accessibility/', 'הצהרת נגישות · TomiZ', 'הצהרת הנגישות של האתר tomizs.com.', ''),
}

def links(html):
    html = re.sub(r'href="#a-([\w-]+)"', r'href="/blog/\1/"', html)
    html = html.replace('href="#home"', 'href="/"')
    for name, (path, *_) in PAGES.items():
        html = html.replace(f'href="#{name}"', f'href="{path}"')
    return html

def strip_draft(html):
    if not LIVE:
        return html
    # drop elements marked draft-only (they never nest another draft-only element)
    out = html
    while True:
        m = re.search(r'<(\w+)([^>]*class="[^"]*\bdraft-only\b[^"]*"[^>]*)>', out)
        if not m:
            return out
        tag, start, depth, i = m.group(1), m.start(), 0, m.start()
        pat = re.compile(rf'<{tag}\b|</{tag}>')
        for t in pat.finditer(out, start):
            depth += 1 if not t.group().startswith('</') else -1
            if depth == 0:
                out = out[:start] + out[t.end():]
                break

def card(a):
    return (f'<a class="card reveal" href="/blog/{a["id"]}/"><span class="tag">{a["tag"]}</span>'
            f'<h3>{a["title"]}</h3><p>{a["teaser"]}</p><span class="go">לקריאה ←</span></a>')

def page(body, title, desc, path, nav, lang='he', image='/assets/og.png'):
    header = read('header.html')
    if nav:
        header = header.replace(f'data-nav="{nav}"', f'data-nav="{nav}" aria-current="page"')
    banner = '' if LIVE else '<div class="draft">טיוטה לעיון · לא באוויר</div>\n'
    robots = '' if LIVE else '<meta name="robots" content="noindex,nofollow">\n'
    hook = f'<script>window.TOMIZ_WEBHOOK={json.dumps(WEBHOOK)}</script>\n' if WEBHOOK else ''
    html = f'''<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{title}</title>
<meta name="description" content="{desc}">
{robots}<link rel="canonical" href="{SITE}{path}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{SITE}{path}">
<meta property="og:image" content="{SITE}{image}">
<meta property="og:locale" content="{'en_US' if lang == 'en' else 'he_IL'}">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;700;800&display=swap">
<link rel="stylesheet" href="/assets/site.css">
</head>
<body id="top">
{banner}{header}
<main>
{body}
</main>
{read('contact.html')}
{read('footer.html')}
{hook}<script src="/assets/site.js" defer></script>
</body>
</html>
'''
    return strip_draft(links(html))

def write(path, html):
    out = os.path.join(ROOT, path.strip('/'), 'index.html') if path != '/' else os.path.join(ROOT, 'index.html')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w', encoding='utf-8').write(html)

WAVE = '<svg class="wave" viewBox="0 0 1440 56" preserveAspectRatio="none" aria-hidden="true" style="color:var(--bg)"><path fill="currentColor" d="M0 56V28C240 0 480 0 720 22s480 34 720 6v28z"/></svg>'

for name, (path, title, desc, nav) in PAGES.items():
    body = read(f'pages/{name}.html')
    body = body.replace('<div class="articles" id="home-articles"></div>', '<div class="articles">' + ''.join(card(a) for a in ARTICLES[:3]) + '</div>')
    body = body.replace('<div class="articles" id="all-articles"></div>', '<div class="articles">' + ''.join(card(a) for a in ARTICLES) + '</div>')
    write(path, page(body, title, desc, path, nav, 'en' if name == 'en' else 'he',
                     '/assets/ai-dictionary-cover.jpg' if name == 'ai-dictionary' else '/assets/og.png'))

for a in ARTICLES:
    body = (f'<div class="view"><article class="post"><section class="page-head"><div class="wrap narrow">'
            f'<div class="crumbs"><a href="/">ראשי</a> / <a href="/blog/">בינה בתבונה</a></div>'
            f'<div class="eyebrow" style="color:var(--pink-soft)">{a["tag"]}</div><h1>{a["title"]}</h1></div>{WAVE}</section>'
            f'<div class="wrap narrow">{a["body"]}<a class="back" href="/blog/">→ לכל הטיפים</a></div></article></div>')
    write(f'/blog/{a["id"]}/', page(body, f'{a["title"]} · TomiZ', a['teaser'], f'/blog/{a["id"]}/', 'blog'))

urls = [p for p, *_ in PAGES.values()] + [f'/blog/{a["id"]}/' for a in ARTICLES]
open(os.path.join(ROOT, 'sitemap.xml'), 'w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(f'  <url><loc>{SITE}{u}</loc></url>\n' for u in urls) + '</urlset>\n')
open(os.path.join(ROOT, 'robots.txt'), 'w').write(('User-agent: *\nAllow: /\nSitemap: ' + SITE + '/sitemap.xml\n') if LIVE else 'User-agent: *\nDisallow: /\n')
print(('LIVE' if LIVE else 'DRAFT'), 'build:', len(urls), 'pages')
