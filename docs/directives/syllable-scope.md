# Syllable Scope

The `syl` scope is the most common scope in Pykara. It runs once per
karaoke syllable.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\pos($syl_center,$syl_middle)}
```

## Variables

The `line_*`, `word_*`, and `syl_*` variables are available. See
[Variables](./variables.md) and [Objects](./objects.md).

## Behavior

- Without `loop`, one generated line is emitted per syllable. With `loop N`,
  N generated lines are emitted per syllable.
- The source syllable text is appended by default; use `no_text` to skip it.
- Use `no_blank` to skip syllables with empty text.
- Use `fx NAME` to match only syllables tagged with a specific inline-fx name.

Pulse each syllable during its own duration:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,!retime.syl()!{\pos($syl_center,$syl_middle)\t(\fscx120\fscy120)}
```

Prepare one value per syllable with `code syl`:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code syl,current_color = color.rgb_to_ass(255, 120 + syl.i * 20, 80)
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\pos($syl_center,$syl_middle)\1c!current_color!}
```

Only run on syllables tagged `glow`:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl fx glow,{\pos($syl_center,$syl_middle)\blur3}
```
