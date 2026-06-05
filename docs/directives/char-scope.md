# Char Scope

The `char` scope runs once per character inside every syllable. Both
`template` and `mixin` directives may target it.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template char,{\pos($char_center,$char_middle)}
```

## Variables

The `line_*`, `word_*`, `syl_*`, and `char_*` variables are available.
Characters inherit the parent syllable's timing. See
[Variables](./variables.md) and [Objects](./objects.md).

## Behavior

- Without `loop`, one generated line is emitted per character. With `loop N`,
  N generated lines are emitted per character.
- Accurate per-character widths require the font measurement libraries
  (`freetype-py`, `uharfbuzz`, `fonttools`), which are installed automatically
  on Linux and macOS but not on Windows.
- The source character text is appended by default; use `no_text` to skip it.
- Use `no_blank` to skip whitespace characters.

Rotate each character slightly based on its index:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template char,{\pos($char_center,$char_middle)\frz!$char_i * 10!}
```
