# global

Global functions are called directly, without a namespace. They are
available in `template` directives. Some are also available in `code`
directives.

## Available Functions

### `put(key, value)`

Store `value` under `key` and return `value`. Replaces any previous
value unless the key is locked.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\1c!put("main", color.rgb_to_ass(255, 200, 0))!}
```

### `lock(key, value)`

Like `put`, but locks the key after the first call. Subsequent `lock` or
`put` calls with the same key are ignored. Returns the locked value.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template line,{\1c!lock("main", color.rgb_to_ass(255, 200, 0))!}
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,mixin line,{\3c!get("main")!}
```

### `get(key, default_value=None)`

Return the value stored under `key`. If the key does not exist, return
`default_value`.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\1c!get("main", style.primary_color)!}
```

### `get_style(style_name)`

Return an object with information for the named style. If the style does
not exist, Pykara raises an error. This function is available in both
`template` and `code` directives.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code setup,my_style = get_style("My Style")
```

The returned object exposes the normalized ASS style fields such as
`name`, `fontname`, `fontsize`, `primary_colour`, `outline`, `shadow`,
`alignment`, margins, and encoding. It also exposes the familiar color
aliases `primary_color`, `secondary_color`, `outline_color`, and
`shadow_color`.

## Scope Behavior

A value set in any `line`, `word`, `syl`, or `char` template, or any mixin,
can be read by any later template or mixin. The store persists across
syllables, words, and lines; the last `put` wins unless the key is locked.

## Notes

`put` and `lock` cannot store functions or methods.

Inside `!expr!`, `put` outputs the value it stores, and `get` outputs
nothing when the key is missing:

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\fscx!put("size", 120)!\fscy!get("size")!}
```

Values assigned in `code` blocks are normal Python variables and are
available as `$name` or `!name!` in later templates. They do not use
this store.
