#!/bin/sh

set -e

topdir=$(realpath $(dirname $0)/..)
cd $topdir

set -x

find tests/unit/ -path "*/cassettes/*" -a -name "*.yaml" -delete
poetry run pytest --no-cov -vv -x tests/unit
