# abhaynataraj.github.io

My data and analytics portfolio: **https://abhaynataraj.github.io**

## Adding a new project

**The quick way:** on the project's GitHub repo, click the gear icon next to *About* and add the
topic `portfolio`. The site checks GitHub every morning at 6am IST and adds the repo under
"More projects", using:

- the repo **description** (or the first paragraph of its README)
- the **Website** link from the About box, shown as "Live demo"
- its **topics** and main language as tags
- the **first image** in its README (badges are skipped)

Want it live straight away? Go to *Actions → Build and publish portfolio → Run workflow*.

**The fuller way:** add an entry to [`content/projects.yml`](content/projects.yml) to give a
project a big featured card with headline numbers and highlights. Entries there show even if the
repo isn't tagged, which is also how the Tableau-only NimbusPM project is listed.

## Editing everything else

| What | Where |
|---|---|
| Headline, about text, experience, education, skills, contact links | `content/profile.yml` |
| Project cards, order, featured or not, hiding a repo | `content/projects.yml` |
| Resume | replace `assets/Abhay_Nataraj_Resume.pdf` (keep the name) |
| Project screenshots | `assets/img/` |
| Look and layout | `build/template.html`, `assets/style.css` |

Every commit to `main` rebuilds and republishes the site in about a minute. You can edit the YAML
files directly on github.com.

## Running it locally

```bash
pip install -r build/requirements.txt
python build/build.py
# then open _site/index.html
```
