# Variables

Template variables are accessed with `$name`. Values from `code` directives
are available as `$name` and inside `!expr!` in later templates.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code setup,main = color.rgb_to_ass(255, 200, 0)
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\1c$main}
```

## Available Variables

### Generated Line Variables

| Variable | Description |
|----------|-------------|
| `layer` | Layer of the generated line. |
| `actor` | Actor field of the generated line. |
| `loop_i` | Current loop iteration index (only when exactly one `loop` is active). |
| `loop_n` | Total loop iterations (only when exactly one `loop` is active). |

### `line_*`

| Variable | Description |
|----------|-------------|
| `line_start` | Line start time in ms. |
| `line_end` | Line end time in ms. |
| `line_dur` | Line duration in ms. |
| `line_mid` | Line midpoint in ms. |
| `line_i` | Karaoke line index. |
| `line_left` | Left edge. |
| `line_center` | Horizontal center. |
| `line_right` | Right edge. |
| `line_width` | Width. |
| `line_top` | Top edge. |
| `line_middle` | Vertical center. |
| `line_bottom` | Bottom edge. |
| `line_height` | Height. |
| `line_x` | ASS anchor x position. |
| `line_y` | ASS anchor y position. |

### `word_*`

| Variable | Description |
|----------|-------------|
| `word_start` | Word start time in ms. |
| `word_end` | Word end time in ms. |
| `word_dur` | Word duration in ms. |
| `word_kdur` | Word duration in centiseconds. |
| `word_mid` | Word midpoint in ms. |
| `word_n` | Total word count in the line. |
| `word_i` | Word index. |
| `word_left` | Left edge. |
| `word_center` | Horizontal center. |
| `word_right` | Right edge. |
| `word_width` | Width. |
| `word_top` | Top edge. |
| `word_middle` | Vertical center. |
| `word_bottom` | Bottom edge. |
| `word_height` | Height. |
| `word_x` | ASS anchor x position. |
| `word_y` | ASS anchor y position. |

### `syl_*`

| Variable | Description |
|----------|-------------|
| `syl_start` | Syllable start time in ms. |
| `syl_end` | Syllable end time in ms. |
| `syl_dur` | Syllable duration in ms. |
| `syl_kdur` | Syllable duration in centiseconds. |
| `syl_mid` | Syllable midpoint in ms. |
| `syl_n` | Total syllable count in the line. |
| `syl_i` | Syllable index. |
| `syl_left` | Left edge. |
| `syl_center` | Horizontal center. |
| `syl_right` | Right edge. |
| `syl_width` | Width. |
| `syl_top` | Top edge. |
| `syl_middle` | Vertical center. |
| `syl_bottom` | Bottom edge. |
| `syl_height` | Height. |
| `syl_x` | ASS anchor x position. |
| `syl_y` | ASS anchor y position. |

### `char_*`

| Variable | Description |
|----------|-------------|
| `char_i` | Character index in the line. |
| `char_n` | Total character count in the current syllable. |
| `char_left` | Left edge. |
| `char_center` | Horizontal center. |
| `char_right` | Right edge. |
| `char_width` | Width. |
| `char_top` | Top edge. |
| `char_middle` | Vertical center. |
| `char_bottom` | Bottom edge. |
| `char_height` | Height. |
| `char_x` | ASS anchor x position. |
| `char_y` | ASS anchor y position. |
