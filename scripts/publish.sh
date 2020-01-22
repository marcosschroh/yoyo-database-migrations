#!/bin/sh -e

export VERSION=`cat yoyo/__init__.py | grep __version__ | sed "s/__version__ = //" | sed "s/'//g"`
export PREFIX=""
if [ -d 'venv' ] ; then
    export PREFIX="venv/bin/"
fi

scripts/clean.sh

if ! command -v "${PREFIX}twine" &>/dev/null ; then
    echo "Unable to find the 'twine' command."
    echo "Install from PyPI, using '${PREFIX}pip install twine'."
    exit 1
fi

find yoyo -type f -name "*.py[co]" -delete
find yoyo -type d -name __pycache__ -delete

${PREFIX}python setup.py sdist
${PREFIX}twine upload dist/*
${PREFIX}mkdocs gh-deploy

echo "You probably want to also tag the version now:"
echo "git tag -a v${VERSION} -m 'version v${VERSION}'"
echo "git push origin v${VERSION}"

scripts/clean.sh
