# Include

`include` loads Python code from one or more `.py` files into a `code setup`
directive. Use it for shared configuration used by several templates.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code setup,include "common.py"
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\1c$main_color}
```

With `common.py` next to the `.ass` file:

```python
main_color = color.rgb_to_ass(255, 200, 0)
```

## Multiple Files

Separate paths with commas.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code setup,include "palette.py", "styles.py"
```

Files run from left to right. Values assigned by included files become
available to later `code`, `template`, and `mixin` directives.

## Paths

Relative paths are resolved from the directory of the input `.ass` file.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code setup,include "shared/common.py"
```

Absolute paths are also supported. Prefer `/` separators for portable paths;
Python accepts them on Windows, Linux, and macOS.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code setup,include "C:/Karaoke/Project/common.py"
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code setup,include "/karaoke/project/common.py"
```

Windows paths with backslashes must be written as raw strings or escaped
strings.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code setup,include r"C:\Karaoke\Project\common.py"
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code setup,include "C:\\Karaoke\\Project\\common.py"
```

## Rules

- Included paths must be string literals.
- Included files must use the `.py` extension.
- Included code uses the same safe execution namespace as `code` directives.
- Included code cannot assign to Pykara names such as `line`, `syl`, `style`,
  `color`, `shape`, `random`, `assets`, or built-ins such as `range`.
- Pykara raises an error when an included file and `.ass` code declare the
  same name.
- Pykara raises an error when two included files declare the same name.

## Valid Example

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code setup,include "config.py"
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,template syl,{\bord$outline_size\1c$main_color}
```

```python
main_color = color.rgb_to_ass(255, 200, 0)
outline_size = 3
```

## Invalid Example

This fails because both files declare `main_color`.

```ass
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code setup,include "config.py"
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,code setup,main_color = color.rgb_to_ass(0, 0, 0)
```

```python
main_color = color.rgb_to_ass(255, 200, 0)
```
