# Setup Scope

The `setup` scope runs once, before any karaoke line is processed. Only
`code` directives may target it.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code setup,main = color.rgb_to_ass(255, 128, 0)
```

## Purpose

- Pre-compute values every line will use.
- Define reusable or shared data.

## Available Tools

All tools are available: `color`, `coord`, `shape`, `math`, `random`,
`assets`, and the built-ins documented in [builtins](../tools/builtins.md).

Line, word, syllable, and character variables are **not** available here.
`retime` and `layer` are also not available, as they operate on generated
lines during template rendering.
