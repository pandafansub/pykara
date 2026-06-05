# motion

Use `motion` to create motion effects with two backends: `motion.shad` simulates
motion with ASS shadow tags and keeps one output event, while `motion.fbf`
expands the rendered line into one event per frame.

Both backends are available only inside `template` declarations, not mixins.

> [!WARNING]
> `motion` is an experimental feature under active testing and improvement.
> Bugs, excessive memory use, and slowness may be encountered — use with caution.
>
> `motion.fbf` expands each rendered line into one event per frame. On long
> subtitle events or high framerates, this can produce a very large number of
> output lines.

## motion.shad

`motion.shad` produces inline ASS tags and requires no framerate metadata. On
the first call it injects shadow-color setup tags automatically, using `\4c` if
defined or the style's primary color otherwise. Each rendered line accepts at
most one `motion.*` call.

The positional effects `arc`, `bezier`, `spring`, and `wave` cannot be combined
with existing `\pos` or `\move` tags. `jitter` can use an existing `\pos`, but
cannot be combined with `\move`.

### Available Effects

- `motion.shad.jitter(left, right, up, down, period, seed=0)`
- `motion.shad.arc(x1, y1, x2, y2, a1=0, a2=360, r1=100, r2=100, t1=None, t2=None, segments=16)`
- `motion.shad.bezier(*points, t1=None, t2=None)`
- `motion.shad.spring(x0, y0, x1, y1, amplitude=1.0, damping=3.0, freq=6.0, t1=None, t2=None, segments=48)`
- `motion.shad.wave(x0, x1, y_base, amplitude=150, frequency=2.0, phase=0.0, t1=None, t2=None, segments=32)`

```ass
Comment: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,template line,{\an5!motion.shad.arc(640, 360, 640, 360, 0, 180, 80, 80)!}
Comment: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,karaoke,Goal
```

## motion.fbf

`motion.fbf` expands the rendered line into one event per frame and requires
`PlaybackFPS` or dummy-video FPS metadata. It cannot be combined with `\pos` or
`\move`. One `gradient.make(...)` may be added alongside; Pykara bakes the
motion first and applies the gradient per frame.

### Available Effects

- `motion.fbf.jitter(left, right, up, down, period, seed=0)`
- `motion.fbf.arc(x1, y1, x2, y2, a1=0, a2=360, r1=100, r2=100, t1=None, t2=None)`
- `motion.fbf.bezier(*points, t1=None, t2=None)`
- `motion.fbf.spring(x0, y0, x1, y1, amplitude=1.0, damping=3.0, freq=6.0, t1=None, t2=None)`
- `motion.fbf.wave(x0, x1, y_base, amplitude=150, frequency=2.0, phase=0.0, t1=None, t2=None)`

```ass
[Script Info]
PlayResX: 1280
PlayResY: 720
PlaybackFPS: 24

Comment: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,template line,{\an5!motion.fbf.wave(560, 720, 360, 30, 1.0)!}
Comment: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,karaoke,Goal
```
