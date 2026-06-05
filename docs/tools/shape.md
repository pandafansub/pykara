# shape

Use `shape` to transform or generate ASS drawing shapes for `\p` drawings
and clipping masks.

## Available Functions

### `shape.rotate(shape, angle, origin_x=0, origin_y=0)`

Rotate every point in a drawing shape around an origin.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\p1}!shape.rotate(assets.shapes.star, $syl_i * 30)!{\p0}
```

### `shape.center_at(shape, x=0, y=0)`

Move a shape so its bounding-box center sits at `x,y`.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\p1}!shape.center_at(assets.shapes.circle, $syl_center, $syl_middle)!{\p0}
```

### `shape.displace(shape, offset_x, offset_y)`

Move every point in a drawing shape by `offset_x,offset_y`.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\p1}!shape.displace(assets.shapes.star, $syl_center, $syl_middle)!{\p0}
```

### `shape.split_clip(width, angle=0, x=0, y=0, height=None)`

Build a rotated split clipping shape centered at `x,y`.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\clip(!shape.split_clip($syl_width, 0, $syl_center, $syl_middle)!)}
```
