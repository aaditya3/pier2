#!/bin/bash
export PYTHONPATH="$PYTHONPATH:./src/"; poetry run python -m scripts.create_db

