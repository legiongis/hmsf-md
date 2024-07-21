#! /usr/bin/bash

CUR=$PWD

DIR="$( dirname -- "${BASH_SOURCE[0]}"; )";

cd $DIR/../docs
sphinx-build . ./_build/dirhtml -b dirhtml

cd $CUR
