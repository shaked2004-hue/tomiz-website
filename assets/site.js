// Lead forms post to the Make webhook; everything else is progressive enhancement.
const LEAD_WEBHOOK = window.TOMIZ_WEBHOOK || '';
const EN = document.documentElement.lang === 'en';
const T = EN ? {
  off: 'The form is not connected yet. You can write directly to office@tomizs.com.',
  fail: 'Sending failed. Please try again, or write directly to office@tomizs.com.',
  lead: 'Please fill in your name, phone, a valid email and tick the consent box.',
  thanks: "Thank you! Your message was received, and I'll get back to you soon.",
  lm: 'Please fill in your first name and a valid email.'
} : {
  off: 'הטופס עדיין לא מחובר. אפשר לכתוב ישירות ל-office@tomizs.com.',
  fail: 'השליחה לא הצליחה. נסו שוב, או כתבו ישירות ל-office@tomizs.com.',
  lead: 'נא למלא שם, טלפון, אימייל תקין ולסמן את האישור.',
  thanks: 'תודה! הפנייה התקבלה, ואחזור אליכם בהקדם.',
  lm: 'נא למלא שם פרטי ואימייל תקין.'
};

(function reveal() {
  if (!('IntersectionObserver' in window) || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const io = new IntersectionObserver(es => es.forEach(e => {
    if (e.isIntersecting) { e.target.classList.remove('pre'); io.unobserve(e.target); }
  }), { rootMargin: '0px 0px -8% 0px' });
  document.querySelectorAll('.reveal').forEach(el => {
    if (el.getBoundingClientRect().top > innerHeight * 0.92) { el.classList.add('pre'); io.observe(el); }
  });
})();

async function sendLead(form, data, note) {
  if (form.querySelector('.hp input')?.value) return true; // bot filled the honeypot
  if (!LEAD_WEBHOOK) { note.textContent = T.off; return false; }
  const btn = form.querySelector('button[type=submit]');
  btn.disabled = true;
  try {
    // form-encoded + no-cors keeps this a simple request (no CORS preflight); Make parses it into fields
    const body = new URLSearchParams({ ...data, source: form.dataset.source, page: location.pathname, sentAt: new Date().toISOString() });
    await fetch(LEAD_WEBHOOK, { method: 'POST', mode: 'no-cors', body });
    return true;
  } catch (e) {
    note.textContent = T.fail;
    btn.disabled = false;
    return false;
  }
}

const lead = document.getElementById('lead');
lead?.addEventListener('submit', async e => {
  e.preventDefault();
  const note = document.getElementById('form-note');
  if (!lead.checkValidity()) { note.textContent = T.lead; return; }
  note.textContent = '';
  const ok = await sendLead(lead, {
    name: lead.name.value.trim(), phone: lead.phone.value.trim(), email: lead.email.value.trim(), org: lead.org.value.trim(),
    type: lead.type.value, message: lead.msg.value.trim(), contactConsent: true, marketingConsent: false
  }, note);
  if (ok) { lead.reset(); note.textContent = T.thanks; }
});

const lm = document.getElementById('lm-form');
lm?.addEventListener('submit', async e => {
  e.preventDefault();
  const note = document.getElementById('lm-note');
  const name = document.getElementById('lm-name'), mail = document.getElementById('lm-mail');
  if (!name.value.trim() || !mail.value || !mail.checkValidity()) { note.textContent = T.lm; return; }
  note.textContent = '';
  const ok = await sendLead(lm, {
    name: name.value.trim(), email: mail.value.trim(),
    marketingConsent: document.getElementById('lm-ok').checked
  }, note);
  if (ok) { lm.hidden = true; document.getElementById('lm-done').hidden = false; }
});

// ---- accessibility menu: text size, contrast, link highlight, readable font, stop motion ----
(function a11y() {
  const btn = document.querySelector('.a11y-btn');
  if (!btn) return;
  const L = EN ? { title: 'Accessibility', size: 'Text size', contrast: 'High contrast', links: 'Highlight links', readable: 'Readable font', still: 'Stop animations', reset: 'Reset', close: 'Close', stmt: 'Accessibility statement', bigger: 'Larger text', smaller: 'Smaller text' }
               : { title: 'נגישות', size: 'גודל טקסט', contrast: 'ניגודיות גבוהה', links: 'הדגשת קישורים', readable: 'גופן קריא', still: 'עצירת אנימציות', reset: 'איפוס', close: 'סגירה', stmt: 'הצהרת נגישות', bigger: 'הגדלת טקסט', smaller: 'הקטנת טקסט' };
  const store = { get() { try { return JSON.parse(localStorage.getItem('tomiz-a11y')) || {}; } catch (e) { return {}; } },
                  set(v) { try { localStorage.setItem('tomiz-a11y', JSON.stringify(v)); } catch (e) {} } };
  const MODES = ['contrast', 'links', 'readable', 'still'];
  let st = store.get();
  const apply = () => {
    const c = document.documentElement.classList;
    MODES.forEach(m => c.toggle('a11y-' + m, !!st[m]));
    [1, 2, 3].forEach(n => c.toggle('a11y-fs' + n, st.fs === n));
  };
  apply();
  const panel = document.createElement('div');
  panel.className = 'a11y-panel'; panel.id = 'a11y-panel'; panel.hidden = true;
  panel.setAttribute('role', 'dialog'); panel.setAttribute('aria-label', L.title);
  panel.innerHTML = `<h2>${L.title}<button type="button" class="x" aria-label="${L.close}">×</button></h2>
    <div class="sz"><span>${L.size}</span><button type="button" data-fs="-1" aria-label="${L.smaller}">A−</button><button type="button" data-fs="1" aria-label="${L.bigger}">A+</button></div>
    <div class="grid">${MODES.map(m => `<button type="button" class="opt" data-m="${m}" aria-pressed="${!!st[m]}">${L[m]}</button>`).join('')}
    <button type="button" class="opt reset">${L.reset}</button></div>
    <a class="stmt" href="${EN ? '/en/accessibility/' : '/accessibility/'}">${L.stmt}</a>`;
  document.body.appendChild(panel);
  const open = v => { panel.hidden = !v; btn.setAttribute('aria-expanded', v); if (v) panel.querySelector('button').focus(); };
  btn.addEventListener('click', () => open(panel.hidden));
  panel.querySelector('.x').addEventListener('click', () => { open(false); btn.focus(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !panel.hidden) { open(false); btn.focus(); } });
  document.addEventListener('click', e => { if (!panel.hidden && !panel.contains(e.target) && !btn.contains(e.target)) open(false); });
  panel.addEventListener('click', e => {
    const b = e.target.closest('button');
    if (!b) return;
    if (b.dataset.fs) st.fs = Math.max(0, Math.min(3, (st.fs || 0) + +b.dataset.fs));
    else if (b.dataset.m) { st[b.dataset.m] = !st[b.dataset.m]; b.setAttribute('aria-pressed', st[b.dataset.m]); }
    else if (b.classList.contains('reset')) { st = {}; panel.querySelectorAll('[data-m]').forEach(x => x.setAttribute('aria-pressed', 'false')); }
    else return;
    store.set(st); apply();
  });
})();

// ---- mark the current page in the rail ----
document.querySelectorAll('.rail a[href^="/"]').forEach(a => {
  const h = a.getAttribute('href');
  if (h.length > 4 && location.pathname.startsWith(h)) a.setAttribute('aria-current', 'page');
});

// ---- "ask about this": prefill the contact form from a talk or service card ----
(function ask() {
  const form = document.getElementById('lead');
  const cards = document.querySelectorAll('.talk-card, .service');
  if (!form || !cards.length) return;
  cards.forEach(card => {
    const title = card.querySelector('h3, h2')?.textContent.trim();
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'ask';
    b.textContent = EN ? 'Ask about this →' : 'לפרטים ותיאום ←';
    b.addEventListener('click', () => {
      const talk = /הרצאה|Talk/.test(card.querySelector('.tag, .k')?.textContent || '');
      form.type.selectedIndex = card.classList.contains('service') ? 1 : talk ? 2 : 1;
      form.msg.value = (EN ? "I'd like to hear more about: " : 'אשמח לשמוע עוד על: ') + title;
      document.getElementById('contact').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
      form.classList.remove('flash'); void form.offsetWidth; form.classList.add('flash');
      setTimeout(() => form.name.focus({ preventScroll: true }), 600);
    });
    (card.querySelector('.body') || card).appendChild(b);
  });
})();

// ---- talks page: filter talks vs. workshops ----
(function filters() {
  const grid = document.querySelector('.talks-grid');
  if (!grid) return;
  const cards = [...grid.querySelectorAll('.talk-card')];
  const kinds = [...new Set(cards.map(c => c.querySelector('.tag').textContent.trim()))];
  const bar = document.createElement('div');
  bar.className = 'chips'; bar.setAttribute('role', 'group'); bar.setAttribute('aria-label', EN ? 'Filter' : 'סינון');
  const all = EN ? 'All' : 'הכל';
  const labels = { 'הרצאה': 'הרצאות', 'סדנה': 'סדנאות', 'Talk': 'Talks', 'Workshop': 'Workshops' };
  [all, ...kinds].forEach((k, i) => {
    const b = document.createElement('button');
    b.type = 'button'; b.textContent = labels[k] || k; b.setAttribute('aria-pressed', i === 0);
    b.addEventListener('click', () => {
      bar.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x === b));
      cards.forEach(c => c.classList.toggle('is-hidden', k !== all && c.querySelector('.tag').textContent.trim() !== k));
    });
    bar.appendChild(b);
  });
  grid.before(bar);
})();

// ---- articles: reading progress bar + copy button for prompts ----
(function article() {
  const post = document.querySelector('article.post .back') && document.querySelector('article.post');
  if (!post) return;
  const bar = document.createElement('div');
  bar.className = 'progress'; bar.setAttribute('aria-hidden', 'true');
  document.body.appendChild(bar);
  const upd = () => {
    const r = post.getBoundingClientRect();
    bar.style.transform = `scaleX(${Math.min(1, Math.max(0, -r.top / Math.max(1, r.height - innerHeight)))})`;
  };
  addEventListener('scroll', upd, { passive: true }); upd();
  post.querySelectorAll('blockquote').forEach(q => {
    if (q.textContent.length < 120 || !navigator.clipboard) return;
    const text = q.textContent;
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'copy'; b.textContent = EN ? 'Copy prompt' : 'העתקת הפרומפט';
    b.addEventListener('click', async () => {
      try { await navigator.clipboard.writeText(text); b.textContent = EN ? 'Copied ✓' : 'הועתק ✓'; } catch (e) {}
      setTimeout(() => b.textContent = EN ? 'Copy prompt' : 'העתקת הפרומפט', 2000);
    });
    q.appendChild(b);
  });
})();

// ---- hero: the unboxing graphic leans gently toward the pointer ----
(function hero() {
  const svg = document.querySelector('.hero .unbox svg');
  if (!svg || matchMedia('(prefers-reduced-motion: reduce)').matches || !matchMedia('(pointer:fine)').matches) return;
  const hero = svg.closest('.hero');
  svg.style.transition = 'transform .4s ease-out';
  hero.addEventListener('pointermove', e => {
    if (document.documentElement.classList.contains('a11y-still')) return;
    const r = hero.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5;
    svg.style.transform = `perspective(600px) rotateY(${x * 14}deg) rotateX(${-y * 14}deg) translate(${x * 10}px,${y * 10}px)`;
  });
  hero.addEventListener('pointerleave', () => svg.style.transform = '');
})();

// ---- "where to start?" chooser: highlights the matching path ----
(function chooser() {
  const paths = document.querySelector('.paths');
  if (!paths) return;
  const items = [...paths.querySelectorAll('.path')];
  const custom = document.querySelector('.custom');
  const opts = EN ? ["I'm from an organization", 'I have knowledge to turn into a product', "I'm not sure yet"]
                  : ['אני מארגון', 'יש לי ידע להפוך למוצר', 'עוד לא בטוח/ה'];
  const targets = [items[0], items[1], custom];
  const bar = document.createElement('div');
  bar.className = 'chooser reveal'; bar.setAttribute('role', 'group'); bar.setAttribute('aria-label', EN ? 'Where to start?' : 'איפה מתחילים?');
  const scope = paths.parentElement;
  opts.forEach((label, i) => {
    const b = document.createElement('button');
    b.type = 'button'; b.textContent = label; b.setAttribute('aria-pressed', 'false');
    b.addEventListener('click', () => {
      const on = b.getAttribute('aria-pressed') !== 'true';
      bar.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', on && x === b));
      scope.classList.toggle('picked', on);
      targets.forEach((t, j) => t?.classList.toggle('on', on && j === i));
      if (on && targets[i]) {
        const r = targets[i].getBoundingClientRect();
        if (r.top < 0 || r.bottom > innerHeight) targets[i].scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    });
    bar.appendChild(b);
  });
  paths.before(bar);
})();

// ---- cards lean toward the pointer, with a soft spotlight ----
(function tilt() {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches || !matchMedia('(pointer:fine)').matches) return;
  document.querySelectorAll('.card, .talk-card, .path, .step').forEach(el => {
    el.classList.add('tilt');
    el.addEventListener('pointermove', e => {
      const r = el.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
      el.style.setProperty('--mx', x * 100 + '%'); el.style.setProperty('--my', y * 100 + '%');
      if (document.documentElement.classList.contains('a11y-still')) return;
      el.style.transform = `perspective(900px) rotateX(${(.5 - y) * 5}deg) rotateY(${(x - .5) * 5}deg) translateY(-4px)`;
    });
    el.addEventListener('pointerleave', () => el.style.transform = '');
  });
})();
