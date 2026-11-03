# tomiz-website

The TomiZ site (tomizs.com). Static HTML, hosted on Netlify.

- Edit content in `src/` (shared header/contact/footer, one file per page in `src/pages/`, articles in `src/articles.json`).
- Run `python3 build.py` for a draft build (draft banner, noindex) or `python3 build.py --live` for production, then commit the generated pages.
- Forms post to the Make webhook in `src/webhook.txt`.
- Webinar campaign pages (`/webinar/`, `/webinar/thanks/`): source in `src/webinar/`, styles/script in `assets/webinar.css` and `assets/webinar.js`. They have no site nav, are always noindex and stay out of the sitemap. Sign-ups go to their own Make webhook: put the URL in `src/webinar/webhook.txt` (or set `TOMIZ_WEBINAR_WEBHOOK`) and rebuild. The build also writes the calendar file `files/tomiz-webinar-2026-12-01.ics`.
