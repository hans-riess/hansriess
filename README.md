# My Academic Website
Developed by Hans Riess.

## CV generation

`python manage.py generate_cv` renders the CV from the database in the official
Georgia Tech research-faculty format (Sections I–V) and attaches the PDF to the
profile, which `/cv/` redirects to. The LaTeX body is assembled in
`academic/cv_builder.py`; typesetting lives in `academic/tex/academic-cv.sty`.
Requires `pdflatex` (see `texlive.packages`).

Sections with no data are skipped, so the document fills in as content is added
through the admin. The Georgia Tech fields — publication categories, CRediT
roles, proposal details, and so on — are grouped into a "Georgia Tech CV"
fieldset on each model.

Prose fields may contain `[[ref:some-slug]]`, which renders as a live
cross-reference such as `I.B.3.4` to whichever entry carries that `cv_ref_slug`.

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