#!/bin/sh -e

if [ -d 'dist' ] ; then
    rm -r dist
fi

if [ -d 'yoyo_database_migrations.egg-info' ] ; then
    rm -r yoyo_database_migrations.egg-info
fi