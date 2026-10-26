# tomiz-website

The TomiZ site (tomizs.com). Static HTML, hosted on Netlify.

- Edit content in `src/` (shared header/contact/footer, one file per page in `src/pages/`, articles in `src/articles.json`).
- Run `python3 build.py` for a draft build (draft banner, noindex) or `python3 build.py --live` for production, then commit the generated pages.
- Forms post to the Make webhook in `src/webhook.txt`.
