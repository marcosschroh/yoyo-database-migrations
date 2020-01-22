#!/bin/sh -e

scripts/clean.sh

VERSION=`cat yoyo/__init__.py | grep __version__ | sed 's/__version__ = //' | sed 's/"//g'`

export PREFIX=""
if [ -d 'venv' ] ; then
    export PREFIX="venv/bin/"
fi

if ! command -v "${PREFIX}twine" &>/dev/null ; then
    echo "Unable to find the 'twine' command."
    echo "Install from PyPI, using '${PREFIX}pip install twine'."
    exit 1
fi

# uploading to pypi
python setup.py sdist
twine upload dist/*

# creating git tag
echo "Creating tag version v${VERSION}:"
git tag -a v${VERSION} -m 'Bump version v${VERSION}'

echo "git push origin v${VERSION}"

# deploy documentation
mkdocs gh-deploy