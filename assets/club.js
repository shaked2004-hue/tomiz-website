// TomiZ Club pages: sticky join button on phones, and the members' booking form (posts to the site's Make webhook, like the other forms).
(function stick() {
  const bar = document.querySelector('.cl-stick'), hero = document.getElementById('hero-cta'), join = document.getElementById('join');
  if (!bar || !hero || !join || !('IntersectionObserver' in window)) return;
  const seen = new Map();
  const io = new IntersectionObserver(es => {
    es.forEach(e => seen.set(e.target, e.isIntersecting));
    bar.classList.toggle('on', !seen.get(hero) && hero.getBoundingClientRect().bottom < 0 && !seen.get(join));
  });
  io.observe(hero); io.observe(join);
})();

(function book() {
  const form = document.getElementById('book');
  if (!form) return;
  const HOOK = window.TOMIZ_WEBHOOK || '';
  const msg = document.getElementById('book-msg'), btn = form.querySelector('button[type=submit]'), label = btn.textContent;
  const T = {
    name: 'נא למלא שם.',
    phone: 'נא למלא מספר טלפון תקין, למשל ⁦050-1234567⁩.',
    email: 'נא למלא כתובת אימייל תקינה.',
    ok: 'קיבלתי! אחזור אליכם בהקדם 💚',
    off: 'הטופס עוד לא מחובר. אפשר לכתוב לי בוואטסאפ או במייל ⁦office@tomizs.com⁩',
    fail: 'אופס, ההודעה לא נשלחה. נסו שוב, או כתבו לי בוואטסאפ.'
  };
  const checks = {
    name: v => v.trim().length >= 2,
    phone: v => /^(?:\+?972|0)(?:5\d|7\d|[23489])\d{7}$/.test(v.replace(/[\s\-().]/g, '')),
    email: v => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v.trim())
  };
  const check = n => {
    const el = form.elements[n], ok = checks[n](el.value);
    el.setAttribute('aria-invalid', !ok);
    document.getElementById(el.getAttribute('aria-describedby')).textContent = ok ? '' : T[n];
    return ok;
  };
  let sending = false;
  const say = (t, cls) => { msg.textContent = t; msg.className = 'clm-msg ' + cls; msg.focus(); };
  form.addEventListener('submit', async e => {
    e.preventDefault();
    if (sending) return;
    const bad = Object.keys(checks).filter(n => !check(n));
    if (bad.length) { form.elements[bad[0]].focus(); return; }
    if (form.website.value) { say(T.ok, 'ok'); form.reset(); return; }
    if (!HOOK) { say(T.off, 'bad'); return; }
    sending = true; btn.disabled = true; btn.textContent = 'שולח...';
    const body = new URLSearchParams({
      name: form.name.value.trim(), phone: form.phone.value.trim(), email: form.email.value.trim(),
      kind: form.kind.value, message: form.message.value.trim(), source: form.dataset.source,
      page: location.pathname, sentAt: new Date().toISOString()
    });
    try {
      await fetch(HOOK, { method: 'POST', mode: 'no-cors', body });
      form.reset(); say(T.ok, 'ok');
    } catch (err) { say(T.fail, 'bad'); }
    sending = false; btn.disabled = false; btn.textContent = label;
  });
})();

// scroll reveal: cards rise in as they enter the screen. Armed only below the first screen, so nothing visible starts hidden.
(function reveal() {
  if (!('IntersectionObserver' in window) || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const els = [...document.querySelectorAll('.reveal, .cl-ev, .clm-card, .clm-off, .cl-steps li, .cl-faq details')];
  const below = els.filter(el => el.getBoundingClientRect().top > innerHeight);
  if (!below.length) return;
  document.documentElement.classList.add('js-reveal');
  below.forEach(el => { el.classList.add('reveal', 'pre'); });
  const io = new IntersectionObserver(es => es.forEach(e => {
    if (!e.isIntersecting) return;
    const sibs = [...e.target.parentElement.children].filter(c => c.classList.contains('pre'));
    e.target.style.transitionDelay = Math.min(sibs.indexOf(e.target), 4) * 90 + 'ms';
    e.target.classList.remove('pre'); io.unobserve(e.target);
  }), { rootMargin: '0px 0px -8% 0px' });
  below.forEach(el => io.observe(el));
})();

// Campaign tracking: keep src / utm_* from the landing address, report checkout starts and purchases to the Meta pixel.
(function track() {
  const KEYS = ['src', 'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term'];
  const CFG = window.TOMIZ_CLUB || {};
  const store = {
    get() { try { return JSON.parse(localStorage.getItem('tomiz_club_src') || '{}'); } catch (e) { return {}; } },
    set(v) { try { localStorage.setItem('tomiz_club_src', JSON.stringify(v)); } catch (e) {} }
  };
  const q = new URLSearchParams(location.search), found = {};
  KEYS.forEach(k => { if (q.get(k)) found[k] = q.get(k).slice(0, 80); });
  if (Object.keys(found).length) store.set(Object.assign(found, { at: Date.now() }));
  const src = store.get();
  const fb = (...a) => { if (typeof window.fbq === 'function') window.fbq(...a); };
  const extra = { content_name: 'tomiz-club', source: src.src || src.utm_source || 'direct', campaign: src.utm_campaign || '' };

  document.querySelectorAll('a.cl-btn[href]').forEach(a => {
    const href = a.getAttribute('href');
    if (!/^https?:/.test(href) || /wa\.me|calendar|\/club\//.test(href)) return; // only the payment link
    if (CFG.pass_params) {
      const u = new URL(href);
      KEYS.forEach(k => { if (src[k] && !u.searchParams.has(k)) u.searchParams.set(k, src[k]); });
      a.href = u.toString();
    }
    a.addEventListener('click', () => fb('track', 'InitiateCheckout', Object.assign({ value: CFG.price || 69, currency: 'ILS' }, extra)));
  });

  if (document.querySelector('[data-page="thanks"]')) {
    let sent = 0;
    try { sent = +localStorage.getItem('tomiz_club_purchase') || 0; } catch (e) {}
    if (Date.now() - sent > 25 * 864e5) { // one Purchase per browser per month, so refreshes don't double count
      fb('track', 'Purchase', Object.assign({ value: CFG.price || 69, currency: 'ILS' }, extra));
      try { localStorage.setItem('tomiz_club_purchase', String(Date.now())); } catch (e) {}
    }
  }
})();
