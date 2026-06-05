# random

Use `random` to add pseudo-random variation to generated lines, such as
jitter, color choices, or rotation.

## Available Functions

### `random.random()`

Return a uniform float in `[0.0, 1.0)`.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\1c!color.interpolate(random.random(), style.primary_color, style.secondary_color)!}
```

### `random.choice(seq)`

Return one pseudo-random element from a non-empty sequence.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code syl,offset = random.choice((-20, 0, 20))
```

### `random.choice_no_repeat(seq)`

Return one pseudo-random element from a non-empty sequence, avoiding the value
returned on the immediately preceding call from the same template expression or
code block.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code syl,offset = random.choice_no_repeat((-20, 0, 20))
```

### `random.randint(a, b)`

Return a uniform integer `N` such that `a <= N <= b`.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\frz!random.randint(-5, 5)!}
```

## Determinism

Use `--seed` when you want the same input to produce the same random
values every time. Without a seed, each run may produce different values.

```sh
pykara input.ass output.ass --seed 42
```

`--seed` controls the seed from the CLI. To set it from within the file,
assign `__seed__ = N` in any `code` directive; it applies to all `random`
calls that follow.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code setup,__seed__ = 7
```
