# Copyright 2026 Capstone MCP contributors.
"""Save rendered reports with exclusive creation and recover from write failures."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory


def _publish(outputs: list[tuple[Path, str]]) -> None:
    parent = outputs[0][0].parent
    parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=parent) as temporary:
        staged = []
        for index, (target, content) in enumerate(outputs):
            pending = Path(temporary) / str(index)
            _ = pending.write_text(content, encoding="utf-8")
            staged.append((pending, target, pending.stat()))

        # A process crash between two publishes can leave one complete file.
        published = []
        try:
            for pending, target, original_stat in staged:
                if os.name == "nt":
                    _ = pending.rename(target)  # Windows rename rejects existing names.
                else:
                    os.link(pending, target)
                published.append((target, original_stat))
        except OSError as error:
            for target, original_stat in published:
                try:
                    if os.path.samestat(target.lstat(), original_stat):
                        target.unlink()
                except FileNotFoundError:
                    pass
                except OSError as cleanup_error:
                    error.add_note(
                        f"Could not remove partial output {target}: {cleanup_error}",
                    )
            raise


def write_report_file(
    out_path: str,
    format_type: str,
    md_text: str | None,
    html_text: str | None,
) -> None:
    """Write one or both report formats to new ordinary files."""
    path = Path(out_path)
    if os.name == "nt" and (
        path.is_reserved()
        or path.anchor.startswith(("\\\\.\\", "\\\\?\\"))
        or any(":" in part for part in path.parts if part != path.anchor)
    ):
        msg = "Report output must be an ordinary filesystem path."
        raise ValueError(msg)
    if format_type == "html":
        outputs = [(path, html_text or "")]
    elif format_type == "both":
        html_path = path.with_suffix(".html")
        if path == html_path:
            msg = "Markdown and HTML report destinations must be different."
            raise ValueError(msg)
        outputs = [(path, md_text or ""), (html_path, html_text or "")]
    else:
        outputs = [(path, md_text or "")]

    for target, _ in outputs:
        if target.exists() or target.is_symlink():
            msg = f"Report output already exists: {target}"
            raise FileExistsError(msg)

    _publish(outputs)
