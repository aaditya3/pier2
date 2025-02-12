#!/bin/bash
export PYTHONPATH="$PYTHONPATH:./src/"; poetry run pytest -s tests
