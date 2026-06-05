# Word Scope

The `word` scope runs once per word inside every karaoke line. Both
`template` and `code` directives can target it.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template word,{\pos($word_center,$word_middle)}
```

## Variables

The `line_*` and `word_*` variables are available.
See [Variables](./variables.md) and [Objects](./objects.md).

## Behavior

- Without `loop`, one generated line is emitted per word. With `loop N`, N
  generated lines are emitted per word.
- The source word text is appended by default; use `no_text` to skip it.
- Use `no_blank` to skip words with empty text.

Assign a per-word value for syllable templates inside the same word:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code word,word_is_even = word.i % 2 == 0
```
