// Webinar pages: the sign-up form posts to its own Make webhook, then goes to /webinar/thanks/.
// The Meta Lead event fires once, on the thanks page, only after a successful send (a flag in sessionStorage).
const WEBINAR_WEBHOOK = window.TOMIZ_WEBINAR_WEBHOOK || '';
const THANKS = '/webinar/thanks/';
const FLAG = 'tomiz-webinar-lead';
const T = {
  name: 'נא למלא שם מלא.',
  phone: 'נא למלא מספר טלפון תקין, למשל ⁦050-1234567⁩.', // ⁦..⁩ keep the example left-to-right
  email: 'נא למלא כתובת אימייל תקינה, למשל ⁦name@gmail.com⁩.',
  consent: 'כדי להירשם צריך לאשר קבלת טיפים ועדכונים.',
  off: 'ההרשמה עדיין לא מחוברת. אפשר להירשם בינתיים במייל: ⁦office@tomizs.com⁩',
  fail: 'אופס, ההרשמה לא נשלחה. בדקו את החיבור לאינטרנט ונסו שוב. אם זה ממשיך, כתבו לנו: ⁦office@tomizs.com⁩',
  sending: 'שומרים לכם מקום...'
};
const flag = {
  set() { try { sessionStorage.setItem(FLAG, '1'); return true; } catch (e) { return false; } },
  take() { try { const v = sessionStorage.getItem(FLAG); sessionStorage.removeItem(FLAG); return !!v; } catch (e) { return false; } }
};
const lead = () => window.fbq && fbq('track', 'Lead', { content_name: 'webinar-2026-12-01' });

// ---- registration form ----
(function register() {
  const form = document.getElementById('reg');
  if (!form) return;
  const note = document.getElementById('reg-note');
  const btn = form.querySelector('button[type=submit]');
  const label = btn.textContent;
  const checks = {
    name: v => v.trim().length >= 2,
    phone: v => /^(?:\+?972|0)(?:5\d|7\d|[23489])\d{7}$/.test(v.replace(/[\s\-().]/g, '')),
    email: v => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v.trim())
  };
  let tried = false, sending = false;

  const check = name => {
    const el = form.elements[name], ok = checks[name](el.value);
    el.setAttribute('aria-invalid', !ok);
    document.getElementById(el.getAttribute('aria-describedby')).textContent = ok ? '' : T[name];
    return ok;
  };
  const checkConsent = () => {
    const ok = form.marketing.checked;
    form.marketing.setAttribute('aria-invalid', !ok);
    document.getElementById('r-ok-err').textContent = ok ? '' : T.consent;
    return ok;
  };
  form.marketing.addEventListener('change', () => { if (tried) checkConsent(); });
  Object.keys(checks).forEach(name => {
    const el = form.elements[name];
    el.addEventListener('blur', () => { if (tried || el.value) check(name); });
    el.addEventListener('input', () => { if (el.getAttribute('aria-invalid') === 'true') check(name); });
  });

  form.addEventListener('submit', async e => {
    e.preventDefault();
    if (sending) return; // double-submit guard
    tried = true;
    note.textContent = '';
    const bad = Object.keys(checks).filter(name => !check(name));
    if (bad.length) { form.elements[bad[0]].focus(); }
    if (!checkConsent()) { if (!bad.length) form.marketing.focus(); return; }
    if (bad.length) return;
    if (form.website.value) { location.href = THANKS; return; } // bot filled the honeypot: pretend it worked
    if (!WEBINAR_WEBHOOK) { note.textContent = T.off; note.focus(); return; }

    sending = true; btn.disabled = true; btn.textContent = T.sending; form.setAttribute('aria-busy', 'true');
    const utm = {};
    new URLSearchParams(location.search).forEach((v, k) => { if (k.startsWith('utm_')) utm[k] = v; });
    const body = new URLSearchParams({
      name: form.name.value.trim(), phone: form.phone.value.trim(), email: form.email.value.trim(),
      marketingConsent: form.marketing.checked, source: form.dataset.source, webinar: '2026-12-01T10:00+02:00',
      page: location.pathname, sentAt: new Date().toISOString(), ...utm
    });
    const ctrl = new AbortController(), timer = setTimeout(() => ctrl.abort(), 15000);
    try {
      // form-encoded + no-cors keeps this a simple request (no CORS preflight), same as the site's other forms
      await fetch(WEBINAR_WEBHOOK, { method: 'POST', mode: 'no-cors', body, signal: ctrl.signal });
    } catch (err) {
      clearTimeout(timer);
      sending = false; btn.disabled = false; btn.textContent = label; form.removeAttribute('aria-busy');
      note.textContent = T.fail; note.focus();
      return;
    }
    clearTimeout(timer);
    if (!flag.set()) lead(); // no sessionStorage: fire here instead of on the thanks page
    location.href = THANKS;
  });

  // focus the first field when arriving via a "save my spot" link
  document.querySelectorAll('a[href="#register"]').forEach(a => a.addEventListener('click', () =>
    setTimeout(() => form.elements.name.focus({ preventScroll: true }), 450)));
})();

// ---- sticky CTA on phones: shown once the hero button scrolls away, hidden while the form is on screen ----
(function stick() {
  const bar = document.querySelector('.wb-stick'), hero = document.getElementById('hero-cta'), reg = document.getElementById('register');
  if (!bar || !hero || !reg || !('IntersectionObserver' in window)) return;
  document.body.classList.add('has-stick');
  const seen = new Map();
  const io = new IntersectionObserver(es => {
    es.forEach(e => seen.set(e.target, e.isIntersecting));
    const heroAbove = !seen.get(hero) && hero.getBoundingClientRect().bottom < 0;
    bar.classList.toggle('on', heroAbove && !seen.get(reg));
  });
  io.observe(hero); io.observe(reg);
})();

// ---- thanks page: the Lead event, once per successful sign-up ----
if (document.querySelector('[data-page="thanks"]') && flag.take()) lead();
