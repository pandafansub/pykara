"""Public text-measurement API."""

# pyright: reportAttributeAccessIssue=false, reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownVariableType=false

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from dataclasses import dataclass
from functools import lru_cache
from importlib import import_module
from pathlib import Path
from typing import Any, Protocol, cast

from pykara.data import Style
from pykara.errors import DependencyUnavailableError, PykaraError
from pykara.processing.font_resolver import (
    font_load_error_message,
    resolve_font,
)

platform = sys.platform


@dataclass(slots=True, frozen=True)
class TextMeasurement:
    """Measured text extents for one string."""

    width: float
    height: float
    descent: float
    extlead: float


RawTextMeasurement = tuple[float, float, float, float]


class TextExtentsProvider(Protocol):
    """Minimal contract for text measurement providers."""

    def measure(self, style: Style, text: str) -> TextMeasurement:
        """Measure text using one subtitle style."""
        ...


class _TextMeasureBackend(Protocol):
    """Minimal contract for private text-measurement backends."""

    def measure_backend(
        self,
        style: Style,
        text: str,
        font_dirs: tuple[Path, ...] = (),
    ) -> RawTextMeasurement:
        """Measure raw backend text metrics for one string."""
        ...


def _scale_metrics(
    *,
    width: float,
    height: float,
    descent: float,
    extlead: float,
    style: Style,
) -> TextMeasurement:
    """Scale raw backend metrics into ASS script coordinates."""

    return TextMeasurement(
        width=style.scale_x / 100.0 * width / 64.0,
        height=style.scale_y / 100.0 * height / 64.0,
        descent=style.scale_y / 100.0 * descent / 64.0,
        extlead=style.scale_y / 100.0 * extlead / 64.0,
    )


@lru_cache(maxsize=1)
def _load_backend() -> _TextMeasureBackend:
    """Load the active platform backend once per process."""

    if platform == "win32":
        return cast(
            _TextMeasureBackend,
            import_module("pykara.processing.font_metrics"),
        )

    try:
        backend = cast(
            _TextMeasureBackend,
            import_module("pykara.processing.font_metrics"),
        )
    except ImportError as exc:
        raise PykaraError(
            "FontMetricsProvider missing dependencies. Install "
            "freetype-py, uharfbuzz, and fonttools."
        ) from exc

    import_error = getattr(backend, "IMPORT_ERROR", None)
    if import_error is not None:
        raise PykaraError(
            "FontMetricsProvider missing dependencies. Install "
            "freetype-py, uharfbuzz, and fonttools."
        ) from import_error

    return backend


def _measure_raw_text(
    style: Style,
    text: str,
    font_dirs: tuple[Path, ...] = (),
) -> RawTextMeasurement:
    """Dispatch to the active platform backend and return raw metrics."""

    backend = _load_backend()
    return backend.measure_backend(style, text, font_dirs)


@dataclass(slots=True, frozen=True)
class FontMetricsProvider(TextExtentsProvider):
    """Measure subtitle text using the active platform backend."""

    font_dirs: tuple[Path, ...] = ()

    def measure(self, style: Style, text: str) -> TextMeasurement:
        """Measure text using the active platform backend.

        Args:
            style: Subtitle style used for measurement.
            text: Plain text to measure.

        Returns:
            Measured text extents in ASS script coordinates.
        """

        cache_key = (style, text, self.font_dirs)
        cached = _MEASUREMENT_CACHE.get(cache_key)
        if cached is not None:
            return cached

        width, height, descent, extlead = _measure_raw_text(
            style,
            text,
            self.font_dirs,
        )
        measurement = _scale_metrics(
            width=width,
            height=height,
            descent=descent,
            extlead=extlead,
            style=style,
        )
        _MEASUREMENT_CACHE[cache_key] = measurement
        return measurement


_import_error: ImportError | None = None

if sys.platform == "win32":
    freetype = None
    hb = None
    TTFont = None
else:
    try:
        import freetype as freetype
        import uharfbuzz as hb
        from fontTools.ttLib import TTFont as TTFont
    except ImportError as exc:
        _import_error = exc
        freetype = None
        hb = None
        TTFont = None

IMPORT_ERROR = _import_error

_FONT_CACHE: dict[
    tuple[str, bool, bool, tuple[Path, ...]], tuple[object, object, str]
] = {}
_FONT_METRICS_CACHE: dict[str, tuple[float, float, float, float]] = {}
_MEASUREMENT_CACHE: dict[
    tuple[Style, str, tuple[Path, ...]], TextMeasurement
] = {}
_HB_FEATURES = {"kern": False, "liga": False, "clig": False}


def reset_font_cache() -> None:
    """Clear all internal font and metrics caches.

    Useful when new fonts are registered at runtime (e.g., in tests) and
    measurements taken before the registration must be invalidated.
    """

    _FONT_CACHE.clear()
    _FONT_METRICS_CACHE.clear()
    _MEASUREMENT_CACHE.clear()
    _load_backend.cache_clear()


def _require_dependencies() -> None:
    """Raise the original import failure when optional deps are unavailable."""

    if IMPORT_ERROR is not None:
        raise DependencyUnavailableError(
            "FontMetricsProvider optional dependencies are unavailable"
        ) from IMPORT_ERROR


def _get_freetype_module() -> object:
    """Return the imported FreeType module after dependency validation."""

    _require_dependencies()

    freetype_module = freetype
    if freetype_module is None:
        raise DependencyUnavailableError("freetype is unavailable")

    return freetype_module


def _get_harfbuzz_module() -> object:
    """Return the imported HarfBuzz module after dependency validation."""

    _require_dependencies()

    harfbuzz_module = hb
    if harfbuzz_module is None:
        raise DependencyUnavailableError("uharfbuzz is unavailable")

    return harfbuzz_module


def _resolve_font_path(
    family_name: str,
    *,
    is_bold: bool,
    is_italic: bool,
    font_dirs: tuple[Path, ...] = (),
) -> str:
    """Resolve one concrete font path or raise a lookup error."""

    resolved = resolve_font(
        family_name,
        is_bold=is_bold,
        is_italic=is_italic,
        font_dirs=font_dirs,
    )
    return resolved.path


def get_font_objects(
    family_name: str,
    is_bold: bool,
    is_italic: bool,
    font_dirs: tuple[Path, ...] = (),
) -> tuple[object, object, str]:
    """Resolve and cache the FreeType/HarfBuzz objects for one font face."""

    cache_key = (family_name, is_bold, is_italic, font_dirs)
    cached = _FONT_CACHE.get(cache_key)
    if cached is not None:
        return cached

    freetype_module = cast(Any, _get_freetype_module())
    harfbuzz_module = cast(Any, _get_harfbuzz_module())
    font_path = _resolve_font_path(
        family_name,
        is_bold=is_bold,
        is_italic=is_italic,
        font_dirs=font_dirs,
    )

    ft_face = freetype_module.Face(font_path)
    with Path(font_path).open("rb") as handle:
        font_data = handle.read()

    hb_face = harfbuzz_module.Face(font_data)
    hb_font = harfbuzz_module.Font(hb_face)
    hb_font.scale = (ft_face.units_per_EM, ft_face.units_per_EM)

    resolved = (ft_face, hb_font, font_path)
    _FONT_CACHE[cache_key] = resolved
    return resolved


def get_gdi_metrics(
    font_path: str,
    ft_face: object,
) -> tuple[float, float, float, float]:
    """Extract stable metrics that approximate the GDI cell box."""

    _require_dependencies()

    cached = _FONT_METRICS_CACHE.get(font_path)
    if cached is not None:
        return cached

    tt_font_type = TTFont
    if tt_font_type is None:
        raise DependencyUnavailableError("TTFont is unavailable")

    try:
        font = cast(Any, tt_font_type(font_path))
    except (
        AttributeError,
        KeyError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ):
        font = None
    if font is not None:
        try:
            os2 = font.get("OS/2", None)
            is_cff = "CFF " in font

            if os2 is not None and os2.usWinAscent != 0:
                win_ascent = float(os2.usWinAscent)
                win_descent = float(os2.usWinDescent)
                cell_height = win_ascent + win_descent
                if cell_height <= 0:
                    cell_height = float(ft_face.units_per_EM)

                if is_cff:
                    extlead = 0.0
                else:
                    typo_height = float(
                        os2.sTypoAscender
                        - os2.sTypoDescender
                        + os2.sTypoLineGap
                    )
                    extlead = max(0.0, typo_height - cell_height)

                metrics = (win_ascent, win_descent, cell_height, extlead)
                _FONT_METRICS_CACHE[font_path] = metrics
                return metrics
        except (
            AttributeError,
            KeyError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ):
            pass
        finally:
            close = getattr(font, "close", None)
            if callable(close):
                close()

    face = cast(Any, ft_face)
    ascender = float(face.ascender)
    descent = float(-face.descender)
    cell_height = ascender + descent
    if cell_height <= 0:
        cell_height = float(face.units_per_EM)

    extlead = max(0.0, float(face.height) - cell_height)
    metrics = (ascender, descent, cell_height, extlead)
    _FONT_METRICS_CACHE[font_path] = metrics
    return metrics


def _shape_width(hb_font: object, text: str) -> float:
    """Shape one string and return the HarfBuzz x advance sum."""

    if not text:
        return 0.0

    harfbuzz_module = cast(Any, _get_harfbuzz_module())
    buffer = harfbuzz_module.Buffer()
    buffer.add_str(text)
    buffer.guess_segment_properties()
    harfbuzz_module.shape(hb_font, buffer, _HB_FEATURES)
    glyph_positions = buffer.glyph_positions or ()
    return float(sum(position.x_advance for position in glyph_positions))


def measure_backend(
    style: Style,
    text: str,
    font_dirs: tuple[Path, ...] = (),
) -> tuple[float, float, float, float]:
    """Measure text and return raw backend metrics before final ASS scaling."""

    if platform == "win32":
        return _measure_backend_win32(style, text, font_dirs)

    ft_face, hb_font, font_path = get_font_objects(
        style.fontname,
        style.bold,
        style.italic,
        font_dirs,
    )
    _win_ascent, win_descent, cell_height_du, extlead_du = get_gdi_metrics(
        font_path,
        ft_face,
    )

    fontsize_64 = style.fontsize * 64.0
    scale = fontsize_64 / cell_height_du if cell_height_du > 0 else 1.0

    width_64 = 0.0
    spacing_64 = style.spacing * 64.0

    if spacing_64 != 0:
        for char in text:
            width_64 += _shape_width(hb_font, char) * scale + spacing_64
    else:
        width_64 = _shape_width(hb_font, text) * scale

    return (
        width_64,
        cell_height_du * scale,
        win_descent * scale,
        extlead_du * scale,
    )


MM_TEXT = 1
FW_NORMAL = 400
FW_BOLD = 700
OUT_TT_PRECIS = 4
CLIP_DEFAULT_PRECIS = 0
ANTIALIASED_QUALITY = 4
DEFAULT_PITCH = 0
FF_DONTCARE = 0
FR_PRIVATE = 0x10


class SIZE(ctypes.Structure):
    """Win32 text size structure."""

    _fields_ = [
        ("cx", wintypes.LONG),
        ("cy", wintypes.LONG),
    ]


class LOGFONTW(ctypes.Structure):
    """Win32 logical font definition."""

    _fields_ = [
        ("lfHeight", wintypes.LONG),
        ("lfWidth", wintypes.LONG),
        ("lfEscapement", wintypes.LONG),
        ("lfOrientation", wintypes.LONG),
        ("lfWeight", wintypes.LONG),
        ("lfItalic", wintypes.BYTE),
        ("lfUnderline", wintypes.BYTE),
        ("lfStrikeOut", wintypes.BYTE),
        ("lfCharSet", wintypes.BYTE),
        ("lfOutPrecision", wintypes.BYTE),
        ("lfClipPrecision", wintypes.BYTE),
        ("lfQuality", wintypes.BYTE),
        ("lfPitchAndFamily", wintypes.BYTE),
        ("lfFaceName", wintypes.WCHAR * 32),
    ]


class TEXTMETRICW(ctypes.Structure):
    """Win32 text metric structure."""

    _fields_ = [
        ("tmHeight", wintypes.LONG),
        ("tmAscent", wintypes.LONG),
        ("tmDescent", wintypes.LONG),
        ("tmInternalLeading", wintypes.LONG),
        ("tmExternalLeading", wintypes.LONG),
        ("tmAveCharWidth", wintypes.LONG),
        ("tmMaxCharWidth", wintypes.LONG),
        ("tmWeight", wintypes.LONG),
        ("tmOverhang", wintypes.LONG),
        ("tmDigitizedAspectX", wintypes.LONG),
        ("tmDigitizedAspectY", wintypes.LONG),
        ("tmFirstChar", wintypes.WCHAR),
        ("tmLastChar", wintypes.WCHAR),
        ("tmDefaultChar", wintypes.WCHAR),
        ("tmBreakChar", wintypes.WCHAR),
        ("tmItalic", wintypes.BYTE),
        ("tmUnderlined", wintypes.BYTE),
        ("tmStruckOut", wintypes.BYTE),
        ("tmPitchAndFamily", wintypes.BYTE),
        ("tmCharSet", wintypes.BYTE),
    ]


if sys.platform == "win32":
    gdi32 = ctypes.WinDLL("gdi32")

    gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi32.CreateCompatibleDC.restype = wintypes.HDC

    gdi32.SetMapMode.argtypes = [wintypes.HDC, ctypes.c_int]
    gdi32.SetMapMode.restype = ctypes.c_int

    gdi32.CreateFontIndirectW.argtypes = [ctypes.POINTER(LOGFONTW)]
    gdi32.CreateFontIndirectW.restype = wintypes.HFONT

    gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    gdi32.SelectObject.restype = wintypes.HGDIOBJ

    gdi32.GetTextExtentPoint32W.argtypes = [
        wintypes.HDC,
        wintypes.LPCWSTR,
        ctypes.c_int,
        ctypes.POINTER(SIZE),
    ]
    gdi32.GetTextExtentPoint32W.restype = wintypes.BOOL

    gdi32.GetTextMetricsW.argtypes = [wintypes.HDC, ctypes.POINTER(TEXTMETRICW)]
    gdi32.GetTextMetricsW.restype = wintypes.BOOL

    gdi32.GetTextFaceW.argtypes = [
        wintypes.HDC,
        ctypes.c_int,
        wintypes.LPWSTR,
    ]
    gdi32.GetTextFaceW.restype = ctypes.c_int

    gdi32.AddFontResourceExW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.LPVOID,
    ]
    gdi32.AddFontResourceExW.restype = ctypes.c_int

    gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi32.DeleteObject.restype = wintypes.BOOL

    gdi32.DeleteDC.argtypes = [wintypes.HDC]
    gdi32.DeleteDC.restype = wintypes.BOOL
else:
    gdi32 = None


_REGISTERED_WIN32_FONT_PATHS: set[str] = set()


def _register_font_dirs_win32(font_dirs: tuple[Path, ...]) -> None:
    """Make explicit font directories visible to this process on Windows."""

    if platform != "win32":
        return

    for directory in font_dirs:
        if not directory.is_dir():
            continue

        for path in directory.rglob("*"):
            if not path.is_file() or path.suffix.casefold() not in {
                ".ttf",
                ".otf",
            }:
                continue

            resolved = str(path.resolve())
            if resolved in _REGISTERED_WIN32_FONT_PATHS:
                continue

            if gdi32.AddFontResourceExW(resolved, FR_PRIVATE, None) > 0:
                _REGISTERED_WIN32_FONT_PATHS.add(resolved)


def _make_logfont(style: Style, fontsize: float) -> LOGFONTW:
    """Build a Win32 logical font from an ASS style."""

    logfont = LOGFONTW()
    ctypes.memset(ctypes.byref(logfont), 0, ctypes.sizeof(logfont))
    logfont.lfHeight = int(fontsize)
    logfont.lfWeight = FW_BOLD if style.bold else FW_NORMAL
    logfont.lfItalic = 1 if style.italic else 0
    logfont.lfUnderline = 1 if style.underline else 0
    logfont.lfStrikeOut = 1 if style.strike_out else 0
    logfont.lfCharSet = int(style.encoding)
    logfont.lfOutPrecision = OUT_TT_PRECIS
    logfont.lfClipPrecision = CLIP_DEFAULT_PRECIS
    logfont.lfQuality = ANTIALIASED_QUALITY
    logfont.lfPitchAndFamily = DEFAULT_PITCH | FF_DONTCARE
    logfont.lfFaceName = style.fontname[:31]
    return logfont


def _measure_backend_win32(
    style: Style,
    text: str,
    font_dirs: tuple[Path, ...] = (),
) -> tuple[float, float, float, float]:
    """Measure text and return raw backend metrics before final ASS scaling."""

    width = 0.0
    height = 0.0
    descent = 0.0
    extlead = 0.0

    fontsize = style.fontsize * 64.0
    spacing = style.spacing * 64.0

    _register_font_dirs_win32(font_dirs)

    dc = gdi32.CreateCompatibleDC(None)
    if not dc:
        raise PykaraError(
            "FontMetricsProvider backend error: CreateCompatibleDC failed"
        )

    try:
        gdi32.SetMapMode(dc, MM_TEXT)
        logfont = _make_logfont(style, fontsize)
        hfont = gdi32.CreateFontIndirectW(ctypes.byref(logfont))
        if not hfont:
            raise PykaraError(
                "FontMetricsProvider backend error: CreateFontIndirectW failed"
            )

        try:
            old_font = gdi32.SelectObject(dc, hfont)
            try:
                selected_name = ctypes.create_unicode_buffer(32)
                name_length = gdi32.GetTextFaceW(dc, 32, selected_name)
                if name_length <= 0:
                    raise PykaraError(
                        "FontMetricsProvider backend error: GetTextFaceW failed"
                    )
                if selected_name.value.casefold() != style.fontname.casefold():
                    raise PykaraError(font_load_error_message(style.fontname))

                size = SIZE()

                if spacing != 0:
                    for char in text:
                        ok = gdi32.GetTextExtentPoint32W(
                            dc,
                            char,
                            1,
                            ctypes.byref(size),
                        )
                        if not ok:
                            raise PykaraError(
                                "FontMetricsProvider backend error: "
                                "GetTextExtentPoint32W failed in spacing branch"
                            )
                        width += size.cx + spacing
                        height = float(size.cy)
                else:
                    ok = gdi32.GetTextExtentPoint32W(
                        dc,
                        text,
                        len(text),
                        ctypes.byref(size),
                    )
                    if not ok:
                        raise PykaraError(
                            "FontMetricsProvider backend error: "
                            "GetTextExtentPoint32W failed in non-spacing branch"
                        )
                    width = float(size.cx)
                    height = float(size.cy)

                metrics = TEXTMETRICW()
                ok = gdi32.GetTextMetricsW(dc, ctypes.byref(metrics))
                if not ok:
                    raise PykaraError(
                        "FontMetricsProvider backend error: "
                        "GetTextMetricsW failed"
                    )

                descent = float(metrics.tmDescent)
                extlead = float(metrics.tmExternalLeading)
            finally:
                gdi32.SelectObject(dc, old_font)
        finally:
            gdi32.DeleteObject(hfont)
    finally:
        gdi32.DeleteDC(dc)

    return (width, height, descent, extlead)
