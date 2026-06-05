# gradient

Use `gradient` to build clip-based gradients over the bounding box of the
current rendered line or syllable.

> [!WARNING]
> `gradient` is an experimental feature under active testing and improvement.
> Bugs, excessive memory use, and slowness may be encountered — use with caution.
>
> Combining `gradient.make(...)` with `motion.fbf.*` effects can produce a very
> large number of output lines, proportional to the number of frames covered by
> the subtitle event. Be mindful of output size when using this combination.
> If you only need motion, `motion.shad.*` keeps a single output event per
> rendered line.

## Available Functions

### `gradient.make(colors, step=2, direction="top-bottom")`

Build a gradient over the bounding box of the rendered line or syllable.
`colors` is a sequence of 2 or more ASS colors such as
`["&H0000FF&", "&HFF00FF&"]`. `step` is the slice thickness in pixels.
`direction` is one of `"top-bottom"`, `"bottom-top"`, `"left-right"`, or
`"right-left"`.

Multiple `gradient.make(...)` calls can be used in one template, for example to
apply separate gradients to `\1c`, `\2c`, and `\3c`. When calls use different
`step` values, the smallest `step` has priority and determines the shared slice
segmentation.

```ass
[Script Info]
PlayResX: 1280
PlayResY: 720
PlaybackFPS: 24

Comment: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,template line,{\an5\1c!gradient.make(["&H0000FF&", "&H00FFFF&", "&HFFFFFF&"], step=4)!}
Comment: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,karaoke,Goal
```

## Restrictions

- Requires `PlaybackFPS` or dummy-video FPS metadata.
- Available only inside `template` declarations, not mixins.
- Can be combined with one `motion.fbf.*` effect on the same rendered line. In
  that case, Pykara expands the motion frame-by-frame first and slices the gradient after.
- Cannot be combined with `\move`.
- Can be combined with `\pos`.
- Cannot be combined with `\clip` or `\iclip`.
- Does not support rotation or shear tags: `\frz`, `\frx`, `\fry`, `\fax`,
  `\fay`.

In line scope, Pykara resolves implicit ASS positioning into an explicit
`\pos(...)` before slicing. Animated geometry tags such as `\fs`, `\fscx`,
`\fscy`, `\fsp`, `\bord`, `\shad`, `\blur`, and `\be` are expanded
frame-by-frame before the gradient is applied.
