# Configuration file


Yoyo looks for a configuration file named `yoyo.ini` in the current working
directory or any ancestor directory.

If no configuration file is found `yoyo` will prompt you to
create one, popuplated with the current command line args.

Using a configuration file saves repeated typing,
avoids your database username and password showing in process listings
and lessens the risk of accidentally running migrations
against the wrong database (ie by re-running an earlier `yoyo` entry in
your command history when you have moved to a different directory).

If you do not want a config file to be loaded
add the `--no-config` parameter to the command line options.

The configuration file may contain the following options:

```
# List of migration source directories. "%(here)s" is expanded to the full path of the directory containing this ini file.
sources = %(here)s/migrations %(here)s/lib/module/migrations

# Target database
database = postgresql://scott:tiger@localhost/mydb

# Verbosity level. Goes from 0 (least verbose) to 3 (most verbose)
verbosity = 3

### Disable interactive features
batch_mode = on

# Editor to use when starting new migrations "{}" is expanded to the filename of the new migration
editor = /usr/local/bin/vim -f {}#

# An arbitrary command to run after a migration has been created "{}" is expanded to the filename of the new migration
post_create_command = hg add {}

# A prefix to use for generated migration filenames
prefix = myproject_
```

Config file inheritance may be used to customize configuration per site:

```
# file: yoyo-defaults.ini

[DEFAULT]
sources = %(here)s/migrations

# file: yoyo.ini
[DEFAULT]

; Inherit settings from yoyo-defaults.ini
%inherit = %(here)s/yoyo-defaults.ini

; Use '?' to avoid raising an error if the file does not exist
%inherit = ?%(here)s/yoyo-defaults.ini

database = sqlite:///%(here)s/mydb.sqlite
```