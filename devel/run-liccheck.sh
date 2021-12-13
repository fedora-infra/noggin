#!/bin/bash

trap 'rm -f "$TMPFILE"' EXIT

set -e

TMPFILE=$(mktemp -t noggin-requirements-XXXXXX.txt)

# Note: we can't use poetry export because it isn't smart enough with conditional dependencies:
# flake8 requires importlib_metadata on python < 3.8, so it's not installed, but it's exported
# and liccheck crashes on packages listed in the req file but not installed.
# poetry export --dev -f requirements.txt -o $TMPFILE

poetry run pip freeze --exclude-editable --isolated > $TMPFILE

poetry run liccheck -r $TMPFILE
