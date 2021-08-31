pared
=====

An experimental patch relation detector based on simple name matching.

0) Install the dependencies (currently just `requests`)

1) Adjust the settings at the top of `pared.py`

2) Run:

`PW_API_KEY=<a maintainer api key> python pared.py`

State is stored in `subjects.json` so the process can be killed and restarted
more or less with impunity.
