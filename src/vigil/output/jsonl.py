"""Writes Finding objects as JSON Lines, to stdout or a file."""

import sys
from collections.abc import Iterable
from pathlib import Path
from typing import TextIO

from vigil.models import Finding


class JSONLWriter:
    """Serializes Finding objects to newline-delimited JSON, one per line."""

    def __init__(self, destination: TextIO | Path | str | None = None) -> None:
        self._owns_handle = False
        if destination is None or destination == "-":
            self._handle: TextIO = sys.stdout
        elif isinstance(destination, (str, Path)):
            self._handle = Path(destination).open("a", encoding="utf-8")
            self._owns_handle = True
        else:
            self._handle = destination

    def write(self, finding: Finding) -> None:
        self._handle.write(finding.model_dump_json())
        self._handle.write("\n")
        self._handle.flush()

    def write_all(self, findings: Iterable[Finding]) -> None:
        for finding in findings:
            self.write(finding)

    def close(self) -> None:
        if self._owns_handle:
            self._handle.close()

    def __enter__(self) -> "JSONLWriter":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
