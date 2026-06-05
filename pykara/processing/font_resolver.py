"""Platform-aware font discovery for text measurement backends."""

# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from sys import platform
from typing import Literal

from pykara.errors import PykaraError

try:
    from fontTools.ttLib import TTFont as TTFont
except ImportError:
    TTFont = None


FontSource = Literal[
    "explicit",
    "user",
    "system",
    "fontconfig",
    "coretext",
    "matplotlib",
]


@dataclass(slots=True, frozen=True)
class ResolvedFont:
    """Concrete font selected for one ASS style face."""

    path: str
    family: str
    source: FontSource


_FONT_EXTENSIONS = frozenset({".ttf", ".otf"})
_FONT_FAMILY_NAME_IDS = frozenset({1, 4, 16})
_FONT_STYLE_NAME_IDS = frozenset({2, 17})
_BOLD_STYLE_MARKERS = frozenset({"bold", "black", "heavy"})
_ITALIC_STYLE_MARKERS = frozenset({"italic", "oblique"})
_CORETEXT_LOOKUP_SCRIPT = (
    "import AppKit, sys\n"
    "font = AppKit.NSFontManager.sharedFontManager()"
    ".fontWithFamily_traits_weight_size_(sys.argv[1], 0, 5, 12)\n"
    "if font is None:\n"
    "    raise SystemExit(1)\n"
    "desc = font.fontDescriptor()\n"
    "url = desc.objectForKey_(AppKit.NSFontURLAttribute)\n"
    "print(url.path() if url is not None else '')\n"
)


def _normalize(value: str) -> str:
    return value.strip().casefold()


def _font_names(path: Path) -> tuple[set[str], set[str]]:
    """Read family/full names and subfamily names from a font file."""

    tt_font_type = TTFont
    if tt_font_type is None:
        return set(), set()

    try:
        with tt_font_type(path) as font:
            name_table = font["name"]
            families: set[str] = set()
            styles: set[str] = set()

            for record in name_table.names:
                value = str(record.toUnicode()).strip()
                if not value:
                    continue
                if record.nameID in _FONT_FAMILY_NAME_IDS:
                    families.add(value)
                if record.nameID in _FONT_STYLE_NAME_IDS:
                    styles.add(value)

            return families, styles
    except KeyError, OSError, RuntimeError, TypeError, ValueError:
        return set(), set()


def _style_score(styles: set[str], *, is_bold: bool, is_italic: bool) -> int:
    style_text = " ".join(styles).casefold()
    has_bold = any(token in style_text for token in _BOLD_STYLE_MARKERS)
    has_italic = any(token in style_text for token in _ITALIC_STYLE_MARKERS)

    score = 0
    if has_bold == is_bold:
        score += 2
    if has_italic == is_italic:
        score += 2
    return score


def _iter_font_files(directories: tuple[Path, ...]) -> list[Path]:
    files: list[Path] = []
    for directory in directories:
        if not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            if path.is_file() and path.suffix.casefold() in _FONT_EXTENSIONS:
                files.append(path)
    return files


def _describe_dirs(label: str, directories: tuple[Path, ...]) -> str:
    return f"{label}: " + ", ".join(str(path) for path in directories)


def _resolve_from_directories(
    family_name: str,
    *,
    is_bold: bool,
    is_italic: bool,
    directories: tuple[Path, ...],
    source: FontSource,
) -> ResolvedFont | None:
    requested = _normalize(family_name)
    matches: list[tuple[int, Path, str]] = []

    for path in _iter_font_files(directories):
        families, styles = _font_names(path)
        normalized_families = {_normalize(family) for family in families}
        if requested not in normalized_families:
            continue

        display_family = next(iter(families), family_name)
        matches.append(
            (
                _style_score(styles, is_bold=is_bold, is_italic=is_italic),
                path,
                display_family,
            )
        )

    if not matches:
        return None

    _score, path, display_family = max(matches, key=lambda match: match[0])
    return ResolvedFont(
        path=str(path),
        family=display_family,
        source=source,
    )


def _fontconfig_pattern(
    family_name: str,
    *,
    is_bold: bool,
    is_italic: bool,
) -> str:
    styles: list[str] = []
    if is_bold:
        styles.append("Bold")
    if is_italic:
        styles.append("Italic")

    if not styles:
        return family_name

    return f"{family_name}:style={' '.join(styles)}"


def _resolve_with_fontconfig(
    family_name: str,
    *,
    is_bold: bool,
    is_italic: bool,
) -> ResolvedFont | None:
    fc_match = shutil.which("fc-match")
    if fc_match is None:
        return None

    try:
        completed = subprocess.run(  # noqa: S603
            [
                fc_match,
                "--format=%{family}\t%{file}\n",
                _fontconfig_pattern(
                    family_name,
                    is_bold=is_bold,
                    is_italic=is_italic,
                ),
            ],
            check=False,
            capture_output=True,
            encoding="utf-8",
            timeout=5,
        )
    except OSError, subprocess.SubprocessError, TimeoutError:
        return None

    if completed.returncode != 0:
        return None

    family, separator, font_path = completed.stdout.strip().partition("\t")
    if not separator or not font_path:
        return None

    requested = _normalize(family_name)
    matched_families = {
        _normalize(candidate)
        for candidate in family.split(",")
        if candidate.strip()
    }
    if requested not in matched_families:
        return None

    return ResolvedFont(
        path=font_path,
        family=family.split(",")[0].strip() or family_name,
        source="fontconfig",
    )


def _resolve_with_coretext(
    family_name: str,
    *,
    is_bold: bool,
    is_italic: bool,
) -> ResolvedFont | None:
    del is_bold, is_italic
    if platform != "darwin":
        return None

    python = shutil.which("python3")
    if python is None:
        return None

    try:
        completed = subprocess.run(  # noqa: S603
            [python, "-c", _CORETEXT_LOOKUP_SCRIPT, family_name],
            check=False,
            capture_output=True,
            encoding="utf-8",
            timeout=5,
        )
    except OSError, subprocess.SubprocessError, TimeoutError:
        return None

    path = completed.stdout.strip()
    if completed.returncode != 0 or not path:
        return None

    return ResolvedFont(path=path, family=family_name, source="coretext")


def _resolve_with_matplotlib(
    family_name: str,
    *,
    is_bold: bool,
    is_italic: bool,
) -> ResolvedFont | None:
    try:
        from matplotlib import font_manager
    except ImportError:
        return None

    font_prop = font_manager.FontProperties(
        family=family_name,
        weight="bold" if is_bold else "normal",
        style="italic" if is_italic else "normal",
    )
    try:
        path = str(font_manager.findfont(font_prop, fallback_to_default=False))
    except ValueError:
        return None

    return ResolvedFont(path=path, family=family_name, source="matplotlib")


def default_user_font_dirs() -> tuple[Path, ...]:
    """Return per-user font directories for the active platform."""

    home = Path.home()
    if platform == "win32":
        return (home / "AppData" / "Local" / "Microsoft" / "Windows" / "Fonts",)
    if platform == "darwin":
        return (home / "Library" / "Fonts",)
    return (home / ".local" / "share" / "fonts", home / ".fonts")


def default_system_font_dirs() -> tuple[Path, ...]:
    """Return system font directories for the active platform."""

    if platform == "win32":
        return (Path("C:/Windows/Fonts"),)
    if platform == "darwin":
        return (Path("/Library/Fonts"), Path("/System/Library/Fonts"))
    return (
        Path("/usr/local/share/fonts"),
        Path("/usr/share/fonts"),
    )


def resolve_font(
    family_name: str,
    *,
    is_bold: bool,
    is_italic: bool,
    font_dirs: tuple[Path, ...] = (),
) -> ResolvedFont:
    """Resolve a concrete font path or raise a diagnostic error."""

    attempts: list[str] = []

    explicit = _resolve_from_directories(
        family_name,
        is_bold=is_bold,
        is_italic=is_italic,
        directories=font_dirs,
        source="explicit",
    )
    if explicit is not None:
        return explicit
    if font_dirs:
        attempts.append(_describe_dirs("explicit font dirs", font_dirs))

    if platform == "linux":
        fontconfig = _resolve_with_fontconfig(
            family_name,
            is_bold=is_bold,
            is_italic=is_italic,
        )
        if fontconfig is not None:
            return fontconfig
        attempts.append("fontconfig")

    if platform == "darwin":
        coretext = _resolve_with_coretext(
            family_name,
            is_bold=is_bold,
            is_italic=is_italic,
        )
        if coretext is not None:
            return coretext
        attempts.append("CoreText")

    user_dirs = default_user_font_dirs()
    user = _resolve_from_directories(
        family_name,
        is_bold=is_bold,
        is_italic=is_italic,
        directories=user_dirs,
        source="user",
    )
    if user is not None:
        return user
    attempts.append(_describe_dirs("user font dirs", user_dirs))

    system_dirs = default_system_font_dirs()
    system = _resolve_from_directories(
        family_name,
        is_bold=is_bold,
        is_italic=is_italic,
        directories=system_dirs,
        source="system",
    )
    if system is not None:
        return system
    attempts.append(_describe_dirs("system font dirs", system_dirs))

    matplotlib = _resolve_with_matplotlib(
        family_name,
        is_bold=is_bold,
        is_italic=is_italic,
    )
    if matplotlib is not None:
        return matplotlib
    attempts.append("matplotlib")

    raise PykaraError(
        "FontMetricsProvider: unknown font family "
        f"{family_name!r}. Tried: {'; '.join(attempts)}."
    )
