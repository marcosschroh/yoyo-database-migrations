# Password security

You can specify your database username and password either as part of the
database connection string on the command line (exposing your database
password in the process list)
or in a configuration file where other users may be able to read it.

The ``-p`` or ``--prompt-password`` flag causes yoyo to prompt
for a password, helping prevent your credentials from being leaked.