"""Tests for frame-baked motion helpers."""

from __future__ import annotations

import re
from typing import cast

import pytest

from pykara.adapters import SubtitleDocument
from pykara.data import Event, Metadata, Style
from pykara.errors import PykaraError
from pykara.fbf import ass_tags as fbf_module
from pykara.fbf import expand_document_to_fbf, line_to_fbf
from pykara.fbf.ass_tags import (
    MotionState,
    alpha_from_tag,
    calc_accel,
    coerce_value,
    collect_initial_data,
    extract_all_tags_from_block,
    extract_t_tags,
    get_alpha_interpolation,
    get_tag_fade,
    get_tag_move,
    get_tag_value_from_block,
    get_time_in_interval,
    inject_pos,
    interpolate_alpha,
    interpolate_color,
    interpolate_shape,
    interpolate_value,
    lerp_tag_move,
    math_clamp,
    math_lerp,
    math_round,
    parse_t_tag,
    remove_move,
    replace_tag_in_block,
)
from pykara.fbf.timeline import ConstantFrameRate, frame_from_ms, ms_from_frame

FPS = 24.0


def make_event(
    text: str,
    start_time: int = 0,
    end_time: int = 1000,
    *,
    comment: bool = False,
) -> Event:
    return Event(
        text=text,
        effect="fx",
        style="Default",
        layer=0,
        start_time=start_time,
        end_time=end_time,
        comment=comment,
        actor="Singer",
        margin_l=0,
        margin_r=0,
        margin_t=0,
        margin_b=0,
    )


def make_document(
    events: list[Event], playback_fps: str | None = None
) -> SubtitleDocument:
    style = Style(
        name="Default",
        fontname="Noto Sans",
        fontsize=40.0,
        primary_colour="&H00FFFFFF",
        secondary_colour="&H0000FFFF",
        outline_colour="&H00000000",
        back_colour="&H64000000",
        bold=False,
        italic=False,
        underline=False,
        strike_out=False,
        scale_x=100.0,
        scale_y=100.0,
        spacing=0.0,
        angle=0.0,
        border_style=1,
        outline=2.0,
        shadow=1.0,
        alignment=2,
        margin_l=10,
        margin_r=10,
        margin_t=20,
        margin_b=20,
        encoding=1,
    )
    raw: dict[str, str] = {}
    if playback_fps is not None:
        raw["PlaybackFPS"] = playback_fps
    return SubtitleDocument(
        metadata=Metadata(res_x=1920, res_y=1080, raw=raw),
        styles={style.name: style},
        events=events,
    )


def tag_values(lines: list[Event], tag_pattern: str) -> list[str]:
    results: list[str] = []
    for line in lines:
        match = re.search(tag_pattern, line.text)
        if match:
            results.append(match.group(1))
    return results


def numeric_tag_values(lines: list[Event], tag_pattern: str) -> list[float]:
    return [float(value) for value in tag_values(lines, tag_pattern)]


def position_values(line_text: str) -> tuple[float, float]:
    match = re.search(r"\\pos\(([\d.-]+),([\d.-]+)\)", line_text)
    assert match is not None
    return float(match.group(1)), float(match.group(2))


def alpha_value(line_text: str) -> int:
    match = re.search(r"\\alpha&H([0-9A-F]{2})&", line_text)
    assert match is not None
    return int(match.group(1), 16)


def test_math_helpers() -> None:
    assert math_clamp(-5, 0, 1) == 0
    assert math_lerp(0.5, 100, 200) == 150
    assert math_round(2.6, 0) == 3


def test_frame_time_conversion() -> None:
    assert ms_from_frame(24, 24.0) == 1000
    assert frame_from_ms(1000, 24.0) == 24
    assert ms_from_frame(0, 24.0) == 0
    assert abs(ms_from_frame(24, 23.976) - 1001) <= 1
    with pytest.raises(PykaraError):
        ConstantFrameRate(0.0)
    with pytest.raises(PykaraError):
        ms_from_frame(-1, 24.0)
    for frame in (0, 12, 24):
        milliseconds = ms_from_frame(frame, 24.0)
        assert frame_from_ms(milliseconds, 24.0) == frame


def test_interpolate_helpers() -> None:
    assert interpolate_alpha(0.5, "&H00&", "&HFF&") == "&H80&"
    assert re.fullmatch(
        r"&H[0-9A-F]{6}&",
        interpolate_color(0.5, "&H0000FF&", "&HFF0000&"),
    )
    assert (
        interpolate_shape(0.5, "m 0 0 l 10 10", "m 0 0 l 20 20")
        == "m 0 0 l 15 15"
    )
    with pytest.raises(
        PykaraError,
        match="clip shape interpolation requires matching point counts",
    ):
        interpolate_shape(0.5, "m 0 0 l 10 10", "m 0 0 l 10 10 20 20")


def test_interpolate_value_rejects_numeric_lists() -> None:
    with pytest.raises(
        PykaraError,
        match="numeric tag interpolation does not accept list values",
    ):
        interpolate_value("frz", 0.5, [1.0], 2.0)  # type: ignore[arg-type]


def test_interpolate_value_other_branches() -> None:
    assert interpolate_value("alpha", 0.5, "&H00&", "&HFF&") == "&H80&"
    assert interpolate_value(
        "clip",
        0.5,
        [0.0, 0.0, 10.0, 10.0],
        [10.0, 20.0, 30.0, 40.0],
    ) == [5.0, 10.0, 20.0, 25.0]
    assert interpolate_value("unknown", 0.5, "keep", "drop") == "keep"


def test_parse_and_extract_transform_tags() -> None:
    start_default, end_default, accel_default, transform_default = parse_t_tag(
        r"\frz360"
    )
    start, end, accel, transform = parse_t_tag(r"0,500,2,\frz360")
    start_accel, end_accel, accel_only, _ = parse_t_tag(r"2,\frz360")
    start_times, end_times, accel_times, _ = parse_t_tag(r"0,500,\frz360")
    start_empty, end_empty, accel_empty, transform_empty = parse_t_tag("")
    assert start_default is None
    assert end_default is None
    assert accel_default == 1.0
    assert "frz" in transform_default
    assert start == 0.0
    assert end == 500.0
    assert accel == 2.0
    assert "frz" in transform
    assert start_accel is None
    assert end_accel is None
    assert accel_only == 2.0
    assert start_times == 0.0
    assert end_times == 500.0
    assert accel_times == 1.0
    assert start_empty is None
    assert end_empty is None
    assert accel_empty == 1.0
    assert transform_empty == ""
    t_list, cleaned = extract_t_tags(r"{\pos(100,100)\frz0\t(\frz360)}")
    multi_t_list, _ = extract_t_tags(r"{\t(0,500,\frz360)\t(500,1000,\blur5)}")
    no_t_list, no_t_cleaned = extract_t_tags(r"{\pos(100,100)\frz45}")
    assert len(t_list) == 1
    assert r"\t(" not in cleaned
    assert r"\pos" in cleaned
    assert r"\frz0" in cleaned
    assert len(multi_t_list) == 2
    assert no_t_list == []
    assert r"\frz45" in no_t_cleaned


def test_collect_initial_data_reads_effective_state() -> None:
    data = collect_initial_data(r"{\frz45\t(\frz360)\move(0,0,100,100)}")
    assert data["frz"] == 45.0
    assert "move" in data


def test_collect_initial_data_more_cases() -> None:
    assert "frz" not in collect_initial_data(r"{\pos(100,100)\t(\frz360)}")
    assert collect_initial_data(r"{\pos(320,240)\t(\frz360)}")["pos"] == [
        320.0,
        240.0,
    ]
    assert "fad" in collect_initial_data(r"{\pos(100,100)\fad(200,200)}")
    assert "fad" not in collect_initial_data(r"{\fad(100,200,300)}")
    assert collect_initial_data(r"{\fade(255,0,255,0,100,900,1000)}")[
        "fade"
    ] == ("fade", 255.0, 0.0, 255.0, 0.0, 100.0, 900.0, 1000.0)
    assert "fade" not in collect_initial_data(r"{\fade(255,0,255,0,100,900)}")
    assert (
        collect_initial_data(r"{\c&H0000FF&\t(\c&HFF0000&)}")["c"]
        == "&H0000FF&"
    )
    assert "move" not in collect_initial_data(r"{\move(10,20,30)}x")


def test_tag_block_utilities() -> None:
    assert get_tag_value_from_block(r"\frz45", "unknown") is None
    assert get_tag_value_from_block(r"\frz45", "frz") == "45"
    assert coerce_value("clip", "1,2,3,4") == [1.0, 2.0, 3.0, 4.0]
    assert remove_move(r"{\move(0,0,100,100)\frz45}") == r"{\frz45}"
    assert (
        fbf_module.remove_tag_from_block(r"{\frz45}", "unknown") == r"{\frz45}"
    )
    assert (
        replace_tag_in_block(
            r"{\clip(0,0,10,10)}", "clip", [1.0, 2.0, 3.0, 4.0]
        )
        == r"{\clip(1,2,3,4)}"
    )
    assert replace_tag_in_block(r"{\fs20}", "fs", "30") == r"{\fs30}"
    assert extract_all_tags_from_block(r"\fs20\fs30\c&H0000FF&\c&HFF0000&") == {
        "c": "&HFF0000&",
        "fs": "30",
    }


def test_move_and_interval_helpers() -> None:
    assert get_time_in_interval(0, 100, 500) == 0.0
    assert get_time_in_interval(600, 100, 500) == 1.0
    assert get_time_in_interval(300, 100, 500) == 0.5
    assert get_time_in_interval(100, 100, 500) == 0.0
    assert get_time_in_interval(500, 100, 500) == 1.0
    assert get_time_in_interval(200, 0, 1000, 2.0) < get_time_in_interval(
        200, 0, 1000, 1.0
    )
    x0, y0, _ = get_tag_move(0, 1000, 0, 0, 500, 300, None, None)
    x1, y1, _ = get_tag_move(1000, 1000, 0, 0, 500, 300, None, None)
    x, y, _ = get_tag_move(500, 1000, 0, 0, 500, 300, None, None)
    x_window_start, _, _ = get_tag_move(200, 1000, 0, 0, 100, 100, 200, 800)
    x_window_end, y_window_end, _ = get_tag_move(
        800, 1000, 0, 0, 100, 100, 200, 800
    )
    x_before, y_before, _ = get_tag_move(100, 1000, 50, 50, 200, 200, 300, 700)
    x_swap, y_swap, _ = get_tag_move(250, 1000, 0, 0, 100, 100, 800, 200)
    assert abs(x0 - 0.0) < 0.01
    assert abs(y0 - 0.0) < 0.01
    assert abs(x1 - 500.0) < 0.01
    assert abs(y1 - 300.0) < 0.01
    assert abs(x - 250.0) < 0.01
    assert abs(y - 150.0) < 0.01
    assert abs(x_window_start - 0.0) < 0.01
    assert abs(x_window_end - 100.0) < 0.01
    assert abs(y_window_end - 100.0) < 0.01
    assert abs(x_before - 50.0) < 0.01
    assert abs(y_before - 50.0) < 0.01
    assert abs(x_swap - 8.33) < 0.05
    assert abs(y_swap - 8.33) < 0.05


def test_alpha_and_fade_helpers() -> None:
    assert get_alpha_interpolation(50, 100, 200, 300, 400, 255, 0, 255) == 255
    fade = ("fad", 200.0, 200.0)
    assert abs(get_tag_fade(500, 1000, 0, fade) - 0.0) < 0.1
    assert abs(get_tag_fade(0, 1000, 0, fade) - 255.0) < 0.1
    assert abs(get_tag_fade(1000, 1000, 0, fade) - 255.0) < 0.1
    assert abs(get_tag_fade(100, 1000, 0, fade) - 127.5) < 1.0
    fade_full = ("fade", 255.0, 0.0, 255.0, 0.0, 200.0, 800.0, 1000.0)
    assert abs(get_tag_fade(500, 1000, 0, fade_full) - 0.0) < 0.1


def test_calc_accel_fallbacks(monkeypatch: pytest.MonkeyPatch) -> None:
    assert abs(calc_accel(0.25, 0.5, 0.75) - 1.0) < 0.01
    assert calc_accel(0.5, 0.5, 0.5) == 1.0
    assert calc_accel(0.0, 0.1, 1.0) > 1.0
    assert calc_accel(0.0, 0.9, 1.0) < 1.0
    accel = calc_accel(0.0, 0.001, 1.0)
    assert 0.01 <= accel <= 100.0
    assert calc_accel(0.0, 0.0, 1.0) == 1.0
    original_log = fbf_module.math.log

    def nan_log(value: float) -> float:
        return float("nan") if value == 0.25 else original_log(value)

    monkeypatch.setattr(fbf_module.math, "log", nan_log)
    assert calc_accel(0.0, 0.25, 1.0) == 1.0


def test_calc_accel_handles_log_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    original_log = fbf_module.math.log
    calls = {"count": 0}

    def flaky_log(value: float) -> float:
        calls["count"] += 1
        if calls["count"] == 2:
            raise ValueError("boom")
        return original_log(value)

    monkeypatch.setattr(fbf_module.math, "log", flaky_log)
    assert calc_accel(0.0, 0.25, 1.0) == 1.0


def test_inject_pos_and_lerp_tag_move() -> None:
    event = make_event(r"{\move(0,0,100,100)}x")
    injected = inject_pos(event, 10, 20)
    assert r"\pos(10,20)" in injected.text
    data = {"move": (0.0, 0.0, 100.0)}
    assert (
        lerp_tag_move(
            0,
            1,
            0,
            40,
            0,
            cast(MotionState, data),
            r"{\move(0,0,100,100)}",
        )
        == r"{\move(0,0,100,100)}"
    )


def test_line_to_fbf_basic_frame_counts() -> None:
    output = line_to_fbf(make_event(r"{\pos(100,100)}Texto"), FPS, step=1)
    assert len(output) == 24
    output_step_2 = line_to_fbf(
        make_event(r"{\pos(100,100)}Texto"), FPS, step=2
    )
    assert len(output_step_2) == 12


def test_line_to_fbf_timing_and_passthrough_cases() -> None:
    output = line_to_fbf(make_event(r"{\pos(100,100)}Texto", 1000, 2000), FPS)
    assert output[0].start_time == 1000
    assert output[-1].end_time == 2000
    for index in range(len(output) - 1):
        assert output[index].end_time == output[index + 1].start_time

    misaligned = line_to_fbf(
        make_event(r"{\pos(100,100)}Texto", 1020, 1100), FPS
    )
    assert [generated.start_time for generated in misaligned] == [
        1020,
        1041,
        1083,
    ]
    assert [generated.end_time for generated in misaligned] == [
        1041,
        1083,
        1100,
    ]

    static = line_to_fbf(make_event(r"{\pos(100,100)\frz45}Texto"), FPS)
    assert all(r"\frz45" in generated.text for generated in static)
    assert line_to_fbf(make_event(r"{\pos(0,0)}x", 1000, 1010), FPS) == [
        make_event(r"{\pos(0,0)}x", 1000, 1010)
    ]
    assert line_to_fbf(make_event(r"{\pos(0,0)}x", 1000, 1000), FPS) == [
        make_event(r"{\pos(0,0)}x", 1000, 1000)
    ]
    plain = line_to_fbf(make_event("hello"), FPS)
    assert len(plain) == 24
    assert all(generated.text == "hello" for generated in plain)


def test_line_to_fbf_rejects_invalid_step() -> None:
    with pytest.raises(
        PykaraError, match="frame-baked expansion step must be >= 1"
    ):
        line_to_fbf(make_event(r"{\pos(0,0)}x"), FPS, step=0)


def test_line_to_fbf_resolves_numeric_transforms() -> None:
    output = line_to_fbf(make_event(r"{\pos(100,100)\frz0\t(\frz360)}"), FPS)
    values = numeric_tag_values(output, r"\\frz([\d.-]+)")
    assert values[0] > 0.0
    assert values[-1] < 360.0
    assert all(r"\t(" not in generated.text for generated in output)


def test_line_to_fbf_numeric_transform_variants() -> None:
    fscx_output = line_to_fbf(
        make_event(r"{\pos(100,100)\fscx100\t(\fscx200)}"), FPS
    )
    fscx_values = numeric_tag_values(fscx_output, r"\\fscx([\d.-]+)")
    assert all(
        fscx_values[index] <= fscx_values[index + 1]
        for index in range(len(fscx_values) - 1)
    )
    assert fscx_values[0] > 100.0
    assert fscx_values[-1] < 200.0
    assert fscx_values[-1] > fscx_values[0]

    blur_output = line_to_fbf(
        make_event(r"{\pos(100,100)\blur0\t(\blur10)}"), FPS
    )
    blur_values = numeric_tag_values(blur_output, r"\\blur([\d.-]+)")
    assert max(blur_values) > 0
    assert max(blur_values) < 10.1

    timed_before = line_to_fbf(
        make_event(r"{\pos(0,0)\fscx100\t(800,1000,\fscx200)}"), FPS
    )
    early = [
        generated for generated in timed_before if generated.end_time <= 800
    ]
    early_values = numeric_tag_values(early, r"\\fscx([\d.-]+)")
    assert all(abs(value - 100.0) < 0.5 for value in early_values)

    timed_after = line_to_fbf(
        make_event(r"{\pos(0,0)\fscx100\t(0,200,\fscx200)}"), FPS
    )
    late = [
        generated for generated in timed_after if generated.start_time >= 200
    ]
    late_values = numeric_tag_values(late, r"\\fscx([\d.-]+)")
    assert all(abs(value - 200.0) < 0.5 for value in late_values)

    accel_two = line_to_fbf(
        make_event(r"{\pos(0,0)\frz0\t(0,1000,2,\frz100)}"), FPS
    )
    accel_values = numeric_tag_values(accel_two, r"\\frz([\d.-]+)")
    assert accel_values[len(accel_values) // 4] < 25.0


def test_line_to_fbf_resolves_move_to_pos() -> None:
    output = line_to_fbf(make_event(r"{\move(0,0,500,300)}"), FPS)
    assert all(r"\pos(" in generated.text for generated in output)
    assert all(r"\move(" not in generated.text for generated in output)
    xs = [position_values(generated.text)[0] for generated in output]
    assert all(xs[index] <= xs[index + 1] for index in range(len(xs) - 1))


def test_line_to_fbf_move_variants() -> None:
    output = line_to_fbf(make_event(r"{\move(100,200,500,300)}"), FPS)
    first_x, first_y = position_values(output[0].text)
    last_x, last_y = position_values(output[-1].text)
    assert first_x < 120
    assert first_y < 210
    assert last_x > 480
    assert last_y > 290

    delayed = line_to_fbf(make_event(r"{\move(0,0,500,300,200,800)}"), FPS)
    early = [generated for generated in delayed if generated.end_time <= 200]
    if early:
        x, _ = position_values(early[0].text)
        assert abs(x - 0.0) < 1

    grouped_before = line_to_fbf(
        make_event(r"{\move(0,0,500,300,800,900)}"), FPS, step=4
    )
    assert r"\move(" not in grouped_before[0].text
    assert r"\pos(0,0)" in grouped_before[0].text

    grouped_after = line_to_fbf(
        make_event(r"{\move(0,0,500,300,100,200)}"), FPS, step=4
    )
    assert r"\move(" not in grouped_after[-1].text
    assert r"\pos(500,300)" in grouped_after[-1].text


def test_line_to_fbf_resolves_fad_to_alpha() -> None:
    output = line_to_fbf(make_event(r"{\pos(0,0)\fad(200,200)}"), FPS)
    assert all(r"\fad(" not in generated.text for generated in output)
    assert all(r"\alpha" in generated.text for generated in output)
    assert alpha_value(output[0].text) > 200
    assert alpha_value(output[len(output) // 2].text) < 10
    assert alpha_value(output[-1].text) > 200


def test_line_to_fbf_fade_variants() -> None:
    output = line_to_fbf(
        make_event(r"{\pos(0,0)\alpha&H80&\fade(255,0,255,0,200,800,1000)}"),
        FPS,
    )
    mid = output[len(output) // 2]
    assert r"\alpha&H80&" in mid.text


def test_line_to_fbf_resolves_color_transform() -> None:
    output = line_to_fbf(
        make_event(r"{\pos(0,0)\c&H0000FF&\t(\c&HFF0000&)}"), FPS
    )
    colors = tag_values(output, r"\\c(&H[0-9A-F]+&)")
    assert len(set(colors)) > 5


def test_line_to_fbf_color_transform_endpoints() -> None:
    output = line_to_fbf(
        make_event(r"{\pos(0,0)\c&H0000FF&\t(\c&HFF0000&)}"), FPS
    )
    first_color = tag_values(output, r"\\c(&H[0-9A-F]+&)")[0]
    last_color = tag_values(output, r"\\c(&H[0-9A-F]+&)")[-1]
    first_blue = int(first_color[2:4], 16)
    first_red = int(first_color[6:8], 16)
    last_blue = int(last_color[2:4], 16)
    last_red = int(last_color[6:8], 16)
    assert first_blue < 30
    assert first_red > 220
    assert last_blue > 220
    assert last_red < 30


def test_line_to_fbf_step_greater_than_one_keeps_compact_transform() -> None:
    output = line_to_fbf(
        make_event(r"{\pos(0,0)\frz0\t(\frz360)}"), FPS, step=2
    )
    assert all(r"\t(" in generated.text for generated in output)


def test_line_to_fbf_grouped_step_behaviors() -> None:
    output_step_1 = line_to_fbf(
        make_event(r"{\pos(0,0)\frz0\t(\frz360)}"), FPS, step=1
    )
    output_step_2 = line_to_fbf(
        make_event(r"{\pos(0,0)\frz0\t(\frz360)}"), FPS, step=2
    )
    assert len(output_step_2) == len(output_step_1) // 2
    for index in range(len(output_step_2) - 1):
        assert (
            output_step_2[index].end_time == output_step_2[index + 1].start_time
        )

    move_grouped = line_to_fbf(
        make_event(r"{\move(0,0,500,300)\frz0\t(\frz360)}"), FPS, step=2
    )
    for generated in move_grouped:
        if r"\move(" in generated.text:
            match = re.search(
                r"\\move\(([\d.-]+),([\d.-]+),([\d.-]+),([\d.-]+)",
                generated.text,
            )
            assert match is not None
            x1, y1, x2, y2 = [
                float(match.group(index)) for index in range(1, 5)
            ]
            assert not (x1 == 0 and y1 == 0 and x2 == 500 and y2 == 300)

    fad_grouped = line_to_fbf(
        make_event(r"{\pos(0,0)\fad(200,200)}"), FPS, step=4
    )
    assert all(r"\fad(" not in generated.text for generated in fad_grouped)
    assert all(r"\alpha" in generated.text for generated in fad_grouped)

    clip_only = line_to_fbf(
        make_event(
            (
                r"{\clip(m 0 0 l 10 0 10 10 0 10)"
                r"\t(\clip(m 0 0 l 20 0 20 20 0 20))}x"
            ),
            1000,
            2000,
        ),
        FPS,
        step=2,
    )
    assert r"\t(" in clip_only[0].text
    assert r"\clip(" in clip_only[0].text
    assert ",)" not in clip_only[0].text

    step_state = line_to_fbf(
        make_event(r"{\fscx100\t(\fscx200)}x", 1000, 2000),
        FPS,
        step=2,
    )
    assert step_state[1].text.startswith(r"{\fscx108")


def test_line_to_fbf_multiple_transforms() -> None:
    output = line_to_fbf(
        make_event(
            r"{\pos(0,0)\fscx100\blur0\t(0,500,\fscx200)\t(500,1000,\blur10)}"
        ),
        FPS,
    )
    assert all(r"\t(" not in generated.text for generated in output)
    values = numeric_tag_values(output, r"\\fscx([\d.-]+)")
    assert values[0] < values[-1]
    assert values[0] < 115
    last_values = numeric_tag_values(output[-3:], r"\\blur([\d.-]+)")
    assert all(value > 7 for value in last_values)


def test_line_to_fbf_combines_move_fad_and_transform() -> None:
    output = line_to_fbf(
        make_event(r"{\move(0,0,960,540)\fad(150,150)\frz0\t(\frz360)}"),
        FPS,
    )
    for generated in output:
        assert r"\move(" not in generated.text
        assert r"\fad(" not in generated.text
        assert r"\t(" not in generated.text
        assert r"\pos(" in generated.text
        assert r"\alpha" in generated.text
        assert r"\frz" in generated.text


def test_line_to_fbf_combination_variants() -> None:
    move_fad = line_to_fbf(
        make_event(r"{\move(0,0,960,540)\fad(150,150)}"), FPS
    )
    xs = [position_values(generated.text)[0] for generated in move_fad]
    assert all(xs[index] <= xs[index + 1] for index in range(len(xs) - 1))

    move_fad_long = line_to_fbf(
        make_event(r"{\move(0,0,960,540)\fad(300,300)}"), FPS
    )
    alphas = [
        alpha_value(generated.text)
        for generated in move_fad_long
        if r"\alpha" in generated.text
    ]
    first_third = alphas[: len(alphas) // 3]
    assert first_third[0] > first_third[-1]

    move_rotation = line_to_fbf(
        make_event(r"{\move(0,0,500,0)\frz0\t(\frz180)}"), FPS
    )
    assert all(r"\pos(" in generated.text for generated in move_rotation)
    assert all(r"\frz" in generated.text for generated in move_rotation)


def test_expand_document_to_fbf_uses_metadata_playbackfps() -> None:
    document = make_document([make_event(r"{\frz0\t(\frz360)}x")], "24")
    expanded = expand_document_to_fbf(document)
    assert len(expanded.events) == 24


def test_expand_document_to_fbf_uses_rational_metadata_playbackfps() -> None:
    document = make_document(
        [make_event(r"{\frz0\t(\frz360)}x")],
        "24000/1001",
    )

    expanded = expand_document_to_fbf(document)

    assert len(expanded.events) == 24


@pytest.mark.parametrize("playback_fps", ["inf", "24000/0"])
def test_expand_document_to_fbf_rejects_invalid_playbackfps(
    playback_fps: str,
) -> None:
    document = make_document(
        [make_event(r"{\frz0\t(\frz360)}x")],
        playback_fps,
    )

    with pytest.raises(
        PykaraError,
        match=(
            "frame-baked expansion requires explicit timecodes or PlaybackFPS"
        ),
    ):
        expand_document_to_fbf(document)


def test_expand_document_to_fbf_uses_dummy_video_fps() -> None:
    document = make_document([make_event(r"{\frz0\t(\frz360)}x")])
    document.metadata.raw["Video File"] = "?dummy:24:40000:1280:720:0:0:0:"
    expanded = expand_document_to_fbf(document)
    assert len(expanded.events) == 24


def test_expand_document_to_fbf_uses_rational_dummy_video_fps() -> None:
    document = make_document([make_event(r"{\frz0\t(\frz360)}x")])
    document.metadata.raw["Video File"] = (
        "?dummy:24000/1001:40000:1280:720:0:0:0:"
    )

    expanded = expand_document_to_fbf(document)

    assert len(expanded.events) == 24


def test_expand_document_to_fbf_prefers_explicit_framerate() -> None:
    document = make_document([make_event(r"{\frz0\t(\frz360)}x")], "12")
    document.metadata.raw["Video File"] = "?dummy:6:40000:1280:720:0:0:0:"
    expanded = expand_document_to_fbf(document, 24.0)
    assert len(expanded.events) == 24


def test_expand_document_to_fbf_preserves_comments_by_default() -> None:
    document = make_document(
        [
            make_event(r"{\frz0\t(\frz360)}x"),
            make_event(r"{\frz0\t(\frz360)}note", comment=True),
        ],
        "24",
    )
    expanded = expand_document_to_fbf(document)
    assert len(expanded.events) == 25
    assert expanded.events[-1].comment is True


def test_expand_document_to_fbf_can_expand_comments() -> None:
    document = make_document(
        [make_event(r"{\frz0\t(\frz360)}x", comment=True)], "24"
    )
    expanded = expand_document_to_fbf(document, include_comments=True)
    assert len(expanded.events) == 24


def test_expand_document_to_fbf_requires_fps() -> None:
    document = make_document([make_event(r"{\frz0\t(\frz360)}x")])
    with pytest.raises(
        PykaraError,
        match=(
            "frame-baked expansion requires explicit timecodes or PlaybackFPS"
        ),
    ):
        expand_document_to_fbf(document)


def test_alpha_from_tag_invalid_payload_returns_zero() -> None:
    assert alpha_from_tag("invalid") == 0.0
