#!/bin/bash

trap 'rm -f "$TMPFILE"' EXIT

set -e

TMPFILE=$(mktemp -t noggin-requirements-XXXXXX.txt)

pip install --upgrade "poetry>=1.2"
poetry install
poetry export --dev -f requirements.txt -o $TMPFILE
poetry run liccheck -r $TMPFILE
