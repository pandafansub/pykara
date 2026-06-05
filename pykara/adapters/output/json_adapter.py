"""JSON output adapter for normalized subtitle documents."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from pykara.adapters import SubtitleDocument
from pykara.errors import DocumentWriteError


class JsonWriter:
    """Write subtitle documents to a JSON representation."""

    def write(self, document: SubtitleDocument, path: str | Path) -> None:
        """Serialize one document to JSON on disk.

        Args:
            document: Normalized subtitle document to serialize.
            path: Destination JSON path.

        Raises:
            DocumentWriteError: If writing the JSON file fails.
        """

        path_obj = Path(path)
        try:
            path_obj.write_text(
                json.dumps(
                    self.to_dict(document),
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        except Exception as error:
            raise DocumentWriteError(path_obj, message=str(error)) from error

    def to_dict(self, document: SubtitleDocument) -> dict[str, object]:
        """Return the JSON-serializable document schema.

        Args:
            document: Normalized subtitle document to convert.

        Returns:
            JSON-serializable dictionary representation.
        """

        return {
            "metadata": asdict(document.metadata),
            "styles": {
                name: asdict(style) for name, style in document.styles.items()
            },
            "events": [asdict(event) for event in document.events],
        }
