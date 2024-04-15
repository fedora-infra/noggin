#!/bin/bash
#
# SPDX-FileCopyrightText: Contributors to the Fedora Project
#
# SPDX-License-Identifier: GPL-3.0-or-later


STRATEGY_URL=https://raw.githubusercontent.com/fedora-infra/shared/main/liccheck-strategy.ini

trap 'rm -rf "$TMPFILE $STRATEGY_TMPFILE $LOCK_TMPDIR"' EXIT

set -e
set -x

TMPFILE=$(mktemp -t requirements-XXXXXX.txt)
STRATEGY_TMPFILE=$(mktemp -t liccheck-strategy-XXXXXX.ini)
LOCK_TMPDIR=$(mktemp -d -t poetry-lock-XXXXXX)

mkdir -p $LOCK_TMPDIR
# Workaround https://github.com/python-poetry/poetry-plugin-export/issues/183
sed -e '/^urllib3 = {version = "<2"/d' poetry.lock > $LOCK_TMPDIR/poetry.lock
cp -p pyproject.toml $LOCK_TMPDIR/

curl -o $STRATEGY_TMPFILE $STRATEGY_URL

poetry export --with dev --without-hashes -f requirements.txt -o $TMPFILE -C $LOCK_TMPDIR

# Use pip freeze instead of poetry when it fails
# poetry run pip freeze --exclude-editable --isolated > $TMPFILE

poetry run liccheck -r $TMPFILE -s $STRATEGY_TMPFILE
