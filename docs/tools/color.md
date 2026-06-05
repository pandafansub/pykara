# color

Use `color` to build ASS override color strings from RGB values, alpha
values, blends between two colors, or RGB components from HSV/HSL.

## Available Functions

### `color.rgb_to_ass(red, green, blue)`

Return an ASS override color string in `&HBBGGRR&` format. Components are
clamped to `[0, 255]`.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\1c!color.rgb_to_ass(255, 128, 0)!}
```

### `color.alpha(alpha)`

Return an ASS alpha string. `alpha` is clamped to `[0, 255]`.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\alpha!color.alpha(128)!}
```

### `color.interpolate(progress, start_color, end_color)`

Interpolate between two ASS colors at `progress` in `[0, 1]`, returning
an ASS override color string in `&HBBGGRR&` format. Inputs may be ASS
style colors, override colors, alphas, or HTML hex strings like `#FF8000`.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\1c!color.interpolate($syl_i / $syl_n, style.primary_color, style.secondary_color)!}
```

### `color.hsv_to_rgb(hue, saturation, value)`

Convert HSV components to RGB integer components in `[0, 255]`. `hue` is wrapped into `[0, 360)`.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\1c!color.rgb_to_ass(*color.hsv_to_rgb(60, 1, 1))!}
```

### `color.hsl_to_rgb(hue, saturation, luminance)`

Convert HSL components to RGB integer components in `[0, 255]`. `hue` is
wrapped into `[0, 360)`, and `saturation` and `luminance` are clamped to `[0, 1]`.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\1c!color.rgb_to_ass(*color.hsl_to_rgb(120, 1, 0.5))!}
```
