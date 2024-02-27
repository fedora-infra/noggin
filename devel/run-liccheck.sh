#!/bin/bash
#
# SPDX-FileCopyrightText: Contributors to the Fedora Project
#
# SPDX-License-Identifier: GPL-3.0-or-later


STRATEGY_URL=https://raw.githubusercontent.com/fedora-infra/shared/main/liccheck-strategy.ini

trap 'rm -f "$TMPFILE $STRATEGY_TMPFILE"' EXIT

set -e
set -x

TMPFILE=$(mktemp -t requirements-XXXXXX.txt)
STRATEGY_TMPFILE=$(mktemp -t liccheck-strategy-XXXXXX.ini)

curl -o $STRATEGY_TMPFILE $STRATEGY_URL

poetry export --with dev --without-hashes -f requirements.txt -o $TMPFILE

# Use pip freeze instead of poetry when it fails
# poetry run pip freeze --exclude-editable --isolated > $TMPFILE

poetry run liccheck -r $TMPFILE -s $STRATEGY_TMPFILE
