#!/bin/bash
cd "$(dirname "$0")"
cd ..
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
fi
python3 -m "run.$1"