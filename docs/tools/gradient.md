# gradient

Use `gradient` to build clip-based gradients over the bounding box of the
current rendered line, syllable or a drawing shape.

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

Build a gradient over the rendered object. With `\p1`, the object is the
drawing shape. Without `\p1`, it is the text box for the active template scope.
`colors` is a sequence of 2 or more ASS colors such as
`["&H0000FF&", "&HFF00FF&"]`. `step` is the slice thickness in pixels.
`direction` is one of `"top-bottom"`, `"bottom-top"`, `"left-right"`, or
`"right-left"`.

Multiple `gradient.make(...)` calls can be used in one template or mixin, for
example to apply separate gradients to `\1c`, `\2c`, and `\3c`. When calls use
different `step` values, the smallest `step` has priority and determines the
shared slice segmentation.

```ass
[Script Info]
PlayResX: 1280
PlayResY: 720
PlaybackFPS: 24

Comment: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,template line,{\an5\1c!gradient.make(["&H0000FF&", "&H00FFFF&", "&HFFFFFF&"], step=4)!}
Comment: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,karaoke,Goal
```

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template line no_text,{\an5\bord0\shad0\1c!gradient.make(["&H0000FF&", "&H00FFFF&", "&HFFFFFF&"], step=4)!\p1}m -100 -50 l 100 -50 100 50 -100 50{\p0}
Comment: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,karaoke,Goal
```

## Restrictions

- Requires FPS information. In the CLI, pass either `--fps FPS` or
  `--timecodes timecodes.txt`; otherwise Pykara falls back to `PlaybackFPS`,
  then Aegisub dummy-video FPS metadata.
- Available inside `template` and `mixin` declarations. In a mixin, the gradient
  expands only the generated line where that mixin is applied.
- Cannot be combined with `\move`.
- Cannot be combined with `\clip` or `\iclip`.
- Does not support rotation or shear tags: `\frz`, `\frx`, `\fry`, `\fax`,
  `\fay`.
