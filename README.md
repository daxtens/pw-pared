pared
=====

An experimental patch relation detector based on simple name matching.

0) Install the dependencies (currently just `requests`)

1) Adjust the settings at the top of `pared.py`

2) Run:

`PW_API_KEY=<a maintainer api key> python pared.py`

State is stored in `subjects.json` so the process can be killed and restarted
more or less with impunity.

Recognised variables and their defaults
---------------------------------------

`PW_API_KEY` - api token for patchwork, no default

`PW_API_URL` - a *v1.2* API URL for your PW instance, default is
`https://patchwork.ozlabs.org/api/1.2/`

`PW_PROJECT` - what project? default is `patchwork`

`PW_FETCH_DAYS` - when `subjects.json` doesn't exist, how many days of patches
should we download to prime the database? Default is `180` which may be too big
for noisy projects.

`PARED_DATASTORE` - name to use instead of `subjects.json`, default is
`subjects.json`. Handy for when you're managing multiple projects.
