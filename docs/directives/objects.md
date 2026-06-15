# Objects

Inside `!expr!`, runtime data is exposed through objects.

## Available Objects

### `line`

| Property | Description |
|----------|-------------|
| `layer` | Output layer. |
| `actor` | Output actor. |
| `raw_text` | Original line text, including tags. |
| `text` | Visible line text. |
| `trimmed_text` | Visible line text without outer whitespace. |
| `start` | Start time in ms. |
| `end` | End time in ms. |
| `dur` | Duration in ms. |
| `mid` | Midpoint in ms. |
| `i` | Karaoke line index. |
| `left` | Left edge. |
| `center` | Horizontal center. |
| `right` | Right edge. |
| `width` | Width. |
| `top` | Top edge. |
| `middle` | Vertical center. |
| `bottom` | Bottom edge. |
| `height` | Height. |
| `x` | ASS anchor x position. |
| `y` | ASS anchor y position. |
| `syls` | Read-only sequence of syllables. |

### `word`

| Property | Description |
|----------|-------------|
| `text` | Visible word text. |
| `trimmed_text` | Word text without outer whitespace. |
| `start` | Start time in ms. |
| `end` | End time in ms. |
| `dur` | Duration in ms. |
| `kdur` | Duration in centiseconds. |
| `mid` | Midpoint in ms. |
| `n` | Total word count in the line. |
| `i` | Word index. |
| `left` | Left edge. |
| `center` | Horizontal center. |
| `right` | Right edge. |
| `width` | Width. |
| `top` | Top edge. |
| `middle` | Vertical center. |
| `bottom` | Bottom edge. |
| `height` | Height. |
| `x` | ASS anchor x position. |
| `y` | ASS anchor y position. |

### `syl`

| Property | Description |
|----------|-------------|
| `text` | Visible syllable text. |
| `trimmed_text` | Syllable text without outer whitespace. |
| `start` | Start time in ms. |
| `end` | End time in ms. |
| `dur` | Duration in ms. |
| `kdur` | Duration in centiseconds. |
| `mid` | Midpoint in ms. |
| `n` | Total syllable count in the line. |
| `i` | Syllable index. |
| `left` | Left edge. |
| `center` | Horizontal center. |
| `right` | Right edge. |
| `width` | Width. |
| `top` | Top edge. |
| `middle` | Vertical center. |
| `bottom` | Bottom edge. |
| `height` | Height. |
| `x` | ASS anchor x position. |
| `y` | ASS anchor y position. |
| `tag` | Source karaoke tag such as `\k20`. |
| `inline_fx` | Parsed inline-fx marker. |

### `char`

| Property | Description |
|----------|-------------|
| `text` | Visible character text. |
| `trimmed_text` | Character text without outer whitespace. |
| `i` | Character index in the line. |
| `n` | Total character count in the line. |
| `left` | Left edge. |
| `center` | Horizontal center. |
| `right` | Right edge. |
| `width` | Width. |
| `top` | Top edge. |
| `middle` | Vertical center. |
| `bottom` | Bottom edge. |
| `height` | Height. |
| `x` | ASS anchor x position. |
| `y` | ASS anchor y position. |

### `loop`

Available only while rendering a template with a `loop` modifier.

| Property | Description |
|----------|-------------|
| `i` | Current loop iteration index, only when exactly one loop is active. |
| `n` | Total loop iterations, only when exactly one loop is active. |
| `NAME.i` | Current iteration index for the named loop `NAME`. |
| `NAME.n` | Total iterations for the named loop `NAME`. |

### `style`

| Property | Description |
|----------|-------------|
| `name` | Style name. |
| `font_name` | Font face name. |
| `font_size` | Font size. |
| `primary_color` | Primary color as normalized ASS override color, such as `&HFFFFFF&`. |
| `secondary_color` | Secondary color as normalized ASS override color. |
| `outline_color` | Outline color as normalized ASS override color. |
| `shadow_color` | Shadow color as normalized ASS override color. |
| `bold` | Whether the style is bold. |
| `italic` | Whether the style is italic. |
| `underline` | Whether the style is underlined. |
| `strike_out` | Whether the style uses strikeout. |
| `scale_x` | Horizontal scale percentage. |
| `scale_y` | Vertical scale percentage. |
| `spacing` | Letter spacing. |
| `angle` | Rotation angle. |
| `border_style` | ASS border style. |
| `outline` | Outline width. |
| `shadow` | Shadow depth. |
| `alignment` | ASS alignment number. |
| `margin_l` | Left margin. |
| `margin_r` | Right margin. |
| `margin_t` | Top margin. |
| `margin_b` | Bottom margin. |
| `encoding` | ASS character encoding. |

### `metadata`

| Property | Description |
|----------|-------------|
| `res_x` | Script resolution width. |
| `res_y` | Script resolution height. |

### `assets`

See [`assets`](../tools/assets.md) for the available namespaces.
