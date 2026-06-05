"""Unit tests for the karaoke parser."""

from __future__ import annotations

from pykara.data import Event
from pykara.parsing import KaraokeParser


def make_event(text: str) -> Event:
    return Event(
        text=text,
        effect="karaoke",
        style="Default",
        layer=0,
        start_time=0,
        end_time=0,
        comment=False,
        actor="",
        margin_l=0,
        margin_r=0,
        margin_t=0,
        margin_b=0,
    )


class TestKaraokeParser:
    def test_parse_supports_k_tag_with_source_order_indexes(self) -> None:
        parser = KaraokeParser()

        karaoke = parser.parse(make_event("intro {\\k20}ka{\\k30}ra"))

        first_syllable = karaoke.syllables[0]
        second_syllable = karaoke.syllables[1]
        third_syllable = karaoke.syllables[2]

        assert karaoke.text == "intro kara"
        assert karaoke.trimmed_text == "intro kara"
        assert len(karaoke.syllables) == 3

        assert first_syllable.index == 0
        assert first_syllable.text == "intro "
        assert first_syllable.duration == 0
        assert first_syllable.highlights == []

        assert second_syllable.index == 1
        assert second_syllable.tag == "\\k20"
        assert second_syllable.start_time == 0
        assert second_syllable.end_time == 200
        assert second_syllable.duration == 200
        assert second_syllable.kdur == 20.0
        assert second_syllable.text == "ka"
        assert second_syllable.highlights[0].duration == 200

        assert third_syllable.index == 2
        assert third_syllable.tag == "\\k30"
        assert third_syllable.start_time == 200
        assert third_syllable.end_time == 500
        assert third_syllable.duration == 500 - 200

    def test_parse_skips_legacy_empty_leading_syllable(self) -> None:
        parser = KaraokeParser()

        karaoke = parser.parse(make_event("{\\k20}ka{\\k30}ra"))

        first_syllable = karaoke.syllables[0]
        second_syllable = karaoke.syllables[1]

        assert len(karaoke.syllables) == 2
        assert first_syllable.index == 0
        assert first_syllable.tag == "\\k20"
        assert first_syllable.start_time == 0
        assert first_syllable.end_time == 200
        assert first_syllable.duration == 200
        assert first_syllable.kdur == 20.0
        assert first_syllable.text == "ka"
        assert first_syllable.highlights[0].duration == 200

        assert second_syllable.index == 1
        assert second_syllable.tag == "\\k30"
        assert second_syllable.start_time == 200
        assert second_syllable.end_time == 500
        assert second_syllable.duration == 500 - 200

    def test_parse_keeps_consecutive_leading_tags_as_blank_syllable(
        self,
    ) -> None:
        parser = KaraokeParser()

        karaoke = parser.parse(make_event("{\\k23}{\\k22}ka{\\k25}na"))

        first_syllable = karaoke.syllables[0]
        second_syllable = karaoke.syllables[1]
        third_syllable = karaoke.syllables[2]

        assert karaoke.text == "kana"
        assert len(karaoke.syllables) == 3
        assert first_syllable.index == 0
        assert first_syllable.tag == "\\k23"
        assert first_syllable.text == ""
        assert first_syllable.start_time == 0
        assert first_syllable.end_time == 230
        assert first_syllable.duration == 230
        assert second_syllable.index == 1
        assert second_syllable.tag == "\\k22"
        assert second_syllable.text == "ka"
        assert second_syllable.start_time == 230
        assert second_syllable.end_time == 450
        assert second_syllable.duration == 220
        assert third_syllable.index == 2
        assert third_syllable.tag == "\\k25"
        assert third_syllable.text == "na"
        assert third_syllable.start_time == 450
        assert third_syllable.end_time == 700

    def test_parse_supports_uppercase_k_and_kf_tags(self) -> None:
        parser = KaraokeParser()

        karaoke = parser.parse(make_event("{\\K5}A{\\kf7}B"))

        first_syllable = karaoke.syllables[0]
        second_syllable = karaoke.syllables[1]

        assert len(karaoke.syllables) == 2
        assert first_syllable.tag == "\\K5"
        assert first_syllable.duration == 50
        assert second_syllable.tag == "\\kf7"
        assert second_syllable.start_time == 50
        assert second_syllable.duration == 70

    def test_parse_supports_ko_tag(self) -> None:
        parser = KaraokeParser()

        karaoke = parser.parse(make_event("{\\ko5}A{\\k7}B"))

        first_syllable = karaoke.syllables[0]
        second_syllable = karaoke.syllables[1]

        assert len(karaoke.syllables) == 2
        assert first_syllable.tag == "\\ko5"
        assert first_syllable.duration == 50
        assert second_syllable.tag == "\\k7"
        assert second_syllable.start_time == 50
        assert second_syllable.duration == 70

    def test_parse_merges_hash_and_fullwidth_multi_highlights(self) -> None:
        parser = KaraokeParser()
        fullwidth_number_sign = "\uff03"

        karaoke = parser.parse(
            make_event(
                f"{{\\k10}}go{{\\k20}}#go{{\\k30}}"
                f"{fullwidth_number_sign}go{{\\k40}} end"
            )
        )

        merged_syllable = karaoke.syllables[0]
        final_syllable = karaoke.syllables[1]

        assert karaoke.text == "go end"
        assert len(karaoke.syllables) == 2
        assert merged_syllable.text == "go"
        assert merged_syllable.duration == 600
        assert merged_syllable.end_time == 600
        assert len(merged_syllable.highlights) == 3
        assert merged_syllable.highlights[0].duration == 100
        assert merged_syllable.highlights[1].duration == 200
        assert merged_syllable.highlights[2].duration == 300
        assert final_syllable.start_time == 600
        assert final_syllable.text == " end"

    def test_parse_returns_plain_segment_when_no_tags_exist(self) -> None:
        parser = KaraokeParser()

        karaoke = parser.parse(make_event("plain text"))

        first_syllable = karaoke.syllables[0]

        assert karaoke.text == "plain text"
        assert len(karaoke.syllables) == 1
        assert first_syllable.index == 0
        assert first_syllable.raw_text == "plain text"
        assert first_syllable.text == "plain text"
        assert first_syllable.trimmed_text == "plain text"
        assert first_syllable.tag == ""
        assert first_syllable.inline_fx == ""

    def test_parse_tracks_inline_fx_across_syllables(self) -> None:
        parser = KaraokeParser()

        karaoke = parser.parse(
            make_event("{\\k10}{\\-flash}ka{\\k10}ra{\\k10}{\\-shake}ok")
        )

        first_syllable = karaoke.syllables[0]
        second_syllable = karaoke.syllables[1]
        third_syllable = karaoke.syllables[2]

        assert first_syllable.inline_fx == "flash"
        assert second_syllable.inline_fx == "flash"
        assert third_syllable.inline_fx == "shake"
