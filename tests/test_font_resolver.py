"""Tests for platform-aware font resolution."""

# pyright: reportAttributeAccessIssue=false, reportPrivateUsage=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Self

import pytest
from _pytest.monkeypatch import MonkeyPatch

from pykara.errors import PykaraError
from pykara.processing import font_resolver
from pykara.processing.font_resolver import (
    ResolvedFont,
    _font_names,
    _fontconfig_pattern,
    _resolve_with_coretext,
    _resolve_with_fontconfig,
    _resolve_with_matplotlib,
    default_system_font_dirs,
    default_user_font_dirs,
    resolve_font,
)

_FONT_PATH = (
    Path(__file__).parent / "fixtures" / "fonts" / "NotoSans-Regular.ttf"
)


@dataclass(slots=True)
class FakeNameRecord:
    nameID: int  # noqa: N815
    value: str

    def toUnicode(self) -> str:  # noqa: N802
        return self.value


class FakeTTFont:
    def __init__(self, _path: Path) -> None:
        self._name_table = SimpleNamespace(
            names=[
                FakeNameRecord(1, "Cookies"),
                FakeNameRecord(2, "Bold Italic"),
                FakeNameRecord(4, "Cookies Regular"),
                FakeNameRecord(16, ""),
                FakeNameRecord(17, "Display"),
            ]
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        _exc_type: object,
        _exc_value: object,
        _traceback: object,
    ) -> None:
        return None

    def __getitem__(self, key: str) -> object:
        if key != "name":
            raise KeyError(key)
        return self._name_table


class RaisingTTFont:
    def __init__(self, _path: Path) -> None:
        raise OSError("invalid font")


class TestFontNames:
    def test_returns_empty_names_when_fonttools_is_unavailable(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(font_resolver, "TTFont", None)

        assert _font_names(Path("missing.ttf")) == (set(), set())

    def test_reads_family_and_style_names(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(font_resolver, "TTFont", FakeTTFont)

        families, styles = _font_names(Path("Cookies.ttf"))

        assert families == {"Cookies", "Cookies Regular"}
        assert styles == {"Bold Italic", "Display"}

    def test_returns_empty_names_when_font_cannot_be_read(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(font_resolver, "TTFont", RaisingTTFont)

        assert _font_names(Path("broken.ttf")) == (set(), set())


class TestResolveFont:
    def test_prefers_explicit_font_dirs(self, tmp_path: Path) -> None:
        font_dir = tmp_path / "fonts"
        font_dir.mkdir()
        font_path = font_dir / "NotoSans-Regular.ttf"
        font_path.write_bytes(_FONT_PATH.read_bytes())

        resolved = resolve_font(
            "Noto Sans",
            is_bold=False,
            is_italic=False,
            font_dirs=(font_dir,),
        )

        assert resolved.path == str(font_path)
        assert resolved.source == "explicit"

    def test_raises_diagnostic_error_for_unknown_font(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        def missing_resolver(*_args: object, **_kwargs: object) -> None:
            return None

        monkeypatch.setattr(font_resolver, "platform", "linux")
        monkeypatch.setattr(
            font_resolver,
            "_resolve_with_fontconfig",
            missing_resolver,
        )
        monkeypatch.setattr(
            font_resolver,
            "_resolve_with_matplotlib",
            missing_resolver,
        )
        monkeypatch.setattr(
            font_resolver,
            "default_user_font_dirs",
            lambda: (Path("/missing/user/fonts"),),
        )
        monkeypatch.setattr(
            font_resolver,
            "default_system_font_dirs",
            lambda: (Path("/missing/system/fonts"),),
        )

        with pytest.raises(PykaraError, match="Tried: fontconfig"):
            resolve_font(
                "this-font-does-not-exist-1234",
                is_bold=False,
                is_italic=False,
            )

    def test_returns_coretext_result_on_macos(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        resolved_font = ResolvedFont(
            path="/Library/Fonts/Cookies.ttf",
            family="Cookies",
            source="coretext",
        )

        monkeypatch.setattr(font_resolver, "platform", "darwin")
        monkeypatch.setattr(
            font_resolver,
            "_resolve_with_coretext",
            lambda *_args, **_kwargs: resolved_font,
        )
        monkeypatch.setattr(
            font_resolver,
            "_resolve_from_directories",
            lambda *_args, **_kwargs: None,
        )

        assert (
            resolve_font("Cookies", is_bold=False, is_italic=False)
            == resolved_font
        )

    def test_returns_user_system_and_matplotlib_results(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        def missing_directory_resolver(
            *_args: object,
            source: str,
            **_kwargs: object,
        ) -> ResolvedFont | None:
            if source == "system":
                return ResolvedFont(
                    path="/usr/share/fonts/Cookies.ttf",
                    family="Cookies",
                    source="system",
                )
            return None

        monkeypatch.setattr(font_resolver, "platform", "freebsd")
        monkeypatch.setattr(
            font_resolver,
            "_resolve_from_directories",
            lambda *_args, **_kwargs: ResolvedFont(
                path="/home/user/.fonts/Cookies.ttf",
                family="Cookies",
                source="user",
            ),
        )

        user = resolve_font("Cookies", is_bold=False, is_italic=False)
        assert user.source == "user"

        monkeypatch.setattr(
            font_resolver,
            "_resolve_from_directories",
            missing_directory_resolver,
        )
        system = resolve_font("Cookies", is_bold=False, is_italic=False)
        assert system.source == "system"

        monkeypatch.setattr(
            font_resolver,
            "_resolve_from_directories",
            lambda *_args, **_kwargs: None,
        )
        monkeypatch.setattr(
            font_resolver,
            "_resolve_with_matplotlib",
            lambda *_args, **_kwargs: ResolvedFont(
                path="/matplotlib/Cookies.ttf",
                family="Cookies",
                source="matplotlib",
            ),
        )

        matplotlib = resolve_font("Cookies", is_bold=False, is_italic=False)
        assert matplotlib.source == "matplotlib"


class TestFontconfig:
    @staticmethod
    def find_fc_match(_name: str) -> str:
        return "fc-match"

    def test_accepts_matching_fontconfig_family(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        captured_args: list[str] = []

        def fake_run(
            args: list[str],
            *_args: object,
            **_kwargs: object,
        ) -> object:
            captured_args.extend(args)
            return subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="Cookies\t/home/user/.fonts/Cookies.ttf\n",
                stderr="",
            )

        monkeypatch.setattr(
            font_resolver.shutil,
            "which",
            self.find_fc_match,
        )
        monkeypatch.setattr(font_resolver.subprocess, "run", fake_run)

        resolved = _resolve_with_fontconfig(
            "Cookies",
            is_bold=False,
            is_italic=False,
        )

        assert resolved is not None
        assert resolved.path == "/home/user/.fonts/Cookies.ttf"
        assert resolved.source == "fontconfig"
        assert captured_args[-1] == "Cookies"

    def test_rejects_fontconfig_default_for_unknown_font(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        def fake_run(*_args: object, **_kwargs: object) -> object:
            return subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="Noto Sans\t/usr/share/fonts/NotoSans-Regular.ttf\n",
                stderr="",
            )

        monkeypatch.setattr(
            font_resolver.shutil,
            "which",
            self.find_fc_match,
        )
        monkeypatch.setattr(font_resolver.subprocess, "run", fake_run)

        assert (
            _resolve_with_fontconfig(
                "this-font-does-not-exist-1234",
                is_bold=False,
                is_italic=False,
            )
            is None
        )

    def test_builds_bold_italic_fontconfig_pattern(self) -> None:
        assert (
            _fontconfig_pattern("Cookies", is_bold=True, is_italic=True)
            == "Cookies:style=Bold Italic"
        )

    def test_returns_none_when_fontconfig_is_unavailable(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(font_resolver.shutil, "which", lambda _name: None)

        assert (
            _resolve_with_fontconfig(
                "Cookies",
                is_bold=False,
                is_italic=False,
            )
            is None
        )

    @pytest.mark.parametrize(
        "completed",
        [
            subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="",
                stderr="",
            ),
            subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="Cookies only\n",
                stderr="",
            ),
        ],
    )
    def test_returns_none_for_failed_or_malformed_fontconfig_output(
        self,
        monkeypatch: MonkeyPatch,
        completed: subprocess.CompletedProcess[str],
    ) -> None:
        monkeypatch.setattr(
            font_resolver.shutil,
            "which",
            self.find_fc_match,
        )
        monkeypatch.setattr(
            font_resolver.subprocess,
            "run",
            lambda *_args, **_kwargs: completed,
        )

        assert (
            _resolve_with_fontconfig(
                "Cookies",
                is_bold=True,
                is_italic=True,
            )
            is None
        )

    def test_returns_none_when_fontconfig_command_raises(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        def raising_run(*_args: object, **_kwargs: object) -> object:
            raise subprocess.SubprocessError("boom")

        monkeypatch.setattr(
            font_resolver.shutil,
            "which",
            self.find_fc_match,
        )
        monkeypatch.setattr(font_resolver.subprocess, "run", raising_run)

        assert (
            _resolve_with_fontconfig(
                "Cookies",
                is_bold=False,
                is_italic=False,
            )
            is None
        )


class TestCoreText:
    def test_returns_none_outside_macos(self, monkeypatch: MonkeyPatch) -> None:
        monkeypatch.setattr(font_resolver, "platform", "linux")

        assert (
            _resolve_with_coretext("Cookies", is_bold=False, is_italic=False)
            is None
        )

    def test_returns_none_when_python_is_unavailable(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(font_resolver, "platform", "darwin")
        monkeypatch.setattr(font_resolver.shutil, "which", lambda _name: None)

        assert (
            _resolve_with_coretext("Cookies", is_bold=False, is_italic=False)
            is None
        )

    def test_accepts_coretext_path(self, monkeypatch: MonkeyPatch) -> None:
        def fake_run(*_args: object, **_kwargs: object) -> object:
            return subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="/Library/Fonts/Cookies.ttf\n",
                stderr="",
            )

        monkeypatch.setattr(font_resolver, "platform", "darwin")
        monkeypatch.setattr(
            font_resolver.shutil,
            "which",
            lambda _name: "/usr/bin/python3",
        )
        monkeypatch.setattr(font_resolver.subprocess, "run", fake_run)

        resolved = _resolve_with_coretext(
            "Cookies",
            is_bold=False,
            is_italic=False,
        )

        assert resolved == ResolvedFont(
            path="/Library/Fonts/Cookies.ttf",
            family="Cookies",
            source="coretext",
        )

    @pytest.mark.parametrize(
        "completed",
        [
            subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="",
                stderr="",
            ),
            subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="",
                stderr="",
            ),
        ],
    )
    def test_returns_none_for_failed_coretext_lookup(
        self,
        monkeypatch: MonkeyPatch,
        completed: subprocess.CompletedProcess[str],
    ) -> None:
        monkeypatch.setattr(font_resolver, "platform", "darwin")
        monkeypatch.setattr(
            font_resolver.shutil,
            "which",
            lambda _name: "/usr/bin/python3",
        )
        monkeypatch.setattr(
            font_resolver.subprocess,
            "run",
            lambda *_args, **_kwargs: completed,
        )

        assert (
            _resolve_with_coretext("Cookies", is_bold=False, is_italic=False)
            is None
        )

    def test_returns_none_when_coretext_command_raises(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        def raising_run(*_args: object, **_kwargs: object) -> object:
            raise TimeoutError

        monkeypatch.setattr(font_resolver, "platform", "darwin")
        monkeypatch.setattr(
            font_resolver.shutil,
            "which",
            lambda _name: "/usr/bin/python3",
        )
        monkeypatch.setattr(font_resolver.subprocess, "run", raising_run)

        assert (
            _resolve_with_coretext("Cookies", is_bold=False, is_italic=False)
            is None
        )


class TestMatplotlibResolver:
    def test_returns_none_when_matplotlib_is_unavailable(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        monkeypatch.setitem(sys.modules, "matplotlib", None)

        assert (
            _resolve_with_matplotlib("Cookies", is_bold=False, is_italic=False)
            is None
        )

    def test_returns_matplotlib_font(self, monkeypatch: MonkeyPatch) -> None:
        captured: dict[str, Any] = {}

        class FakeFontProperties:
            def __init__(
                self,
                *,
                family: str,
                weight: str,
                style: str,
            ) -> None:
                captured.update(
                    family=family,
                    weight=weight,
                    style=style,
                )

        fake_font_manager = SimpleNamespace(
            FontProperties=FakeFontProperties,
            findfont=lambda *_args, **_kwargs: "/mpl/Cookies-BoldItalic.ttf",
        )
        matplotlib_module = ModuleType("matplotlib")
        monkeypatch.setattr(
            matplotlib_module,
            "font_manager",
            fake_font_manager,
            raising=False,
        )
        monkeypatch.setitem(sys.modules, "matplotlib", matplotlib_module)

        resolved = _resolve_with_matplotlib(
            "Cookies",
            is_bold=True,
            is_italic=True,
        )

        assert resolved == ResolvedFont(
            path="/mpl/Cookies-BoldItalic.ttf",
            family="Cookies",
            source="matplotlib",
        )
        assert captured == {
            "family": "Cookies",
            "weight": "bold",
            "style": "italic",
        }

    def test_returns_none_when_matplotlib_refuses_font(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        fake_font_manager = SimpleNamespace(
            FontProperties=lambda **_kwargs: object(),
            findfont=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                ValueError("missing")
            ),
        )
        matplotlib_module = ModuleType("matplotlib")
        monkeypatch.setattr(
            matplotlib_module,
            "font_manager",
            fake_font_manager,
            raising=False,
        )
        monkeypatch.setitem(sys.modules, "matplotlib", matplotlib_module)

        assert (
            _resolve_with_matplotlib("Cookies", is_bold=False, is_italic=False)
            is None
        )


class TestDefaultFontDirs:
    def test_default_user_font_dirs_follow_platform(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(font_resolver, "platform", "win32")
        assert (
            default_user_font_dirs()[0]
            .as_posix()
            .endswith("Microsoft/Windows/Fonts")
        )

        monkeypatch.setattr(font_resolver, "platform", "darwin")
        assert default_user_font_dirs()[0].as_posix().endswith("Library/Fonts")

    def test_default_system_font_dirs_follow_platform(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(font_resolver, "platform", "win32")
        assert default_system_font_dirs() == (Path("C:/Windows/Fonts"),)

        monkeypatch.setattr(font_resolver, "platform", "darwin")
        assert default_system_font_dirs() == (
            Path("/Library/Fonts"),
            Path("/System/Library/Fonts"),
        )
