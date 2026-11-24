// Club members area: passwordless login (email -> one-time code) and the "my account" page.
// All member data and private links (Zoom, WhatsApp, recordings) come from the auth endpoint, never from this file,
// so the static pages hold nothing worth sharing. The endpoint is set in build.py (CLUB_AUTH_ENDPOINT).
//
// Endpoint contract (form-encoded POST, JSON reply; see docs/club-members.md):
//   action=request-code  email                 -> {ok:true}                      (always ok, so emails can't be probed)
//   action=verify        email, code           -> {ok:true, token} | {ok:false, error:'bad-code'|'expired'|'inactive'}
//   action=me            token                 -> {ok:true, member:{...}, club:{...}} | {ok:false, error:'auth'}
//   action=update        token, name, phone, business -> {ok:true}
//   action=logout        token                 -> {ok:true}
// With no endpoint set, the pages run in demo mode with sample data (code 123456) and say so on screen.
const API = window.TOMIZ_CLUB_AUTH || '';
const DEMO = !API;
const KEY = 'tomiz-club-session';
const LOGIN = '/club/login/', HOME = '/club/home/';
const T = {
  email: 'נא למלא כתובת אימייל תקינה, למשל ⁦name@gmail.com⁩.',
  code: 'הקוד הוא 6 ספרות. אפשר להדביק אותו מהמייל.',
  badCode: 'הקוד לא נכון. בדקי שהעתקת את הקוד מהמייל האחרון.',
  expired: 'הקוד פג תוקף. שלחי לעצמך קוד חדש.',
  inactive: 'לא מצאנו מנוי פעיל עם האימייל הזה. נרשמת עם אימייל אחר? או כתבי לי ונבדוק.',
  fail: 'אופס, משהו לא עבד. בדקי את החיבור לאינטרנט ונסי שוב.',
  sending: 'שולחים...',
  resent: 'שלחנו קוד חדש.',
  name: 'נא למלא שם מלא.',
  phone: 'נא למלא מספר טלפון תקין, למשל ⁦050-1234567⁩.',
  saved: 'הפרטים נשמרו.',
  copied: 'הועתק ✓',
  copyFail: 'לא הצלחתי להעתיק. אפשר לסמן את הטקסט ולהעתיק ידנית.'
};
const store = {
  get() { try { return JSON.parse(localStorage.getItem(KEY) || 'null'); } catch (e) { return null; } },
  set(v) { try { localStorage.setItem(KEY, JSON.stringify(v)); } catch (e) {} },
  clear() { try { localStorage.removeItem(KEY); } catch (e) {} }
};
// the endpoint HTML-escapes free-text fields (so a quote can't break its JSON); textContent needs them decoded
const dec = v => typeof v === 'string' && v.includes('&') ? new DOMParser().parseFromString(v, 'text/html').documentElement.textContent : v;
const isEmail = v => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v.trim());
const isPhone = v => /^(?:\+?972|0)(?:5\d|7\d|[23489])\d{7}$/.test(v.replace(/[\s\-().]/g, ''));

// ---- demo data: shown only while no endpoint is configured ----
const SAMPLE = {
  member: { name: 'דנה לוי', email: 'dana@example.com', phone: '050-1234567', business: 'סטודיו לעיצוב', tier: 'founder',
    status: 'active', joinedAt: '2026-12-15', nextChargeAt: '2027-01-15', price: 69, memberNo: '007' },
  club: { session: { title: 'כלי AI אחד: [נושא המפגש]', start: '2027-01-06T10:00:00+02:00' },
    zoomUrl: '#', calendarUrl: '#', whatsappUrl: '#', whatsappHours: '[שעות המענה]', contentUrl: '#', guidesUrl: '#', supportUrl: '#' }
};
const wait = ms => new Promise(r => setTimeout(r, ms));
async function demo(action, data) {
  await wait(600);
  if (action === 'verify') return data.code === '123456' ? { ok: true, token: 'demo' } : { ok: false, error: 'bad-code' };
  if (action === 'me') { const m = { ...SAMPLE.member, ...(store.get()?.demo || {}) }; return { ok: true, member: m, club: SAMPLE.club }; }
  if (action === 'update') { const s = store.get() || {}; s.demo = { name: data.name, phone: data.phone, business: data.business }; store.set(s); }
  return { ok: true };
}

async function call(action, data) {
  if (DEMO) return demo(action, data);
  const ctrl = new AbortController(), timer = setTimeout(() => ctrl.abort(), 20000);
  try {
    // form-encoded keeps it a simple CORS request (no preflight); the endpoint must reply with Access-Control-Allow-Origin
    const res = await fetch(API, { method: 'POST', body: new URLSearchParams({ action, ...data }), signal: ctrl.signal });
    if (!res.ok) throw new Error(res.status);
    const text = await res.text();
    try { return JSON.parse(text); }
    // the endpoint answers with no JSON when it found no matching member: same as "not ok" (request-code stays ok, so emails can't be probed)
    catch (e) { return action === 'request-code' || action === 'logout' ? { ok: true } : { ok: false, error: action === 'verify' ? 'bad-code' : 'auth' }; }
  } finally { clearTimeout(timer); }
}

function demoBanner() {
  if (!DEMO) return;
  const b = document.createElement('div');
  b.className = 'cm-demo';
  b.textContent = 'מצב הדגמה: עוד אין חיבור למערכת החברות. קוד הכניסה לבדיקה: 123456. כל הפרטים כאן לדוגמה.';
  document.body.prepend(b);
}

function busy(btn, on, label) {
  btn.disabled = on;
  if (on) { btn.dataset.label = btn.textContent; btn.textContent = label || T.sending; }
  else btn.textContent = btn.dataset.label || btn.textContent;
}
function fieldError(el, msg) {
  el.setAttribute('aria-invalid', !!msg);
  document.getElementById(el.getAttribute('aria-describedby')).textContent = msg || '';
}

// ---- login page ----
(function login() {
  const f1 = document.getElementById('cm-email'), f2 = document.getElementById('cm-code');
  if (!f1) return;
  demoBanner();
  const s = store.get();
  if (s && s.token) { location.replace(HOME); return; }
  const mail = f1.email, otp = f2.code, n1 = document.getElementById('cm-email-note'), n2 = document.getElementById('cm-code-note');
  let email = '';

  async function send(btn, note) {
    busy(btn, true);
    try { await call('request-code', { email }); return true; }
    catch (e) { note.textContent = T.fail; note.focus(); return false; }
    finally { busy(btn, false); }
  }

  f1.addEventListener('submit', async e => {
    e.preventDefault();
    n1.textContent = '';
    if (!isEmail(mail.value)) { fieldError(mail, T.email); mail.focus(); return; }
    fieldError(mail, '');
    email = mail.value.trim().toLowerCase();
    if (!(await send(f1.querySelector('button'), n1))) return;
    document.getElementById('cm-sent-to').textContent = email;
    f1.hidden = true; f2.hidden = false; otp.value = ''; otp.focus();
  });

  otp.addEventListener('input', () => {
    otp.value = otp.value.replace(/\D/g, '').slice(0, 6);
    if (otp.value.length === 6) f2.requestSubmit();
  });

  f2.addEventListener('submit', async e => {
    e.preventDefault();
    n2.textContent = '';
    if (!/^\d{6}$/.test(otp.value)) { fieldError(otp, T.code); otp.focus(); return; }
    fieldError(otp, '');
    const btn = f2.querySelector('button[type=submit]');
    busy(btn, true);
    let r;
    try { r = await call('verify', { email, code: otp.value }); }
    catch (err) { busy(btn, false); n2.textContent = T.fail; n2.focus(); return; }
    if (!r.ok) {
      busy(btn, false);
      const msg = r.error === 'expired' ? T.expired : r.error === 'inactive' ? T.inactive : T.badCode;
      if (r.error === 'inactive') { n2.textContent = msg; n2.focus(); } else { fieldError(otp, msg); otp.select(); }
      return;
    }
    store.set({ token: r.token, email });
    location.replace(HOME);
  });

  document.getElementById('cm-resend').addEventListener('click', async e => {
    n2.textContent = '';
    const ok = document.getElementById('cm-resent');
    ok.textContent = '';
    if (await send(e.currentTarget, n2)) { fieldError(otp, ''); ok.textContent = T.resent; otp.focus(); }
  });
  document.getElementById('cm-back').addEventListener('click', () => { f2.hidden = true; f1.hidden = false; mail.focus(); });
})();

// ---- every member page (home, content, my account): shown only after the endpoint confirms an active member ----
(function members() {
  const app = document.getElementById('cm-app');
  if (!app) return;
  demoBanner();
  const s = store.get();
  if (!s || !s.token) { location.replace(LOGIN); return; }
  const out = () => { store.clear(); location.replace(LOGIN); };
  const logout = document.getElementById('cm-logout');
  if (logout) logout.addEventListener('click', () => { call('logout', { token: s.token }).catch(() => {}); out(); });

  const day = d => new Intl.DateTimeFormat('he-IL', { weekday: 'long', day: 'numeric', month: 'numeric', year: 'numeric', timeZone: 'Asia/Jerusalem' }).format(d);
  const time = d => new Intl.DateTimeFormat('he-IL', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Jerusalem' }).format(d);
  const date = v => v ? new Intl.DateTimeFormat('he-IL', { day: 'numeric', month: 'numeric', year: 'numeric' }).format(new Date(v)) : '';

  function render(m, c) {
    const start = c.session && c.session.start ? new Date(c.session.start) : null;
    const v = {
      ...m, firstName: (m.name || '').split(' ')[0], initial: (m.name || '').trim().charAt(0),
      tierLabel: m.tier === 'founder' ? 'חברת מייסדת' : 'חברה',
      joinedLabel: date(m.joinedAt), memberNo: m.memberNo ? '#' + m.memberNo : '',
      planLabel: (m.tier === 'founder' ? 'מייסדת' : 'חודשי') + (m.price ? ` · ${m.price} ₪ לחודש` : '') + (m.tier === 'founder' ? ' (מחיר נעול)' : ''),
      statusLabel: m.status === 'active' ? 'פעיל' : m.status === 'past_due' ? 'בעיה בחיוב' : 'לא פעיל',
      nextChargeLabel: date(m.nextChargeAt) || '—',
      sessionTitle: (c.session && c.session.title) || 'המפגש הבא יפורסם בקרוב',
      sessionDay: start ? day(start) : 'בקרוב', sessionTime: start ? time(start) : '—',
      whatsappHours: c.whatsappHours || ''
    };
    document.querySelectorAll('[data-f]').forEach(el => { el.textContent = v[el.dataset.f] || ''; });
    // private links (Zoom, WhatsApp, recordings) come from the endpoint; without one the button shows as "soon"
    document.querySelectorAll('[data-href]').forEach(el => {
      const url = c[el.dataset.href];
      if (url) { el.href = url; el.removeAttribute('aria-disabled'); }
      else {
        el.removeAttribute('href'); el.setAttribute('aria-disabled', 'true');
        if (el.dataset.soon) el.textContent = el.dataset.soon;
      }
    });
    const pill = app.querySelector('.cm-pill');
    if (pill) pill.classList.toggle('off', m.status !== 'active');
    const f = document.getElementById('cm-profile');
    if (f) { f.name.value = m.name || ''; f.phone.value = m.phone || ''; f.business.value = m.business || ''; }
  }

  call('me', { token: s.token }).then(r => {
    if (!r.ok) { out(); return; }
    const m = {}, c = { ...(r.club || {}) };
    Object.keys(r.member || {}).forEach(k => { m[k] = dec(r.member[k]); });
    if (c.session) c.session = { ...c.session, title: dec(c.session.title) };
    c.whatsappHours = dec(c.whatsappHours);
    render(m, c);
    document.getElementById('cm-loading').hidden = true;
    app.hidden = false;
  }).catch(() => { document.getElementById('cm-loading').textContent = T.fail; });

  // prompts: copy button under each prompt
  app.querySelectorAll('.cm-copy').forEach(btn => btn.addEventListener('click', async () => {
    const text = btn.previousElementSibling.textContent.trim(), label = btn.dataset.label || btn.textContent;
    btn.dataset.label = label;
    try { await navigator.clipboard.writeText(text); btn.textContent = T.copied; }
    catch (e) { btn.textContent = T.copyFail; }
    setTimeout(() => { btn.textContent = label; }, 2200);
  }));

  // my account: profile form
  const f = document.getElementById('cm-profile');
  if (!f) return;
  const ok = document.getElementById('cm-profile-ok'), note = document.getElementById('cm-profile-note');
  f.addEventListener('submit', async e => {
    e.preventDefault();
    ok.textContent = ''; note.textContent = '';
    const bad = [];
    fieldError(f.name, f.name.value.trim().length >= 2 ? '' : (bad.push(f.name), T.name));
    fieldError(f.phone, isPhone(f.phone.value) ? '' : (bad.push(f.phone), T.phone));
    if (bad.length) { bad[0].focus(); return; }
    const btn = f.querySelector('button');
    busy(btn, true);
    try {
      const r = await call('update', { token: s.token, name: f.name.value.trim(), phone: f.phone.value.trim(), business: f.business.value.trim() });
      if (!r.ok) { out(); return; }
      ok.textContent = T.saved;
      const name = f.name.value.trim();
      document.querySelectorAll('[data-f="name"]').forEach(el => { el.textContent = name; });
      document.querySelectorAll('[data-f="firstName"]').forEach(el => { el.textContent = name.split(' ')[0]; });
      document.querySelectorAll('[data-f="initial"]').forEach(el => { el.textContent = name.charAt(0); });
    } catch (err) { note.textContent = T.fail; note.focus(); }
    finally { busy(btn, false); }
  });
})();
