"""Tests for font measurement utilities."""

# pyright: reportAttributeAccessIssue=false, reportPrivateUsage=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownMemberType=false

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, cast

import pytest
from _pytest.monkeypatch import MonkeyPatch

from pykara.data import Style
from pykara.errors import DependencyUnavailableError, PykaraError
from pykara.processing import font_metrics
from pykara.processing.font_metrics import (
    FontMetricsProvider,
    TextExtentsProvider,
    _load_backend,
    _make_logfont,
    _measure_backend_win32,
    _measure_raw_text,
    _register_font_dirs_win32,
    _resolve_font_path,
    _shape_width,
    get_font_objects,
    get_gdi_metrics,
    measure_backend,
    reset_font_cache,
)

pytestmark = pytest.mark.unix_only


def make_style(
    *,
    fontname: str = "Noto Sans",
    fontsize: float = 24.0,
    scale_x: float = 100.0,
    scale_y: float = 100.0,
    spacing: float = 0.0,
) -> Style:
    return Style(
        name="Default",
        fontname=fontname,
        fontsize=fontsize,
        primary_colour="&H00FFFFFF",
        secondary_colour="&H000000FF",
        outline_colour="&H00000000",
        back_colour="&H00000000",
        bold=False,
        italic=False,
        underline=False,
        strike_out=False,
        scale_x=scale_x,
        scale_y=scale_y,
        spacing=spacing,
        angle=0.0,
        border_style=1,
        outline=2.0,
        shadow=0.0,
        alignment=2,
        margin_l=10,
        margin_r=10,
        margin_t=10,
        margin_b=10,
        encoding=1,
    )


class TestFontMetricsProvider:
    def test_satisfies_text_extents_protocol(self) -> None:
        provider: TextExtentsProvider = FontMetricsProvider()

        measurement = provider.measure(make_style(), "Hi")

        assert measurement.width > 0

    def test_measures_known_reference_text(self) -> None:
        provider = FontMetricsProvider()
        measurement = provider.measure(make_style(), "Hello")

        assert measurement.width == pytest.approx(
            42.7488986784141,
            abs=0.0001,
        )
        assert measurement.height == pytest.approx(24.0, abs=0.0001)
        assert measurement.descent == pytest.approx(
            5.1629955947136565,
            abs=0.0001,
        )
        assert measurement.extlead == pytest.approx(0.0, abs=0.0001)

    def test_spacing_increases_width(self) -> None:
        provider = FontMetricsProvider()
        compact = provider.measure(make_style(spacing=0.0), "Hello")
        spaced = provider.measure(make_style(spacing=2.0), "Hello")

        assert spaced.width > compact.width

    def test_scale_x_and_scale_y_affect_output_axes(self) -> None:
        provider = FontMetricsProvider()
        base = provider.measure(make_style(scale_x=100.0, scale_y=100.0), "Hi")
        scaled = provider.measure(
            make_style(scale_x=150.0, scale_y=200.0),
            "Hi",
        )

        assert scaled.width == pytest.approx(base.width * 1.5, abs=0.0001)
        assert scaled.height == pytest.approx(base.height * 2.0, abs=0.0001)
        assert scaled.descent == pytest.approx(base.descent * 2.0, abs=0.0001)

    def test_reuses_cached_measurements_for_same_style_and_text(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        reset_font_cache()
        provider = FontMetricsProvider()
        raw_calls = 0

        def fake_measure_raw_text(
            style: Style,
            text: str,
            font_dirs: tuple[object, ...] = (),
        ) -> tuple[float, float, float, float]:
            del style, text, font_dirs
            nonlocal raw_calls
            raw_calls += 1
            return (64.0, 64.0, 16.0, 0.0)

        monkeypatch.setattr(
            font_metrics,
            "_measure_raw_text",
            fake_measure_raw_text,
        )

        first = provider.measure(make_style(), "cached")
        second = provider.measure(make_style(), "cached")

        assert first == second
        assert raw_calls == 1


class TestMeasureRawText:
    def test_dispatches_to_loaded_backend(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        class FakeBackend:
            def measure_backend(
                self,
                style: Style,
                text: str,
                font_dirs: tuple[Path, ...] = (),
            ) -> tuple[float, float, float, float]:
                assert style.fontname == "Noto Sans"
                assert text == "Hi"
                assert font_dirs == (Path("/fonts"),)
                return (1.0, 2.0, 3.0, 4.0)

        monkeypatch.setattr(
            font_metrics,
            "_load_backend",
            lambda: FakeBackend(),
        )

        assert _measure_raw_text(make_style(), "Hi", (Path("/fonts"),)) == (
            1.0,
            2.0,
            3.0,
            4.0,
        )


class TestShapeWidth:
    def test_returns_zero_for_empty_string(self) -> None:
        assert _shape_width(hb_font=None, text="") == 0.0

    def test_sums_shaped_glyph_advances(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        class FakePosition:
            def __init__(self, x_advance: int) -> None:
                self.x_advance = x_advance

        class FakeBuffer:
            def __init__(self) -> None:
                self.glyph_positions: list[FakePosition] | None = None

            def add_str(self, text: str) -> None:
                assert text == "Hi"

            def guess_segment_properties(self) -> None:
                return None

        class FakeHarfBuzz:
            Buffer = FakeBuffer

            @staticmethod
            def shape(
                _hb_font: object,
                buffer: FakeBuffer,
                features: dict[str, bool],
            ) -> None:
                assert features == {"kern": False, "liga": False, "clig": False}
                buffer.glyph_positions = [FakePosition(10), FakePosition(14)]

        monkeypatch.setattr(
            font_metrics,
            "_get_harfbuzz_module",
            lambda: FakeHarfBuzz,
        )

        assert _shape_width(hb_font=object(), text="Hi") == 24.0


class TestResetFontCache:
    def test_resets_backend_and_metrics_caches(self) -> None:
        provider = FontMetricsProvider()
        provider.measure(make_style(), "primed")

        assert (
            font_metrics._FONT_CACHE
            or font_metrics._FONT_METRICS_CACHE
            or font_metrics._MEASUREMENT_CACHE
        )

        reset_font_cache()

        assert not font_metrics._FONT_CACHE
        assert not font_metrics._FONT_METRICS_CACHE
        assert not font_metrics._MEASUREMENT_CACHE


class TestResolveFontPath:
    def test_raises_pykara_error_for_unknown_font(self) -> None:
        with pytest.raises(PykaraError, match="could not load font"):
            _resolve_font_path(
                "this-font-does-not-exist-1234",
                is_bold=False,
                is_italic=False,
            )


class TestGetFontObjects:
    def test_builds_and_caches_freetype_and_harfbuzz_objects(
        self,
        monkeypatch: MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        reset_font_cache()
        font_path = tmp_path / "Cookies.ttf"
        font_path.write_bytes(b"font-data")
        face_calls: list[str] = []

        class FakeFace:
            def __init__(self, path: str) -> None:
                face_calls.append(path)

            @property
            def units_per_EM(self) -> int:  # noqa: N802
                return 1000

        class FakeHbFace:
            def __init__(self, data: bytes) -> None:
                assert data == b"font-data"

        class FakeHbFont:
            def __init__(self, _face: FakeHbFace) -> None:
                self.scale = (0, 0)

        fake_freetype = SimpleNamespace(Face=FakeFace)
        fake_harfbuzz = SimpleNamespace(Face=FakeHbFace, Font=FakeHbFont)

        monkeypatch.setattr(
            font_metrics,
            "_get_freetype_module",
            lambda: fake_freetype,
        )
        monkeypatch.setattr(
            font_metrics,
            "_get_harfbuzz_module",
            lambda: fake_harfbuzz,
        )
        monkeypatch.setattr(
            font_metrics,
            "_resolve_font_path",
            lambda *_args, **_kwargs: str(font_path),
        )

        first = get_font_objects("Cookies", False, False)
        second = get_font_objects("Cookies", False, False)

        assert first is second
        assert face_calls == [str(font_path)]
        hb_font = cast(Any, first[1])
        assert hb_font.scale == (1000, 1000)


class TestGetGdiMetrics:
    def test_returns_cached_metrics_on_second_call(self) -> None:
        reset_font_cache()
        font_metrics._FONT_METRICS_CACHE["cached.ttf"] = (
            1.0,
            2.0,
            3.0,
            4.0,
        )

        assert get_gdi_metrics("cached.ttf", ft_face=None) == (
            1.0,
            2.0,
            3.0,
            4.0,
        )

    def test_uses_units_per_em_when_os2_cell_height_is_invalid(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        reset_font_cache()

        class FakeTTFont:
            def __init__(self, _path: str) -> None:
                return None

            def __enter__(self) -> FakeTTFont:
                return self

            def __exit__(
                self,
                _exc_type: object,
                _exc_value: object,
                _traceback: object,
            ) -> None:
                return None

            def get(self, key: str, default: object = None) -> object:
                if key == "OS/2":
                    return SimpleNamespace(
                        usWinAscent=10,
                        usWinDescent=-20,
                        sTypoAscender=0,
                        sTypoDescender=0,
                        sTypoLineGap=0,
                    )
                return default

            def __contains__(self, _key: str) -> bool:
                return True

        monkeypatch.setattr(font_metrics, "IMPORT_ERROR", None)
        monkeypatch.setattr(font_metrics, "TTFont", FakeTTFont)

        metrics = get_gdi_metrics(
            "invalid-cell.ttf",
            SimpleNamespace(units_per_EM=1000),
        )

        assert metrics == (10.0, -20.0, 1000.0, 0.0)
        reset_font_cache()

    def test_freetype_fallback_uses_units_per_em_for_invalid_cell_height(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        reset_font_cache()

        def raising_ttfont(*_args: object, **_kwargs: object) -> None:
            raise OSError("simulated TTFont failure")

        monkeypatch.setattr(font_metrics, "IMPORT_ERROR", None)
        monkeypatch.setattr(font_metrics, "TTFont", raising_ttfont)

        metrics = get_gdi_metrics(
            "fallback.ttf",
            SimpleNamespace(
                ascender=10,
                descender=20,
                units_per_EM=1000,
                height=1100,
            ),
        )

        assert metrics == (10.0, -20.0, 1000.0, 100.0)
        reset_font_cache()

    def test_falls_back_to_freetype_when_tt_font_raises(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        reset_font_cache()

        def raising_ttfont(*_args: object, **_kwargs: object) -> None:
            raise OSError("simulated TTFont failure")

        ft_face = SimpleNamespace(
            ascender=1000,
            descender=-250,
            units_per_EM=1000,
            height=1300,
        )
        font_path = "fallback.ttf"

        monkeypatch.setattr(font_metrics, "IMPORT_ERROR", None)
        monkeypatch.setattr(font_metrics, "TTFont", raising_ttfont)

        metrics = get_gdi_metrics(font_path, ft_face)

        assert metrics == (1000.0, 250.0, 1250.0, 50.0)
        reset_font_cache()

    def test_raises_when_tt_font_type_is_missing(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        reset_font_cache()
        monkeypatch.setattr(font_metrics, "IMPORT_ERROR", None)
        monkeypatch.setattr(font_metrics, "TTFont", None)

        with pytest.raises(DependencyUnavailableError, match="TTFont"):
            get_gdi_metrics("missing.ttf", ft_face=None)
        reset_font_cache()


class TestRequireDependencies:
    def test_raises_dependency_unavailable_when_imports_failed(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            font_metrics,
            "IMPORT_ERROR",
            ImportError("missing optional dependencies"),
        )

        with pytest.raises(DependencyUnavailableError):
            font_metrics._require_dependencies()

    def test_freetype_getter_raises_when_module_is_none(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(font_metrics, "IMPORT_ERROR", None)
        monkeypatch.setattr(font_metrics, "freetype", None)

        with pytest.raises(DependencyUnavailableError, match="freetype"):
            font_metrics._get_freetype_module()

    def test_harfbuzz_getter_raises_when_module_is_none(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(font_metrics, "IMPORT_ERROR", None)
        monkeypatch.setattr(font_metrics, "hb", None)

        with pytest.raises(DependencyUnavailableError, match="uharfbuzz"):
            font_metrics._get_harfbuzz_module()


class TestLoadBackend:
    def test_returns_backend_module_directly_on_windows(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        _load_backend.cache_clear()
        monkeypatch.setattr(font_metrics, "platform", "win32")

        backend = _load_backend()

        assert backend is font_metrics
        _load_backend.cache_clear()

    def test_returns_backend_module_on_success(self) -> None:
        _load_backend.cache_clear()

        backend = _load_backend()

        assert backend is font_metrics
        _load_backend.cache_clear()

    def test_raises_when_backend_reports_import_error(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        _load_backend.cache_clear()
        monkeypatch.setattr(
            font_metrics,
            "IMPORT_ERROR",
            ImportError("backend missing"),
        )

        with pytest.raises(PykaraError, match="missing dependencies"):
            _load_backend()

        _load_backend.cache_clear()

    def test_raises_when_backend_import_fails(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        _load_backend.cache_clear()
        monkeypatch.setattr(font_metrics, "platform", "linux")

        def raising_import_module(_name: str) -> ModuleType:
            raise ImportError("backend missing")

        monkeypatch.setattr(
            font_metrics,
            "import_module",
            raising_import_module,
        )

        with pytest.raises(PykaraError, match="missing dependencies"):
            _load_backend()

        _load_backend.cache_clear()


class TestMeasureBackend:
    def test_dispatches_to_win32_backend(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(font_metrics, "platform", "win32")
        monkeypatch.setattr(
            font_metrics,
            "_measure_backend_win32",
            lambda style, text, font_dirs=(): (7.0, 8.0, 9.0, 10.0),
        )

        assert measure_backend(make_style(), "Hi") == (7.0, 8.0, 9.0, 10.0)

    def test_non_windows_backend_handles_zero_cell_height(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(font_metrics, "platform", "linux")
        monkeypatch.setattr(
            font_metrics,
            "get_font_objects",
            lambda *_args, **_kwargs: (object(), object(), "/font.ttf"),
        )
        monkeypatch.setattr(
            font_metrics,
            "get_gdi_metrics",
            lambda *_args, **_kwargs: (0.0, 5.0, 0.0, 2.0),
        )
        monkeypatch.setattr(
            font_metrics,
            "_shape_width",
            lambda _hb_font, text: float(len(text) * 10),
        )

        assert measure_backend(make_style(), "Hi") == (20.0, 0.0, 5.0, 2.0)


class FakeGdi32:
    def __init__(
        self,
        *,
        dc: int = 1,
        hfont: int = 2,
        selected_name: str = "Noto Sans",
        text_extent_ok: bool = True,
        text_metrics_ok: bool = True,
        text_face_length: int = 9,
    ) -> None:
        self.dc = dc
        self.hfont = hfont
        self.selected_name = selected_name
        self.text_extent_ok = text_extent_ok
        self.text_metrics_ok = text_metrics_ok
        self.text_face_length = text_face_length
        self.deleted_font = False
        self.deleted_dc = False

    def __getattr__(self, name: str) -> object:
        mapping = {
            "CreateCompatibleDC": self._create_compatible_dc,
            "SetMapMode": self._set_map_mode,
            "CreateFontIndirectW": self._create_font_indirect_w,
            "SelectObject": self._select_object,
            "GetTextFaceW": self._get_text_face_w,
            "GetTextExtentPoint32W": self._get_text_extent_point_32w,
            "GetTextMetricsW": self._get_text_metrics_w,
            "AddFontResourceExW": self._add_font_resource_ex_w,
            "DeleteObject": self._delete_object,
            "DeleteDC": self._delete_dc,
        }
        try:
            return mapping[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def _create_compatible_dc(self, _hdc: object) -> int:
        return self.dc

    def _set_map_mode(self, _dc: int, _mode: int) -> int:
        return 1

    def _create_font_indirect_w(self, _logfont: object) -> int:
        return self.hfont

    def _select_object(self, _dc: int, _font: int) -> int:
        return 3

    def _get_text_face_w(
        self,
        _dc: int,
        _count: int,
        selected_name: object,
    ) -> int:
        cast(Any, selected_name).value = self.selected_name
        return self.text_face_length

    def _get_text_extent_point_32w(
        self,
        _dc: int,
        text: str,
        length: int,
        size_pointer: object,
    ) -> int:
        del length
        size = cast(Any, size_pointer)._obj
        size.cx = len(text) * 10
        size.cy = 20
        return 1 if self.text_extent_ok else 0

    def _get_text_metrics_w(self, _dc: int, metrics_pointer: object) -> int:
        metrics = cast(Any, metrics_pointer)._obj
        metrics.tmDescent = 4
        metrics.tmExternalLeading = 2
        return 1 if self.text_metrics_ok else 0

    def _add_font_resource_ex_w(
        self,
        _path: str,
        _flags: int,
        _reserved: object,
    ) -> int:
        return 1

    def _delete_object(self, _font: int) -> int:
        self.deleted_font = True
        return 1

    def _delete_dc(self, _dc: int) -> int:
        self.deleted_dc = True
        return 1


class TestWin32Helpers:
    def test_register_font_dirs_adds_new_fonts_once(
        self,
        monkeypatch: MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        font_dir = tmp_path / "fonts"
        font_dir.mkdir()
        font_path = font_dir / "Cookies.ttf"
        font_path.write_bytes(b"font")
        (font_dir / "notes.txt").write_text("skip")
        gdi32 = FakeGdi32()
        calls: list[str] = []

        def add_font(path: str, _flags: int, _reserved: object) -> int:
            calls.append(path)
            return 1

        gdi32.AddFontResourceExW = add_font
        monkeypatch.setattr(font_metrics, "platform", "win32")
        monkeypatch.setattr(font_metrics, "gdi32", gdi32, raising=False)
        font_metrics._REGISTERED_WIN32_FONT_PATHS.clear()

        _register_font_dirs_win32((tmp_path / "missing", font_dir))
        _register_font_dirs_win32((font_dir,))

        assert calls == [str(font_path.resolve())]
        font_metrics._REGISTERED_WIN32_FONT_PATHS.clear()

    def test_register_font_dirs_noops_outside_windows(
        self,
        monkeypatch: MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(font_metrics, "platform", "linux")

        _register_font_dirs_win32((tmp_path,))

    def test_make_logfont_copies_style_flags(self) -> None:
        style = replace(
            make_style(fontname="Very Long Font Name That Will Be Truncated"),
            bold=True,
            italic=True,
            underline=True,
            strike_out=True,
            encoding=2,
        )

        logfont = _make_logfont(style, 1536.8)

        assert logfont.lfHeight == 1536
        assert logfont.lfWeight == font_metrics.FW_BOLD
        assert logfont.lfItalic == 1
        assert logfont.lfUnderline == 1
        assert logfont.lfStrikeOut == 1
        assert logfont.lfCharSet == 2
        assert logfont.lfFaceName == style.fontname[:31]

    @pytest.mark.parametrize(
        ("spacing", "expected_width"),
        [(0.0, 20.0), (2.0, 276.0)],
    )
    def test_measure_backend_win32_success(
        self,
        monkeypatch: MonkeyPatch,
        spacing: float,
        expected_width: float,
    ) -> None:
        gdi32 = FakeGdi32()
        monkeypatch.setattr(font_metrics, "platform", "win32")
        monkeypatch.setattr(font_metrics, "gdi32", gdi32, raising=False)

        result = _measure_backend_win32(
            make_style(spacing=spacing),
            "Hi",
        )

        assert result == (expected_width, 20.0, 4.0, 2.0)
        assert gdi32.deleted_font
        assert gdi32.deleted_dc

    @pytest.mark.parametrize(
        ("gdi32", "message"),
        [
            (
                FakeGdi32(dc=0),
                "CreateCompatibleDC failed",
            ),
            (
                FakeGdi32(hfont=0),
                "CreateFontIndirectW failed",
            ),
            (
                FakeGdi32(text_face_length=0),
                "GetTextFaceW failed",
            ),
            (
                FakeGdi32(selected_name="Arial"),
                "could not load font 'Noto Sans' to process the template",
            ),
            (
                FakeGdi32(text_extent_ok=False),
                "non-spacing branch",
            ),
            (
                FakeGdi32(text_metrics_ok=False),
                "GetTextMetricsW failed",
            ),
        ],
    )
    def test_measure_backend_win32_error_paths(
        self,
        monkeypatch: MonkeyPatch,
        gdi32: FakeGdi32,
        message: str,
    ) -> None:
        monkeypatch.setattr(font_metrics, "platform", "win32")
        monkeypatch.setattr(font_metrics, "gdi32", gdi32, raising=False)

        with pytest.raises(PykaraError, match=message):
            _measure_backend_win32(make_style(), "Hi")

    def test_measure_backend_win32_spacing_extent_error(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(font_metrics, "platform", "win32")
        monkeypatch.setattr(
            font_metrics,
            "gdi32",
            FakeGdi32(text_extent_ok=False),
            raising=False,
        )

        with pytest.raises(PykaraError, match="spacing branch"):
            _measure_backend_win32(make_style(spacing=1.0), "Hi")
