"""Builds the static site from src/ into the repo root.

python3 build.py          -> draft build (draft banner, notes, noindex)
python3 build.py --live   -> production build
"""
import json, os, re, shutil, sys, urllib.parse
from html import escape as esc

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
    'home': ('/', 'TomiZ · AI שעובד בשבילך, לא להפך', 'ליווי אישי וכלי AI מעשיים לבעלי עסקים, עצמאים ומומחים: סוכנים, דשבורדים ואוטומציות שחוסכים עבודה שחורה, והפיכת הידע שלך לסדנה, קורס או הרצאה. ולארגונים: הטמעת AI והעברת ידע.', ''),
    'orgs': ('/orgs/', 'לארגונים · TomiZ', 'Unboxing, Train-the-Trainer, מיפוי פערי מיומנויות והטמעת AI לצוותי L&D ומשאבי אנוש.', 'orgs'),
    'experts': ('/experts/', 'לבעלי עסקים ומומחים · TomiZ', 'סוכני AI, דשבורדים ואוטומציות לעסק, וליווי שהופך את הידע שלך לסדנה, קורס או הרצאה.', 'experts'),
    'talks': ('/talks/', 'הרצאות · TomiZ', 'למידה שמחזיקה מים: הרצאה לכנסים, ימי עיון, צוותי הדרכה ומשאבי אנוש.', 'talks'),
    'about': ('/about/', 'אודות · TomiZ', 'שקד וולוז\'ינסקי לנס, מומחית LXD ו-AI, מנחת סדנאות ומרצה, מייסדת TomiZ.', 'about'),
    'blog': ('/blog/', 'משתמשים בבינה בתבונה · TomiZ', 'טיפים קצרים על AI, העברת ידע והדרכה, שאפשר ליישם כבר מחר בבוקר.', 'blog'),
    'ai-dictionary': ('/ai-dictionary/', 'מילון AI למומחים · TomiZ', '8 מונחים שכל מומחה ואיש מקצוע צריך להכיר, ואיך משתמשים בכל אחד כבר מחר בבוקר. מדריך חינמי.', ''),
    'privacy': ('/privacy/', 'מדיניות פרטיות · TomiZ', 'מדיניות הפרטיות של האתר tomizs.com.', ''),
    'accessibility': ('/accessibility/', 'הצהרת נגישות · TomiZ', 'הצהרת הנגישות של האתר tomizs.com.', ''),
}

EN_PAGES = {
    'home': ('/en/', 'TomiZ · AI that works for you, not the other way around', 'Practical AI adoption, workshops and training programs that turn expert knowledge into learning people actually apply. For organizations, L&D teams and experts.', ''),
    'orgs': ('/en/orgs/', 'For organizations · TomiZ', 'Unboxing, Train-the-Trainer, skills-gap analysis and AI adoption for L&D, HR and Customer Education teams.', 'orgs'),
    'experts': ('/en/experts/', 'For experts · TomiZ', 'Your knowledge can become a product: a workshop, course, digital product or any other format.', 'experts'),
    'talks': ('/en/talks/', 'Talks & workshops · TomiZ', 'Talks and workshops on learning, knowledge transfer and AI at work, for conferences, seminars and teams.', 'talks'),
    'about': ('/en/about/', 'About · TomiZ', 'Shaked Volozinski Lanes, LXD and AI specialist, workshop facilitator and speaker, founder of TomiZ.', 'about'),
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

# ---- TomiZ Club: sales page, thanks page and the members area (own sub-brand, always noindex, not in the sitemap) ----
CLUB = json.loads(read('club/club.json'))
import datetime as _dt
HEB_DAYS = ['שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת', 'ראשון']
HEB_MONTHS = ['ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני', 'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר']
M = CLUB['members_path']
WA = lambda text: 'https://wa.me/' + CLUB['wa_number'] + '?' + urllib.parse.urlencode({'text': text})
PAY = CLUB['pay_url'] or '#join'

def ev_times(e):
    d = _dt.date.fromisoformat(e['date']); h, m = map(int, e['start'].split(':'))
    start = _dt.datetime(d.year, d.month, d.day, h, m) - _dt.timedelta(hours=2)  # Israel winter time (UTC+2)
    return d, start, start + _dt.timedelta(minutes=e['minutes'])

def ev_gcal(e):
    _, s, t = ev_times(e)
    return 'https://calendar.google.com/calendar/render?' + urllib.parse.urlencode({
        'action': 'TEMPLATE', 'text': f'{e["title"]} · TomiZ Club', 'dates': f'{s:%Y%m%dT%H%M%SZ}/{t:%Y%m%dT%H%M%SZ}',
        'details': e['desc'] + ' הקישור ל-Teams נמצא באתר החברים.', 'location': 'Microsoft Teams', 'ctz': 'Asia/Jerusalem'})

def ev_card(e, nxt=False, add=True):
    d, *_ = ev_times(e)
    link = f'<a class="cl-ev-add" href="{ev_gcal(e)}" target="_blank" rel="noopener">+ ליומן</a>' if add else ''
    return (f'<div class="cl-ev{" next" if nxt else ""}"><div class="cl-ev-date"><b>{d.day}.{d.month}</b><small>יום {HEB_DAYS[d.weekday()]}</small></div>'
            f'<div><h3>{e["title"]}</h3><p>{e["start"]} · {e["minutes"]} דקות · Teams</p></div>{link}</div>')

def club_ics():
    esc = lambda t: t.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,')
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//TomiZ//Club//HE', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH']
    for e in CLUB['events']:
        _, s, t = ev_times(e)
        lines += ['BEGIN:VEVENT', f'UID:{e["id"]}@club.tomizs.com', 'DTSTAMP:20261120T000000Z', f'DTSTART:{s:%Y%m%dT%H%M%SZ}', f'DTEND:{t:%Y%m%dT%H%M%SZ}',
                  f'SUMMARY:{esc(e["title"] + " · TomiZ Club")}', f'DESCRIPTION:{esc(e["desc"])}', 'LOCATION:Microsoft Teams', f'URL:{SITE}{M}',
                  'BEGIN:VALARM', 'ACTION:DISPLAY', 'DESCRIPTION:מפגש TomiZ Club בעוד 30 דקות', 'TRIGGER:-PT30M', 'END:VALARM', 'END:VEVENT']
    lines.append('END:VCALENDAR')
    def fold(line):  # RFC 5545: lines of at most 75 octets
        out, cur = [], b''
        for ch in line:
            c = ch.encode('utf-8')
            if len(cur) + len(c) > (75 if not out else 74):
                out.append(cur); cur = b''
            cur += c
        return b'\r\n '.join(out + [cur]).decode('utf-8')
    return '\r\n'.join(fold(l) for l in lines) + '\r\n'

def month_table(y, m):
    evs = {e['date'] for e in CLUB['events']}
    first = _dt.date(y, m, 1); lead = (first.weekday() + 1) % 7  # weeks start on Sunday
    days = (_dt.date(y + (m == 12), m % 12 + 1, 1) - first).days
    cells = [''] * lead + list(range(1, days + 1)); cells += [''] * (-len(cells) % 7)
    rows = ''
    for i in range(0, len(cells), 7):
        tds = ''
        for c in cells[i:i + 7]:
            if c == '':
                tds += '<td></td>'; continue
            iso = f'{y}-{m:02d}-{c:02d}'
            cls = ' class="ev"' if iso in evs else (' class="launch"' if iso == CLUB['launch'] else '')
            tds += f'<td{cls}><span>{c}</span></td>'
        rows += f'<tr>{tds}</tr>'
    head = ''.join(f'<th>{d}</th>' for d in 'אבגדהוש')
    return f'<table class="clm-cal"><caption>{HEB_MONTHS[m - 1]} {y}</caption><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>'

STAMP = ('<svg class="cl-stamp" viewBox="0 0 120 120"><defs><path id="clr" d="M60 60m-44 0a44 44 0 1 1 88 0a44 44 0 1 1-88 0"/></defs>'
         '<circle cx="60" cy="60" r="58" fill="#E94E77"/><circle cx="60" cy="60" r="34" fill="none" stroke="#fff" stroke-width="1.5" stroke-dasharray="2 4"/>'
         '<text direction="ltr" fill="#fff" font-family="Rubik,sans-serif" font-size="11" font-weight="700" letter-spacing="1.5"><textPath href="#clr">TOMIZ CLUB • FOUNDING MEMBER • 2026 •</textPath></text>'
         '<text direction="ltr" unicode-bidi="bidi-override" x="60" y="68" text-anchor="middle" fill="#fff" font-family="Secular One,Rubik,sans-serif" font-size="24">69₪</text></svg>')
TOP = '<div class="cl-top"><a class="cl-lock" href="/club/" aria-label="TomiZ Club"><img src="/assets/logo_dark.png" width="88" height="26" alt="TomiZ"><b>Club</b></a><a class="cl-ask" href="{{WA_ASK}}" target="_blank" rel="noopener">שאלה? וואטסאפ</a></div>'
FOOT = '<footer class="cl-foot"><div class="wrap"><img src="/assets/logo_light.png" width="82" height="24" alt="TomiZ" loading="lazy"><span>TomiZ Club הוא קהילה של TomiZ · <a href="/">tomizs.com</a> · <a href="/club/terms/">תקנון וביטולים</a> · <a href="/privacy/">מדיניות פרטיות</a> · <a href="/accessibility/">הצהרת נגישות</a></span></div></footer>'

def sales_page(body, title, desc, path, members=None):
    banner = '' if LIVE else '<div class="draft">טיוטה לעיון · לא באוויר</div>\n'
    hook = f'<script>window.TOMIZ_WEBHOOK={json.dumps(WEBHOOK)}</script>\n' if WEBHOOK else ''
    pixel = META_PIXEL if (LIVE and members is None) else ''
    if members is not None:
        tabs = [('', 'בית'), ('recordings/', 'הדרכות מוקלטות'), ('guides/', 'מדריכים'), ('perks/', 'הטבות וקביעת פגישה')]
        nav = ''.join(f'<a href="{M}{p}"{" aria-current=\"page\"" if p == members else ""}>{t}</a>' for p, t in tabs)
        body = (f'<header class="clm-head" style="position:static;box-shadow:none"><div class="wrap"><div class="cl-top"><a class="cl-lock" href="{M}" aria-label="TomiZ Club">'
                f'<img src="/assets/logo_light.png" width="88" height="26" alt="TomiZ"><b>Club</b></a><span style="font-size:14px;opacity:.8">אזור החברים</span></div>'
                f'<nav class="clm-nav" aria-label="אזור החברים">{nav}</nav></div></header>\n<main id="main" tabindex="-1">{body}</main>\n{FOOT}')
    else:
        body = f'<main id="main" tabindex="-1">\n{body}\n</main>'
    events = CLUB['events']
    rep = {
        '{{TOP}}': TOP, '{{FOOT}}': FOOT, '{{STAMP}}': STAMP, '{{PAY}}': PAY, '{{M}}': M, '{{MEMBERS}}': M,
        '{{EVENTS}}': ''.join(ev_card(e, i == 0) for i, e in enumerate(events)),
        '{{EVENTS_SHORT}}': ', '.join(f'{ev_times(e)[0].day}.{ev_times(e)[0].month}' for e in events[:-1]) + f' ו-{ev_times(events[-1])[0].day}.{ev_times(events[-1])[0].month}, בשעה {events[0]["start"]}',
        '{{ICS_ALL}}': '/files/tomiz-club-events.ics', '{{BOOK}}': CLUB['book_url'],
        '{{WA_GROUP}}': CLUB['wa_group'] or '#', '{{WA_ASK}}': WA('היי שקד, יש לי שאלה על TomiZ Club'),
        '{{WA_BOOK}}': WA('היי שקד, אני מ-TomiZ Club ורוצה לקבוע פגישה'),
    }
    if '{{NEXT}}' in body:
        e = events[0]; d, *_ = ev_times(e)
        zoom = f'<a class="cl-btn" href="{CLUB["teams_url"]}" target="_blank" rel="noopener">כניסה ל-Teams</a>' if CLUB['teams_url'] else '<span class="cl-btn" style="opacity:.6;cursor:default">קישור ה-Teams יופיע כאן</span>'
        rep['{{NEXT}}'] = (f'<div class="clm-box clm-next"><p class="cl-eye">המפגש הבא</p><h2>{e["title"]}</h2>'
                           f'<p class="when">יום {HEB_DAYS[d.weekday()]}, {d.day}.{d.month}.{d.year} · {e["start"]}</p><p>{e["desc"]}</p>'
                           f'<div class="row">{zoom}<a class="cl-btn line" style="color:#fff;border-color:rgba(255,255,255,.6)" href="{ev_gcal(e)}" target="_blank" rel="noopener">+ ליומן</a></div></div>')
    if '{{CALS}}' in body:
        months = sorted({(int(x[:4]), int(x[5:7])) for x in [CLUB['launch']] + [e['date'] for e in events]})
        rep['{{CALS}}'] = ''.join(month_table(y, m) for y, m in months)
    if '{{RECS}}' in body:
        done = ''.join(f'<a class="clm-card" href="{r["url"]}" target="_blank" rel="noopener"><div class="thumb"><span class="play"></span></div><div class="body"><span class="kind">הקלטה · {r["date"]}</span><h3>{r["title"]}</h3><p>{r.get("desc", "")}</p></div></a>' for r in CLUB['recordings'])
        recorded = {r.get('event') for r in CLUB['recordings']}
        soon = ''.join(f'<div class="clm-card"><div class="thumb soon">בקרוב</div><div class="body"><span class="kind">יעלה אחרי {ev_times(e)[0].day}.{ev_times(e)[0].month}</span><h3>{e["title"]}</h3><p>{e["desc"]}</p></div></div>' for e in events if e['id'] not in recorded)
        rep['{{RECS}}'] = done + soon
    if '{{GUIDES}}' in body:
        rep['{{GUIDES}}'] = ''.join(f'<a class="clm-card" href="{g["url"]}" target="_blank" rel="noopener"><div class="thumb">{g["title"]}</div><div class="body"><span class="kind">{g["kind"]}</span><h3>{g["title"]}</h3><p>{g["desc"]}</p><span class="open">לפתיחה ←</span></div></a>' for g in CLUB['guides'])
    for k, v in rep.items():
        body = body.replace(k, v)
    for k, v in rep.items():  # TOP/FOOT carry placeholders of their own
        body = body.replace(k, v)
    html = f'''<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="robots" content="noindex,nofollow">
<meta name="color-scheme" content="light">
<meta name="theme-color" content="{'#2D5A52' if members is not None else '#FCE6EC'}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{SITE}{path}">
<meta property="og:image" content="{SITE}/assets/og.png">
<meta property="og:locale" content="he_IL">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;700;800&family=Secular+One&display=swap">
<link rel="stylesheet" href="/assets/site.css">
<link rel="stylesheet" href="/assets/club.css">
{pixel}</head>
<body class="cl">
<a class="skip" href="#main">דילוג לתוכן</a>
{banner}{body}
{hook}<script>window.TOMIZ_CLUB={json.dumps({'price': CLUB.get('price', 69), 'pass_params': CLUB.get('pay_pass_params', False)})}</script>
<script src="/assets/club.js" defer></script>
</body>
</html>
'''
    return strip_draft(html)

CLUB_DESC = 'קהילה לבעלי עסקים: מפגש לייב כל שבועיים, אתר חברים עם כלים מוכנים וקבוצת וואטסאפ לליווי. מחיר מייסדים 69 ₪ לחודש.'
write('/club/', sales_page(read('club/landing.html'), 'TomiZ Club · המקום שבו ה-AI מתחיל לעבוד בשבילכם', CLUB_DESC, '/club/'))
write('/club/terms/', sales_page(read('club/terms.html'), 'תקנון ומדיניות ביטול · TomiZ Club', 'תנאי ההצטרפות, החיוב והביטול של TomiZ Club.', '/club/terms/'))
write('/club/thanks/', sales_page(read('club/thanks.html'), 'ברוכים הבאים · TomiZ Club', 'ההצטרפות ל-TomiZ Club התקבלה.', '/club/thanks/'))
os.makedirs(os.path.join(ROOT, 'files'), exist_ok=True)
open(os.path.join(ROOT, 'files/tomiz-club-events.ics'), 'w', encoding='utf-8', newline='').write(club_ics())
# ---- club members area: /club/login/ and /club/account/ (no site nav, always noindex, not in the sitemap) ----
# Draft until approved: a draft banner shows even in a --live build. The auth endpoint (src/club-members/endpoint.txt or
# TOMIZ_CLUB_AUTH) is a server that checks members and sends login codes; with none set the pages run in demo mode.
CLUB_DRAFT = True
CLUB_AUTH = os.environ.get('TOMIZ_CLUB_AUTH', '') or (read('club-members/endpoint.txt').strip() if os.path.exists(os.path.join(SRC, 'club-members/endpoint.txt')) else '')
CLUB_PAGES = {
    'login': ('/club/login/', 'כניסה לאזור החברות · TomiZ Club', 'כניסה לאזור החברות של TomiZ Club.'),
    'home': ('/club/home/', 'בית · TomiZ Club', 'דף הבית של חברות TomiZ Club.'),
    'recordings': ('/club/recordings/', 'הקלטות · TomiZ Club', 'הקלטות המפגשים והוובינרים של TomiZ Club.'),
    'guides': ('/club/guides/', 'מדריכים · TomiZ Club', 'המדריכים והתבניות של TomiZ Club.'),
    'prompts': ('/club/prompts/', 'פרומפטים מומלצים · TomiZ Club', 'פרומפטים מומלצים לחברות TomiZ Club.'),
    'tips': ('/club/tips/', 'טיפים · TomiZ Club', 'טיפים קצרים לחברות TomiZ Club.'),
    'account': ('/club/account/', 'האזור שלי · TomiZ Club', 'האזור האישי של חברות TomiZ Club.'),
}
CLUB_NAV = [('home', 'בית'), ('recordings', 'הקלטות'), ('guides', 'מדריכים'), ('prompts', 'פרומפטים'), ('tips', 'טיפים')]
# intro of each content page: (eyebrow, h1 with <mark>, lead, one-line pitch for the home page tile)
CLUB_SECTIONS = {
    'recordings': ('הקלטות', 'כל המפגשים, <mark>מתי שנוח לך</mark>', '[משפט פתיחה: מה יש כאן ואיך כדאי לצפות]', 'כל המפגשים והוובינרים, מהחדש לישן.'),
    'guides': ('מדריכים', 'מדריכים ש<mark>חוסכים זמן</mark>', '[משפט פתיחה: אילו מדריכים ותבניות יש כאן]', 'מדריכים, תבניות וצ\'קליסטים להורדה.'),
    'prompts': ('פרומפטים מומלצים', 'פרומפטים <mark>מוכנים להעתקה</mark>', '[משפט פתיחה: איך משתמשים בפרומפטים, ומה ממלאים בסוגריים]', 'מעתיקות, ממלאות את הסוגריים ומדביקות.'),
    'tips': ('טיפים', 'טיפ קטן, <mark>הבדל גדול</mark>', '[משפט פתיחה: כל כמה זמן עולה טיפ חדש]', 'טיפים קצרים שאפשר ליישם היום.'),
}
CLUB_CONTENT = json.loads(read('club-members/content.json'))
def ph(text):
    """Escape, and show [square bracket] text as a visible placeholder."""
    t = esc(text or '')
    return re.sub(r'\[([^\[\]]*)\]', r'<span class="ph">[\1]</span>', t)
def club_card(kind, it):
    h = 'h3'
    if kind == 'recordings':
        meta = ' · '.join(ph(x) for x in (it.get('date'), it.get('length')) if x)
        return (f'<article class="cm-item"><span class="cm-chip">{ph(it.get("topic"))}</span><{h}>{ph(it["title"])}</{h}>'
                f'<p class="cm-meta">{meta}</p><p>{ph(it.get("desc"))}</p>'
                f'<a class="wb-btn ghost cm-go" data-href="{esc(it["key"])}" data-soon="ההקלטה תעלה בקרוב" target="_blank" rel="noopener">לצפייה בהקלטה</a></article>')
    if kind == 'guides':
        link = (f'<a class="wb-btn ghost cm-go" href="{esc(it["url"])}">לפתיחת המדריך</a>' if it.get('url')
                else '<span class="cm-soon">בקרוב</span>')
        return (f'<article class="cm-item"><span class="cm-chip">{ph(it.get("type"))}</span><{h}>{ph(it["title"])}</{h}>'
                f'<p>{ph(it.get("desc"))}</p>{link}</article>')
    if kind == 'prompts':
        body = (f'<pre class="cm-prompt" dir="auto">{ph(it.get("text"))}</pre>'
                                 f'<button class="wb-btn ghost cm-copy" type="button">העתקת הפרומפט</button>')
        return (f'<article class="cm-item"><span class="cm-chip">{ph(it.get("tool"))}</span><{h}>{ph(it["title"])}</{h}>'
                f'<p>{ph(it.get("use"))}</p>{body}</article>')
    if kind == 'tips':
        return (f'<article class="cm-item cm-tip"><p class="cm-meta">{ph(it.get("date"))}</p><{h}>{ph(it["title"])}</{h}>'
                f'<p>{ph(it.get("text"))}</p></article>')
def club_section(kind):
    eyebrow, h1, lead, _ = CLUB_SECTIONS[kind]
    items = '\n'.join(club_card(kind, it) for it in CLUB_CONTENT[kind])
    return (f'<section class="cm-head"><div class="wrap"><p class="wb-eyebrow">{eyebrow}</p><h1 class="cm-h1">{h1}</h1>'
            f'<p class="cm-lead">{ph(lead)}</p></div></section>\n'
            f'<section class="wb-sec cm-list"><div class="wrap"><div class="cm-grid{" one" if kind == "prompts" else ""}">\n{items}\n</div></div></section>')
def club_home():
    body = read('club-members/home.html')
    latest = [('recordings', 'הקלטה חדשה'), ('prompts', 'פרומפט חדש'), ('tips', 'טיפ חדש')]
    def teaser(k, lbl):
        it = CLUB_CONTENT[k][0]
        line = it.get('desc') or it.get('use') or it.get('text')
        return (f'<a class="cm-item cm-tile" href="{CLUB_PAGES[k][0]}"><span class="cm-chip pink">{lbl}</span>'
                f'<h3>{ph(it["title"])}</h3><p>{ph(line)}</p></a>')
    new = '\n'.join(teaser(k, lbl) for k, lbl in latest if CLUB_CONTENT[k])
    secs = '\n'.join(f'<a class="cm-item cm-tile" href="{CLUB_PAGES[k][0]}"><span class="wb-num">{len(CLUB_CONTENT[k])}</span>'
                     f'<h3>{CLUB_SECTIONS[k][0]}</h3><p>{CLUB_SECTIONS[k][3]}</p></a>' for k in CLUB_SECTIONS)
    return body.replace('{{new}}', new).replace('{{sections}}', secs)
def club_nav(current):
    items = ''.join(f'<a href="{CLUB_PAGES[k][0]}"{" aria-current=\"page\"" if k == current else ""}>{label}</a>' for k, label in CLUB_NAV)
    me = ' aria-current="page"' if current == 'account' else ''
    return (f'<header class="cm-bar"><div class="wrap"><a class="cm-brand" href="/club/home/"><img src="/assets/logo_light.png" width="102" height="30" alt="TomiZ"><span>Club</span></a>'
            f'<a class="cm-me" href="/club/account/"{me}><span class="cm-avatar" data-f="initial" aria-hidden="true"></span>האזור שלי</a></div>'
            f'<nav class="cm-nav" aria-label="ניווט במועדון"><div class="wrap">{items}</div></nav></header>\n')
CLUB_FOOT = '<footer class="wb-foot"><div class="wrap"><img src="/assets/logo_light.png" width="102" height="30" alt="TomiZ" loading="lazy"><span>© TomiZ · <a href="/club/terms/" target="_blank" rel="noopener">תקנון וביטולים</a> · <a href="/privacy/" target="_blank" rel="noopener">מדיניות פרטיות</a> · <a href="/accessibility/" target="_blank" rel="noopener">הצהרת נגישות</a></span></div></footer>'
def club_page(body, title, desc, name):
    banner = '<div class="draft">טיוטה לעיון · לא באוויר</div>\n' if CLUB_DRAFT or not LIVE else ''
    if name != 'login':  # member pages: shared nav, content shown only after the endpoint confirms an active member
        body = (club_nav(name) + '<div class="cm-loading" id="cm-loading" role="status">טוענים את המועדון...</div>\n'
                f'<div id="cm-app" hidden>\n{body}\n</div>\n{CLUB_FOOT}')
    return f'''<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="robots" content="noindex,nofollow">
<meta name="theme-color" content="#1E3E38">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;700;800;900&display=swap">
<link rel="stylesheet" href="/assets/site.css">
<link rel="stylesheet" href="/assets/webinar.css">
<link rel="stylesheet" href="/assets/club-members.css">
</head>
<body class="wb cm cm-{name}">
<a class="skip" href="#main">דילוג לתוכן</a>
{banner}<main id="main" tabindex="-1">
{body}
</main>
<script>window.TOMIZ_CLUB_AUTH={json.dumps(CLUB_AUTH)}</script>
<script src="/assets/club-members.js" defer></script>
</body>
</html>
'''
for name, (path, title, desc) in CLUB_PAGES.items():
    body = club_home() if name == 'home' else club_section(name) if name in CLUB_SECTIONS else read(f'club-members/{name}.html')
    write(path, club_page(body, title, desc, name))

urls = ([p for p, *_ in PAGES.values()] + [p for p, *_ in EN_PAGES.values()]
        + [f'/blog/{a["id"]}/' for a in ARTICLES] + [f'/en/blog/{a["id"]}/' for a in ARTICLES_EN])
open(os.path.join(ROOT, 'sitemap.xml'), 'w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(f'  <url><loc>{SITE}{u}</loc></url>\n' for u in urls) + '</urlset>\n')
open(os.path.join(ROOT, 'robots.txt'), 'w').write(('User-agent: *\nAllow: /\nSitemap: ' + SITE + '/sitemap.xml\n') if LIVE else 'User-agent: *\nDisallow: /\n')
print(('LIVE' if LIVE else 'DRAFT'), 'build:', len(urls), 'pages')
