# builtins

Pykara exposes a subset of Python built-in functions inside `!expr!` and
`code` directives.

These names are available directly, without a namespace:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,!sum(range(4))!
```

## Available Functions

| Function | Description |
| ------------------------------ | ------------------------------------------------- |
| `abs(value)` | Absolute value. |
| `all(iterable)` | `True` when every item is truthy. |
| `any(iterable)` | `True` when at least one item is truthy. |
| `bool(value)` | Convert to `True` or `False`. |
| `dict(...)` | Build a dictionary. |
| `enumerate(iterable)` | Iterate as `(index, value)` pairs. |
| `float(value)` | Convert to a float. |
| `int(value)` | Convert to an integer. |
| `len(value)` | Length of a sequence or collection. |
| `list(iterable)` | Build a list. |
| `max(...)` | Largest value. |
| `min(...)` | Smallest value. |
| `range(...)` | Integer range for loops and comprehensions. |
| `reversed(sequence)` | Iterate in reverse order. |
| `round(value, ndigits=None)` | Round a numeric value. |
| `set(iterable=())` | Build a set. |
| `sorted(iterable)` | Return a sorted list. |
| `str(value)` | Convert to text. |
| `sum(iterable)` | Add numeric values. |
| `tuple(iterable)` | Build a tuple. |
| `zip(...)` | Iterate over multiple iterables in parallel. |

## Notes

Unsafe or environment-facing built-ins such as `open`, `eval`, `exec`,
`compile`, `globals`, `locals`, `vars`, `dir`, `getattr`, `setattr`,
`delattr`, `type`, `object`, `super`, `input`, `print`, and `help` are
not exposed. `import` is also not available — use the documented
namespaces: [`math`](./math.md), [`random`](./random.md),
[`color`](./color.md), [`coord`](./coord.md), and [`shape`](./shape.md).

For the shared store helpers `get`, `put`, and `lock`, see
[`global`](./global.md).
