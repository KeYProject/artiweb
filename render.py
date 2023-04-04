#!/usr/bin/python3

from pathlib import Path
import os.path
import os

import markdown


ROOT = Path("pull-requests")
TARGET = Path("public")

file: Path

DATA_PATHS = [Path("css"), Path("js")]

for root in DATA_PATHS:
    for file in root.rglob('*'):
        if file.name.startswith("."):
            continue
        if file.is_file():
            out_file = TARGET / file
            out_file.parent.mkdir(exist_ok=True, parents=True)
            os.link(file, out_file)

for file in ROOT.rglob('*'):
    if file.name.startswith("."):
        continue
    if file.is_file():
        out_file = TARGET / file.relative_to(ROOT)
        if file.stem == 'md':  # found markdown
            markdown.markdownFromFile(input=file, output=str)
        else:
            out_file.parent.mkdir(exist_ok=True, parents=True)
            os.link(file, out_file)
