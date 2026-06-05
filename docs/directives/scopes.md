# Scopes

A **scope** controls how often a directive runs and which variables are
available when it runs. The scope keyword follows the directive type in
the `Effect` field.

## Available Scopes

| Scope | Directives | Runs | Data Available |
| ------- | ---------------------------- | ---------------------- | ------------------------------------------------------------------ |
| `setup` | `code` | Once per document. | No per-line runtime data. |
| `line` | `code`, `template`, `mixin` | Once per karaoke line. | `layer`, `actor`, `loop_i`/`loop_n` (when looping), `line_*`. |
| `word` | `code`, `template`, `mixin` | Once per word. | Everything from `line`, plus `word_*`. |
| `syl` | `code`, `template`, `mixin` | Once per syllable. | Everything from `word`, plus `syl_*`. |
| `char` | `template`, `mixin` | Once per character. | Everything from `syl`, plus `char_*`. |

For the complete variable list, see [Variables](./variables.md). For
object properties available inside `!expr!`, see [Objects](./objects.md).
