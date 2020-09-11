#!/usr/bin/env bash

chmod +x .githooks/pre-commit
bash .githooks/pre-commit && ln -s $PWD/.githooks/pre-commit .git/hooks/pre-commit || exit 1
