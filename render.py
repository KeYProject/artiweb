#!/usr/bin/python3

from pathlib import Path
import os.path
import os

import markdown


ROOT = Path("pull-requests")
TARGET = Path("public")

file: Path
for file in ROOT.rglob('*'):
    if file.is_file():
        out_file = TARGET / file.relative_to(ROOT)
        if file.stem == 'md':  # found markdown
            markdown.markdownFromFile(input=file, output=str)
        else:
            out_file.parent.mkdir(exist_ok=True, parents=True)
            os.link(file, out_file)
