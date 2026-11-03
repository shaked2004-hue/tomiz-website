"""Builds the static site from src/ into the repo root.

python3 build.py          -> draft build (draft banner, notes, noindex)
python3 build.py --live   -> production build
"""
import json, os, re, shutil, sys, urllib.parse

LIVE = '--live' in sys.argv
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'src')
SITE = 'https://tomizs.com'
META_PIXEL_ID = '1639309097614341'
META_PIXEL = f'''<!-- Meta Pixel Code -->
<script>
!function(f,b,e,v,n,t,s)
{{if(f.fbq)return;n=f.fbq=function(){{n.callMethod?
n.callMethod.apply(n,arguments):n.queue.push(arguments)}};
if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
n.queue=[];t=b.createElement(e);t.async=!0;
t.src=v;s=b.getElementsByTagName(e)[0];
s.parentNode.insertBefore(t,s)}}(window, document,'script',
'https://connect.facebook.net/en_US/fbevents.js');
fbq('init', '{META_PIXEL_ID}');
fbq('track', 'PageView');
</script>
<noscript><img height="1" width="1" style="display:none"
src="https://www.facebook.com/tr?id={META_PIXEL_ID}&ev=PageView&noscript=1"
/></noscript>
<!-- End Meta Pixel Code -->
'''
WEBHOOK = os.environ.get('TOMIZ_WEBHOOK', open(os.path.join(SRC, 'webhook.txt')).read().strip() if os.path.exists(os.path.join(SRC, 'webhook.txt')) else '')

read = lambda p: open(os.path.join(SRC, p), encoding='utf-8').read()
ARTICLES = json.loads(read('articles.json'))
ARTICLES_EN = json.loads(read('en/articles.json'))

# page name -> (url path, title, description, nav key)
PAGES = {
    'home': ('/', 'TomiZ · עיצוב למידה והעברת ידע', 'סדנאות, תהליכי הדרכה והרצאות מעשיות על AI, למידה והעברת ידע, לארגונים, לקהילות ולבעלי מקצוע.', ''),
    'orgs': ('/orgs/', 'לארגונים · TomiZ', 'Unboxing, Train-the-Trainer, מיפוי פערי מיומנויות והטמעת AI לצוותי L&D ומשאבי אנוש.', 'orgs'),
    'experts': ('/experts/', 'למומחים · TomiZ', 'הידע שלך יכול להפוך למוצר: סדנה, קורס, מוצר דיגיטלי או כל פורמט אחר.', 'experts'),
    'talks': ('/talks/', 'הרצאות · TomiZ', 'למידה שמחזיקה מים: הרצאה לכנסים, ימי עיון, צוותי הדרכה ומשאבי אנוש.', 'talks'),
    'about': ('/about/', 'אודות · TomiZ', 'שקד וולוז\'ינסקי לנס, מעצבת חוויות למידה, מנחת סדנאות ומרצה, מייסדת TomiZ.', 'about'),
    'blog': ('/blog/', 'משתמשים בבינה בתבונה · TomiZ', 'טיפים קצרים על AI, העברת ידע והדרכה, שאפשר ליישם כבר מחר בבוקר.', 'blog'),
    'ai-dictionary': ('/ai-dictionary/', 'מילון AI למומחים · TomiZ', '8 מונחים שכל מומחה ואיש מקצוע צריך להכיר, ואיך משתמשים בכל אחד כבר מחר בבוקר. מדריך חינמי.', ''),
    'privacy': ('/privacy/', 'מדיניות פרטיות · TomiZ', 'מדיניות הפרטיות של האתר tomizs.com.', ''),
    'accessibility': ('/accessibility/', 'הצהרת נגישות · TomiZ', 'הצהרת הנגישות של האתר tomizs.com.', ''),
}

EN_PAGES = {
    'home': ('/en/', 'TomiZ · Learning design & knowledge transfer', 'Practical workshops, training programs and talks on AI, learning and knowledge transfer, for organizations, communities and professionals.', ''),
    'orgs': ('/en/orgs/', 'For organizations · TomiZ', 'Unboxing, Train-the-Trainer, skills-gap analysis and AI adoption for L&D, HR and Customer Education teams.', 'orgs'),
    'experts': ('/en/experts/', 'For experts · TomiZ', 'Your knowledge can become a product: a workshop, course, digital product or any other format.', 'experts'),
    'talks': ('/en/talks/', 'Talks & workshops · TomiZ', 'Talks and workshops on learning, knowledge transfer and AI at work, for conferences, seminars and teams.', 'talks'),
    'about': ('/en/about/', 'About · TomiZ', 'Shaked Volozinski Lanes, learning experience designer, workshop facilitator and speaker, founder of TomiZ.', 'about'),
    'blog': ('/en/blog/', 'Using AI wisely · TomiZ', 'Short tips on AI, knowledge transfer and training that you can apply tomorrow morning.', 'blog'),
    'privacy': ('/en/privacy/', 'Privacy policy · TomiZ', 'The privacy policy of tomizs.com.', ''),
    'accessibility': ('/en/accessibility/', 'Accessibility statement · TomiZ', 'The accessibility statement of tomizs.com.', ''),
}

def links(html, lang='he'):
    pages = EN_PAGES if lang == 'en' else PAGES
    pre = '/en' if lang == 'en' else ''
    html = re.sub(r'href="#a-([\w-]+)"', rf'href="{pre}/blog/\1/"', html)
    html = html.replace('href="#home"', f'href="{pre}/"')
    for name, (path, *_) in pages.items():
        html = html.replace(f'href="#{name}"', f'href="{path}"')
    return html

def other(path):
    """The same page in the other language (falls back to that language's home)."""
    if path.startswith('/en/'):
        he = path[3:]
        return he if he in [p for p, *_ in PAGES.values()] or he.startswith('/blog/') else '/'
    en = '/en' + path
    return en if en in [p for p, *_ in EN_PAGES.values()] or path.startswith('/blog/') else '/en/'

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

def card(a, lang='he'):
    pre, go = ('/en', 'Read →') if lang == 'en' else ('', 'לקריאה ←')
    return (f'<a class="card reveal" href="{pre}/blog/{a["id"]}/"><span class="tag">{a["tag"]}</span>'
            f'<h3>{a["title"]}</h3><p>{a["teaser"]}</p><span class="go">{go}</span></a>')

def page(body, title, desc, path, nav, lang='he', image='/assets/og.png'):
    en = lang == 'en'
    d = 'en/' if en else ''
    alt = other(path)
    header = read(d + 'header.html').replace('{{HE_URL}}', alt).replace('href="#en"', f'href="{alt}"')
    if nav:
        header = header.replace(f'data-nav="{nav}"', f'data-nav="{nav}" aria-current="page"')
    banner = '' if LIVE else f'<div class="draft">{"Draft for review · not live" if en else "טיוטה לעיון · לא באוויר"}</div>\n'
    robots = '' if LIVE else '<meta name="robots" content="noindex,nofollow">\n'
    hook = f'<script>window.TOMIZ_WEBHOOK={json.dumps(WEBHOOK)}</script>\n' if WEBHOOK else ''
    pixel = META_PIXEL if LIVE else ''
    html = f'''<!doctype html>
<html lang="{lang}" dir="{'ltr' if en else 'rtl'}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{title}</title>
<meta name="description" content="{desc}">
{robots}<link rel="canonical" href="{SITE}{path}">
<link rel="alternate" hreflang="{'he' if en else 'en'}" href="{SITE}{alt}">
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
{pixel}</head>
<body id="top">
<a class="skip" href="#main">{"Skip to content" if en else "דילוג לתוכן"}</a>
{banner}{header}
<main id="main" tabindex="-1">
{body}
</main>
{read(d + 'contact.html')}
{read(d + 'footer.html')}
{hook}<script src="/assets/site.js" defer></script>
</body>
</html>
'''
    return strip_draft(links(html, lang))

def write(path, html):
    out = os.path.join(ROOT, path.strip('/'), 'index.html') if path != '/' else os.path.join(ROOT, 'index.html')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w', encoding='utf-8').write(html)

WAVE = '<svg class="wave" viewBox="0 0 1440 56" preserveAspectRatio="none" aria-hidden="true" style="color:var(--bg)"><path fill="currentColor" d="M0 56V28C240 0 480 0 720 22s480 34 720 6v28z"/></svg>'

for name, (path, title, desc, nav) in PAGES.items():
    body = read(f'pages/{name}.html')
    body = body.replace('<div class="articles" id="home-articles"></div>', '<div class="articles">' + ''.join(card(a) for a in ARTICLES[:3]) + '</div>')
    body = body.replace('<div class="articles" id="all-articles"></div>', '<div class="articles">' + ''.join(card(a) for a in ARTICLES) + '</div>')
    write(path, page(body, title, desc, path, nav, 'he',
                     '/assets/ai-dictionary-cover.jpg' if name == 'ai-dictionary' else '/assets/og.png'))

for name, (path, title, desc, nav) in EN_PAGES.items():
    body = read(f'en/pages/{name}.html')
    body = body.replace('<div class="articles" id="home-articles"></div>', '<div class="articles">' + ''.join(card(a, 'en') for a in ARTICLES_EN[:3]) + '</div>')
    body = body.replace('<div class="articles" id="all-articles"></div>', '<div class="articles">' + ''.join(card(a, 'en') for a in ARTICLES_EN) + '</div>')
    write(path, page(body, title, desc, path, nav, 'en'))

ART = {'he': ('', 'ראשי', 'בינה בתבונה', '→ לכל הטיפים'), 'en': ('/en', 'Home', 'Smart AI', '← All tips')}
for lang, arts in (('he', ARTICLES), ('en', ARTICLES_EN)):
    pre, home, crumb, back = ART[lang]
    for a in arts:
        body = (f'<div class="view"><article class="post"><section class="page-head"><div class="wrap narrow">'
                f'<div class="crumbs"><a href="{pre}/">{home}</a> / <a href="{pre}/blog/">{crumb}</a></div>'
                f'<div class="eyebrow" style="color:var(--pink-soft)">{a["tag"]}</div><h1>{a["title"]}</h1></div>{WAVE}</section>'
                f'<div class="wrap narrow">{a["body"]}<a class="back" href="{pre}/blog/">{back}</a></div></article></div>')
        p = f'{pre}/blog/{a["id"]}/'
        write(p, page(body, f'{a["title"]} · TomiZ', a['teaser'], p, 'blog', lang))

# ---- webinar campaign: standalone landing + thanks pages (no site nav/contact/footer, always noindex, not in the sitemap) ----
# Webinar sign-ups go to the site's lead webhook (source = the webinar name) unless TOMIZ_WEBINAR_WEBHOOK or src/webinar/webhook.txt sets another
WEBINAR_WEBHOOK = os.environ.get('TOMIZ_WEBINAR_WEBHOOK', '') or (read('webinar/webhook.txt').strip() if os.path.exists(os.path.join(SRC, 'webinar/webhook.txt')) else '') or WEBHOOK
WEBINAR = {
    'title': 'תפסיקו לעבוד בשביל ה-AI',
    'start': '20261201T080000Z', 'end': '20261201T090000Z',  # Tue 1.12.2026, 10:00-11:00 Israel time (UTC+2)
    'details': 'וובינר חינם בזום עם שקד וולוז\'ינסקי (TomiZ): ייעול תהליכים בעסק עם AI. הקישור לזום יישלח במייל ב-24.11.2026. בואו עם משימה אחת בעסק שאתם רוצים להשתחרר ממנה.',
    'location': 'Zoom (הקישור יישלח במייל)',
    'ics': '/files/tomiz-webinar-2026-12-01.ics',
}
WEBINAR_PAGES = {
    'landing': ('/webinar/', 'תפסיקו לעבוד בשביל ה-AI · וובינר חינם · TomiZ', 'וובינר חינם בזום, 1.12 ב-10:00: איך גורמים ל-AI לעבוד בשבילכם, לא להפך. מראים הכול על המסך, בזמן אמת ובלי מילים גבוהות.'),
    'thanks': ('/webinar/thanks/', 'נרשמתם! · תפסיקו לעבוד בשביל ה-AI · TomiZ', 'ההרשמה לוובינר התקבלה.'),
}
GCAL = 'https://calendar.google.com/calendar/render?' + urllib.parse.urlencode({
    'action': 'TEMPLATE', 'text': f'{WEBINAR["title"]} · וובינר TomiZ', 'dates': f'{WEBINAR["start"]}/{WEBINAR["end"]}',
    'details': WEBINAR['details'], 'location': WEBINAR['location'], 'ctz': 'Asia/Jerusalem'})

def ics():
    def fold(line):  # RFC 5545: lines of at most 75 octets, continued with CRLF + space
        out, cur = [], b''
        for ch in line:
            c = ch.encode('utf-8')
            if len(cur) + len(c) > (75 if not out else 74):
                out.append(cur); cur = b''
            cur += c
        return b'\r\n '.join(out + [cur]).decode('utf-8')
    esc = lambda t: t.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,')
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//TomiZ//Webinar//HE', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH',
             'BEGIN:VEVENT', 'UID:webinar-2026-12-01@tomizs.com', 'DTSTAMP:20261103T000000Z',
             f'DTSTART:{WEBINAR["start"]}', f'DTEND:{WEBINAR["end"]}',
             f'SUMMARY:{esc(WEBINAR["title"] + " · וובינר TomiZ")}', f'DESCRIPTION:{esc(WEBINAR["details"])}',
             f'LOCATION:{esc(WEBINAR["location"])}', f'URL:{SITE}/webinar/',
             'BEGIN:VALARM', 'ACTION:DISPLAY', 'DESCRIPTION:הוובינר של TomiZ מתחיל בעוד 30 דקות', 'TRIGGER:-PT30M', 'END:VALARM',
             'END:VEVENT', 'END:VCALENDAR']
    return '\r\n'.join(fold(l) for l in lines) + '\r\n'

def landing(body, title, desc, path):
    banner = '' if LIVE else '<div class="draft">טיוטה לעיון · לא באוויר</div>\n'
    hook = f'<script>window.TOMIZ_WEBINAR_WEBHOOK={json.dumps(WEBINAR_WEBHOOK)}</script>\n'
    pixel = META_PIXEL if LIVE else ''
    html = f'''<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="robots" content="noindex,nofollow">
<meta name="theme-color" content="#1E3E38">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{SITE}{path}">
<meta property="og:image" content="{SITE}/assets/og.png">
<meta property="og:locale" content="he_IL">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;700;800;900&display=swap">
<link rel="stylesheet" href="/assets/site.css">
<link rel="stylesheet" href="/assets/webinar.css">
{pixel}</head>
<body class="wb">
<a class="skip" href="#main">דילוג לתוכן</a>
{banner}<main id="main" tabindex="-1">
{body}
</main>
{hook}<script src="/assets/webinar.js" defer></script>
</body>
</html>
'''
    return strip_draft(html.replace('{{GCAL}}', GCAL.replace('&', '&amp;')).replace('{{ICS}}', WEBINAR['ics']))

for name, (path, title, desc) in WEBINAR_PAGES.items():
    write(path, landing(read(f'webinar/{name}.html'), title, desc, path))
open(os.path.join(ROOT, WEBINAR['ics'].strip('/')), 'w', encoding='utf-8', newline='').write(ics())

urls = ([p for p, *_ in PAGES.values()] + [p for p, *_ in EN_PAGES.values()]
        + [f'/blog/{a["id"]}/' for a in ARTICLES] + [f'/en/blog/{a["id"]}/' for a in ARTICLES_EN])
open(os.path.join(ROOT, 'sitemap.xml'), 'w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(f'  <url><loc>{SITE}{u}</loc></url>\n' for u in urls) + '</urlset>\n')
open(os.path.join(ROOT, 'robots.txt'), 'w').write(('User-agent: *\nAllow: /\nSitemap: ' + SITE + '/sitemap.xml\n') if LIVE else 'User-agent: *\nDisallow: /\n')
print(('LIVE' if LIVE else 'DRAFT'), 'build:', len(urls), 'pages')
