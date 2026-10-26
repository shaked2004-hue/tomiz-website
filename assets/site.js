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
