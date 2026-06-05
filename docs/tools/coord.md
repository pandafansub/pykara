# coord

Use `coord` when a position calculation needs a screen-space offset from an
angle and distance, or a generated spread of points.

## Available Functions

### `coord.polar(angle, radius, axis=None)`

Return an offset from an angle and radius using ASS screen coordinates.
Positive Y points downward, so positive angles move upward. Pass `"x"` or
`"y"` as `axis` to return only one component.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\pos(!$syl_center + coord.polar(45, 30, "x")!,$syl_middle)}
```

### `coord.circular_spread(n, rotate=0)`

Return `n` unit-circle points as `(x, y)` tuples in a spatially spread order.
The first point starts at the top of the circle; `rotate` shifts the sequence
forward by that many steps around the circle.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code syl,points = coord.circular_spread(6)
```

### `coord.random_spread(n, spread=30, min_dist=14, min_radius=8, attempts=300)`

Return `n` random `(x, y)` points inside `-spread..spread`, keeping each point
at least `min_dist` away from the others and at least `min_radius` away from the
center.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code syl,points = coord.random_spread(6)
```
