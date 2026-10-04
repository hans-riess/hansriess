# My Academic Website
Developed by Hans Riess.

## Tests and CI

`python manage.py test academic` runs the suite. GitHub Actions runs it on every
push to `main` and on every pull request, alongside a second job that installs
LaTeX and builds a real PDF from the sample fixture — so a broken style file or
an unresolved cross-reference fails the build rather than surfacing the next
time someone hits Download CV. The generated `cv.pdf`, `cv.tex` and `cv.log` are
attached to the run as artifacts.

Both jobs need PostgreSQL: some early migrations are not SQLite compatible.

## CV generation

`python manage.py generate_cv` renders the CV from the database as a plain,
black-on-white academic job-market CV and attaches the PDF to the profile, which
`/cv/` redirects to. The LaTeX body is assembled in `academic/cv_builder.py`;
typesetting lives in `academic/tex/academic-cv.sty`. Requires `pdflatex` (see
`texlive.packages`).

Sponsored research and teaching come ahead of the publication list:

> Research Interests · Education · Appointments · **Sponsored Research** ·
> **Teaching and Mentoring** · Publications · Presentations · Technical
> Contributions · Honors and Awards · Service

Sections with no data are skipped, so the document fills in as content is added
through the admin.

Entries that can be cross-referenced are numbered within a series — `[G]`
funded projects, `[PR]` proposals, `[J]` journal articles, `[C]` conference
proceedings, `[S]` papers under review, `[P]` preprints, `[T]` talks, `[D]`
delivered products, `[I]` technical innovations, `[R]` technical reports.
Numbers count down, so the last entry of a series is 1 and an entry keeps its
number as new ones are added above it.

Work in review is entered with Status *In review* and the target venue in
Journal; it is cited by its arXiv ID and closes with "Submitted to *venue*".
Journal articles and preprints in review appear by default, under Papers Under
Review. Conference papers in review join them there, and preprints with no
submission pending (Status *Published*, or *Rejected* for one that was turned
down and left on arXiv) get a Preprints subsection, but both only when "show all
references" is ticked on the profile.

Prose fields may contain `[[ref:some-slug]]`, which renders as a live
cross-reference such as `[J3]` to whichever entry carries that `cv_ref_slug`.

To check a change to the layout without touching the real database, load the
sample data — representative rows for every section, **not** a copy of the live
content — into a scratch database and build from that:

```
python manage.py loaddata cv_sample
python manage.py generate_cv --keep-tex   # leaves cv.tex and cv.log in temp_cv/
```

## Features
Developed/planning many features to make it easier for researchers to interact with my work.

### Completed
* Basic landing page design
  * basic info and bio
  * publications list
  * contact info icons
* Chalkboard redesign
  * Carousel with math figures

### In progress...
* Organized publications page from Reference objects
  * thumbnail images for each paper
  * my name bolded
  * info about first author 
* Automatic CV generation

### Wish list 
* Generate page for each publication
  * interactive link from the publication list on main page
  * embedded .pdf of paper
  * abstract and keywords
  * names, headshots, and institutions of coauthors
  * AI chat about paper 
* Utilize [Google scholar](https://serpapi.com/google-scholar-api) API to automatically update publicaitons list
* Interactive hypergraph / map of coauthor locations with headshots displaying on hover
* Keyword interactive graph or world cloud like graphic
* Research page automatically generated from publications by AI
* Meeting booking system
  * not using a 3rd party API
  * directly use google calendar and Zoom APIs