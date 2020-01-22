#!/bin/sh -e

if [ -d 'dist' ] ; then
    rm -r dist
fi

if [ -d 'site' ] ; then
    rm -rf site
fi

if [ -d 'yoyo_database_migrations.egg-info' ] ; then
    rm -r yoyo_database_migrations.egg-info
fi

# delete python cache
find . -iname '*.pyc' -delete
find . -iname '__pycache__' -delete

rm -f sqlite::memory:
