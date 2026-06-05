# Line Scope

The `line` scope runs once per karaoke line. Both `template` and `code`
directives can target it.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template line,{\an5\pos($line_center,$line_middle)\fad(200,200)}
```

## Variables

`layer`, `actor`, `loop_i`/`loop_n` (when looping), and all `line_*` variables
are available. See [Variables](./variables.md) and [Objects](./objects.md).

## Behavior

- Without `loop`, one generated line is produced per karaoke line.
- With `loop N`, N generated lines are produced per karaoke line.
- The source text is appended by default; use `no_text` to skip it.

Fade the whole line in and out:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template line,{\fad(200,200)}
```

Assign a per-line value for later use:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code line,hue = line.i % 3
```
