# retime

Use `retime` to choose which part of the source line should define the
generated line's timing.

## Usage

```python
retime.<target>()
retime.<target>(start_offset, end_offset)
retime.<target>.<preset>(start_offset, end_offset)
```

Call `retime` once per template body to change the generated line's
timing. Offsets are in milliseconds: negative values move that edge
earlier, positive values move it later, and omitted offsets default to
`0`.

## Timeline

```text
line.start        syl.start       syl.end         line.end
|                 |               |               |
+-----------------+---------------+---------------+
^ preline         ^ presyl        ^ postsyl       ^ postline

|<----------------------------------------------->| line
|<-- start2syl -->|<---- syl ---->|<-- syl2end -->|
```

The diagram shows the base timing before `start_offset` and `end_offset`
are applied.

## Available Functions

### Targets

| Target | Result range |
| ----------- | ---------------------------------------------- |
| `line` | Full source line. |
| `preline` | Zero-duration window at line start. |
| `postline` | Zero-duration window at line end. |
| `syl` | Syllable start to syllable end. |
| `presyl` | Zero-duration window at syllable start. |
| `postsyl` | Zero-duration window at syllable end. |
| `start2syl` | Line start to syllable start. |
| `syl2end` | Syllable end to line end. |

`line`, `preline`, and `postline` are valid in `template line`,
`template word`, `template syl`, and `template char`.

`syl`, `presyl`, and `postsyl` are valid in `template syl` and
`template char`. In `template char`, the active syllable is the
character's parent syllable.

`start2syl` and `syl2end` are valid in `template syl` and
`template char`. In `template char`, they still use the character's
parent syllable as the syllable boundary.

Play a fade-in right before each syllable:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,!retime.presyl(0, 200)!{\pos($syl_center,$syl_middle)\fad(200,0)}
```

Fade each syllable out after it finishes:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,!retime.syl2end()!{\pos($syl_center,$syl_middle)\t(\alpha&HFF&)}
```

### Presets

Presets spread the offsets across repeated items. In `template char`,
for example, `ltr` makes earlier characters start further before the line
and later characters closer to the line start.

Presets need at least two items to spread across, so they are not valid
in `template line`. `syl`, `presyl`, and `postsyl` presets are only valid
in `template char`, where they spread the offset across characters.
`start2syl` and `syl2end` presets work in both `template syl` and
`template char`, spreading across syllables or characters respectively.

| Preset | Order |
| -------------- | --------------------------- |
| `ltr` | textual left to right |
| `rtl` | textual right to left |
| `from_center` | center first |
| `from_edges` | edges first |
| `odd_first` | odd indexes first |
| `even_first` | even indexes first |
| `spatial_ltr` | visual left to right |
| `spatial_rtl` | visual right to left |
| `random` | deterministic pseudo-random |

Stagger line lead-in across characters:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template char,!retime.line.ltr(-300, 0)!{\pos($char_center,$char_middle)\fad(300,0)}
```
