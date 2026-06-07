# Modifiers

Modifiers refine how a directive runs. They follow the scope token in the
`Effect` field.

```ass
template syl loop 3 no_blank
```

## Reference

| Modifier | Directives | Argument | Scopes | Purpose |
| ---------- | --------------------- | -------------- | -------------------------------------- | --------------------------------------------------------------------------- |
| `all` | `template`, `code` | no | `setup`, `line`, `word`, `syl`, `char` | Match karaoke lines of any style. |
| `loop` | `template` | yes | `line`, `word`, `syl`, `char` | Repeat the template N times. |
| `no_blank` | `template` | no | `line`, `word`, `syl`, `char` | Skip empty lines, words, syllables, or characters. |
| `no_merge` | `template` | no | `line`, `word`, `syl`, `char` | Keep adjacent ASS override blocks separate. |
| `no_text` | `template` | no | `line`, `word`, `syl`, `char` | Do not append source text; use when the template provides its own text. |
| `prepend` | `mixin` | no | `line`, `word`, `syl`, `char` | Insert before the template body. |
| `layer` | `mixin` | integer | `line`, `word`, `syl`, `char` | Match templates that set this output layer. |
| `for` | `mixin` | actor name | `line`, `word`, `syl`, `char` | Match templates with this actor. |
| `fx` | `template`, `mixin` | yes | `syl` | Match only syllables with the given inline-fx tag. |
| `styles` | `template`, `code` | tuple variable | `setup`, `line`, `word`, `syl`, `char` | Apply only to karaoke events using one of the listed styles. |
| `when` | `template`, `mixin` | yes | `line`, `word`, `syl`, `char` | Run only if the expression is truthy. |
| `unless` | `template`, `mixin` | yes | `line`, `word`, `syl`, `char` | Run only if the expression is falsy. |

## `all`

By default, a directive applies only to karaoke lines whose style matches
the directive's own style. Add `all` right after the scope to match every
style instead.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code syl all,shared = 1
```

`all` is not supported on `mixin` directives.

## `loop`

```ass
template syl loop 3
template syl loop glow 2
```

- `loop N` — repeats the template N times and exposes `$loop_i`/`$loop_n`.
  Inside `!expr!`, use `loop.i` and `loop.n`.
- `loop NAME N` — same, but exposes `$loop_NAME_i`/`$loop_NAME_n`.
  Inside `!expr!`, use `loop.NAME.i` and `loop.NAME.n`.
- `loop (EXPR)` / `loop NAME (EXPR)` — evaluates `EXPR` at runtime and
  uses the resulting positive integer.
- Multiple named loops run as a cartesian product (every combination of their iterations).
- Unnamed and named loops cannot be mixed.
- Named loops cannot use `i` or `n`; those names are reserved by the `loop`
  expression object.

## `no_merge`

By default, adjacent ASS override blocks in the final generated text are
merged. For example, `{\an5}{\blur2}` becomes `{\an5\blur2}`.

Use `no_merge` to preserve separate blocks:

```ass
template syl no_merge
```

## `fx`

```ass
template syl fx glow
```

Match only syllables tagged with the given inline-fx name.

## `styles`

```ass
template syl styles my_styles
```

```python
my_styles = ("Romaji", "Kanji", "Translation")
```

Apply a `template` or `code` declaration only to karaoke events whose
style is listed in the tuple. Pykara uses the matched karaoke style as
the reference style for measurements, exposes it through `style`, and
uses it as the output event style.

The argument must be a variable that resolves to a tuple of style names.
Every listed style must exist. A single literal style name is not
accepted.

## `prepend`

```ass
mixin syl prepend
```

Insert the mixin body before the template body instead of before the
source text (the syllable, word, or character text from the karaoke line).

## `layer`

```ass
mixin syl layer 2
```

Apply the mixin only when the generated line has the given layer. This is
checked after the template body has run, so `!layer.set(2)!` inside the
template can select the mixin.

## `for`

```ass
mixin syl for lead
```

Apply the mixin only to templates whose actor field is `lead`.

## `when` / `unless`

```ass
template syl when glow
template syl unless muted
template syl when (syl.i == 0)
template syl unless (syl.i == syl.n - 1)
```

- `when FLAG` / `unless FLAG` — evaluate a single variable name.
- `when (EXPR)` / `unless (EXPR)` — evaluate a Python expression (parentheses
  required when the expression contains spaces).
- Expressions use the same names available inside `!expr!`, such as
  `line.i`, `word.i`, `syl.i`, `char.i`, `style`, and `metadata`.
