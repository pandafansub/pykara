# math

Use `math` for numeric calculations inside `!expr!` and `code`
directives.

## Available Functions

### `math.floor(x)`

Round down to the nearest integer.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\fscx!100 + math.floor($syl_dur / 100) * 5!}
```

### `math.ceil(x)`

Round up to the nearest integer.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\fscx!100 + math.ceil($syl_dur / 100) * 5!}
```

### `math.fabs(x)`

Return the absolute value as a float.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\blur!math.fabs($syl_center - $line_center) / 40!}
```

### `math.sqrt(x)`

Return the square root.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\fscx!100 + math.sqrt($syl_dur)!}
```

### `math.sin(x)`

Return the sine of `x`. `x` must be in radians.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\frz!math.sin(math.radians($syl_i * 30)) * 10!}
```

### `math.cos(x)`

Return the cosine of `x`. `x` must be in radians.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\pos(!$syl_center + math.cos(math.radians($syl_i * 45)) * 15!,$syl_middle)}
```

### `math.radians(x)`

Convert degrees to radians.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\frz!math.cos(math.radians($syl_i * 60)) * 10!}
```

### `math.remap(src, dst, values)`

Scale one value or a list/tuple by the ratio between `src` and `dst`.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\fscx!math.remap(48, 22, 100)!}
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\blur!math.remap((1920, 1080), (960, 720), 3)!}
```
