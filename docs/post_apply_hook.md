# Post-apply hook


It can be useful to have a script that is run after every successful migration.
For example you could use this to update database permissions or re-create
views.
To do this, create a special migration file called ``post-apply.py``.
This file should have the same format as any other migration file.