script_name = "Pykara Templater"
script_description = "Apply Pykara templates with the installed Python CLI"
script_author = "Pykara"
script_version = "0.2"

local DIALOG_WIDTH = 60
local TEXTBOX_HEIGHT = 10
local LABEL_HEIGHT = 2
local FX_EFFECT = "fx"
local SOURCE_EFFECTS = {
    karaoke = true,
}

local function is_windows()
    return package.config:sub(1, 1) == "\\"
end

local function shell_quote(value)
    if is_windows() then
        return '"' .. tostring(value):gsub('"', '""') .. '"'
    end
    return "'" .. tostring(value):gsub("'", "'\\''") .. "'"
end

local function powershell_quote(value)
    return "'" .. tostring(value):gsub("'", "''") .. "'"
end

local function windows_argument_quote(value)
    local text = tostring(value)
    if text == "" then
        return '""'
    end
    if not text:match('[%s"]') then
        return text
    end

    local quoted = {'"'}
    local backslashes = 0

    for index = 1, #text do
        local char = text:sub(index, index)
        if char == "\\" then
            backslashes = backslashes + 1
        elseif char == '"' then
            table.insert(quoted, string.rep("\\", (backslashes * 2) + 1))
            table.insert(quoted, char)
            backslashes = 0
        else
            if backslashes > 0 then
                table.insert(quoted, string.rep("\\", backslashes))
                backslashes = 0
            end
            table.insert(quoted, char)
        end
    end

    if backslashes > 0 then
        table.insert(quoted, string.rep("\\", backslashes * 2))
    end
    table.insert(quoted, '"')
    return table.concat(quoted)
end

local function windows_argument_list(...)
    local args = {}
    for _, value in ipairs({...}) do
        table.insert(args, windows_argument_quote(value))
    end
    return table.concat(args, " ")
end

local function is_absolute_path(path)
    local value = tostring(path or "")
    if value:match("^/") then
        return true
    end
    if value:match("^%a:[/\\]") then
        return true
    end
    return value:match("^\\\\") ~= nil
end

local function join_path(...)
    local separator = is_windows() and "\\" or "/"
    return table.concat({...}, separator)
end

local function pykara_program()
    return "pykara"
end

local function current_subtitle_path()
    local dir = aegisub.decode_path("?script")
    local name = aegisub.file_name()

    if not dir or dir == "" or not name or name == "" then
        return nil
    end

    if is_absolute_path(name) then
        return name
    end

    return join_path(dir, name)
end

local function show_label_dialog(label)
    aegisub.dialog.display({
        {
            class = "label",
            x = 0,
            y = 0,
            width = DIALOG_WIDTH,
            height = LABEL_HEIGHT,
            label = label,
        }
    }, {"OK"})
end

local function show_text_dialog(text)
    aegisub.dialog.display({
        {
            class = "textbox",
            x = 0,
            y = 0,
            width = DIALOG_WIDTH,
            height = TEXTBOX_HEIGHT,
            text = text,
        }
    }, {"OK"})
end

local function show_missing_pykara_message(output)
    show_text_dialog(table.concat({
        "The `pykara` command is not available in PATH.",
        "",
        "Install it in your environment and ensure the command is available.",
        "",
        "Command output:",
        output,
    }, "\n"))
end

local function strip_ansi(text)
    return (text or ""):gsub("\27%[[%d;]*m", "")
end

local function normalize_output_lines(output)
    local lines = {}
    for raw_line in strip_ansi(output):gmatch("[^\r\n]+") do
        local line = raw_line:gsub("%s+$", "")
        if line ~= "" then
            table.insert(lines, line)
        end
    end
    return lines
end

local function format_output_for_dialog(output)
    local lines = normalize_output_lines(output)
    if #lines > 0 then
        return table.concat(lines, "\n")
    end
    return output or ""
end

local function read_text_file(path)
    local file = io.open(path, "rb")
    if not file then
        return ""
    end

    local content = file:read("*a") or ""
    file:close()
    return content
end

local function remove_file(path)
    if path and path ~= "" then
        os.remove(path)
    end
end

local function new_temp_base()
    local base = os.tmpname()
    if is_windows() and base:match("^\\") then
        local temp_dir = os.getenv("TEMP") or os.getenv("TMP")
        if temp_dir and temp_dir ~= "" then
            base = join_path(temp_dir, base:gsub("^\\+", ""))
        end
    end
    return base
end

local function new_command_paths()
    local base = new_temp_base()
    return {
        base = base,
        output = base .. "-pykara-output.ass",
        stdout = base .. "-pykara-events.txt",
        stderr = base .. "-pykara-error.txt",
        launcher_stderr = base .. "-pykara-launcher-error.txt",
    }
end

local function cleanup_command_paths(paths)
    remove_file(paths.base)
    remove_file(paths.output)
    remove_file(paths.stdout)
    remove_file(paths.stderr)
    remove_file(paths.launcher_stderr)
end

local function reset_command_output_paths(paths)
    remove_file(paths.output)
    remove_file(paths.stdout)
    remove_file(paths.stderr)
    remove_file(paths.launcher_stderr)
end

local function combine_outputs(primary, secondary)
    if primary == "" then
        return secondary
    end
    if secondary == "" then
        return primary
    end
    return primary .. "\n" .. secondary
end

local function is_powershell_progress_clixml(output)
    local text = output or ""
    local trimmed = text:gsub("^%s+", ""):gsub("%s+$", "")

    if not trimmed:match("^#< CLIXML") then
        return false
    end

    local saw_stream_object = false
    for stream in trimmed:gmatch('<Obj S="([^"]+)"') do
        saw_stream_object = true
        if stream ~= "progress" then
            return false
        end
    end

    return saw_stream_object
        and trimmed:match("Preparing modules for first use%.") ~= nil
end

local function normalize_launcher_stderr(output)
    if is_powershell_progress_clixml(output) then
        return ""
    end
    return output or ""
end

local function interpret_command_status(ok, why, code)
    if type(ok) == "number" then
        return ok == 0, true
    end
    if type(ok) == "boolean" then
        local started = ok or why ~= nil or code ~= nil
        return ok and why == "exit" and code == 0, started
    end
    if ok == nil then
        local started = why ~= nil or code ~= nil
        return false, started
    end
    return false, false
end

local function run_shell_command_with_popen(command)
    local ok, pipe = pcall(io.popen, command, "r")
    if not ok or not pipe then
        return false, false
    end

    pipe:read("*a")
    local close_ok, why, code = pipe:close()
    return interpret_command_status(close_ok, why, code)
end

local function run_shell_command(command)
    local ok, result, why, code = pcall(os.execute, command)
    if ok then
        return interpret_command_status(result, why, code)
    end
    return run_shell_command_with_popen(command)
end

local function build_default_command(input_path, paths)
    return table.concat({
        pykara_program(),
        shell_quote(input_path),
        shell_quote(paths.output),
        ">",
        shell_quote(paths.stdout),
        "2>",
        shell_quote(paths.stderr),
    }, " ")
end

local function utf8_to_utf16le(value)
    local bytes = {}
    local index = 1
    local text = tostring(value)

    while index <= #text do
        local byte_1 = text:byte(index)
        local codepoint

        if byte_1 < 0x80 then
            codepoint = byte_1
            index = index + 1
        elseif byte_1 >= 0xC2 and byte_1 < 0xE0 then
            local byte_2 = text:byte(index + 1)
            if not byte_2 or byte_2 < 0x80 or byte_2 > 0xBF then
                return nil
            end
            codepoint = (byte_1 - 0xC0) * 0x40 + (byte_2 - 0x80)
            index = index + 2
        elseif byte_1 >= 0xE0 and byte_1 < 0xF0 then
            local byte_2 = text:byte(index + 1)
            local byte_3 = text:byte(index + 2)
            if not byte_2 or not byte_3 then
                return nil
            end
            if byte_2 < 0x80 or byte_2 > 0xBF or byte_3 < 0x80 or byte_3 > 0xBF then
                return nil
            end
            codepoint = (
                (byte_1 - 0xE0) * 0x1000
                + (byte_2 - 0x80) * 0x40
                + (byte_3 - 0x80)
            )
            index = index + 3
        elseif byte_1 >= 0xF0 and byte_1 < 0xF8 then
            local byte_2 = text:byte(index + 1)
            local byte_3 = text:byte(index + 2)
            local byte_4 = text:byte(index + 3)
            if not byte_2 or not byte_3 or not byte_4 then
                return nil
            end
            if byte_2 < 0x80 or byte_2 > 0xBF
                or byte_3 < 0x80 or byte_3 > 0xBF
                or byte_4 < 0x80 or byte_4 > 0xBF
            then
                return nil
            end
            codepoint = (
                (byte_1 - 0xF0) * 0x40000
                + (byte_2 - 0x80) * 0x1000
                + (byte_3 - 0x80) * 0x40
                + (byte_4 - 0x80)
            )
            index = index + 4
        else
            return nil
        end

        if codepoint <= 0xFFFF then
            table.insert(bytes, string.char(codepoint % 0x100, math.floor(codepoint / 0x100)))
        else
            codepoint = codepoint - 0x10000
            local high = 0xD800 + math.floor(codepoint / 0x400)
            local low = 0xDC00 + (codepoint % 0x400)
            table.insert(bytes, string.char(high % 0x100, math.floor(high / 0x100)))
            table.insert(bytes, string.char(low % 0x100, math.floor(low / 0x100)))
        end
    end

    return table.concat(bytes)
end

local function base64_encode(value)
    local alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    local parts = {}

    for index = 1, #value, 3 do
        local byte_1 = value:byte(index) or 0
        local byte_2 = value:byte(index + 1) or 0
        local byte_3 = value:byte(index + 2) or 0
        local combined = byte_1 * 0x10000 + byte_2 * 0x100 + byte_3
        local count = math.min(3, #value - index + 1)

        local char_1 = math.floor(combined / 0x40000) % 0x40
        local char_2 = math.floor(combined / 0x1000) % 0x40
        local char_3 = math.floor(combined / 0x40) % 0x40
        local char_4 = combined % 0x40

        table.insert(parts, alphabet:sub(char_1 + 1, char_1 + 1))
        table.insert(parts, alphabet:sub(char_2 + 1, char_2 + 1))
        if count > 1 then
            table.insert(parts, alphabet:sub(char_3 + 1, char_3 + 1))
        else
            table.insert(parts, "=")
        end
        if count > 2 then
            table.insert(parts, alphabet:sub(char_4 + 1, char_4 + 1))
        else
            table.insert(parts, "=")
        end
    end

    return table.concat(parts)
end

local function powershell_encoded_command(script)
    local utf16le = utf8_to_utf16le(script)
    if not utf16le then
        return nil
    end
    return base64_encode(utf16le)
end

local function build_windows_powershell_command(input_path, paths, hidden)
    local powershell_script = table.concat({
        "$ProgressPreference = 'SilentlyContinue'\n",
        "$p = Start-Process -FilePath ",
        powershell_quote(pykara_program()),
        " -ArgumentList ",
        powershell_quote(windows_argument_list(input_path, paths.output)),
        " -RedirectStandardOutput ",
        powershell_quote(paths.stdout),
        " -RedirectStandardError ",
        powershell_quote(paths.stderr),
        hidden and " -WindowStyle Hidden" or "",
        " -PassThru -Wait\n",
        "exit $p.ExitCode\n",
    })

    local encoded_command = powershell_encoded_command(powershell_script)
    if not encoded_command then
        return nil
    end

    local parts = {
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-EncodedCommand",
        shell_quote(encoded_command),
        "> NUL",
        "2>",
        shell_quote(paths.launcher_stderr),
    }
    if hidden then
        table.insert(parts, 6, "-WindowStyle Hidden")
    end
    return table.concat(parts, " ")
end

local function build_hidden_windows_command(input_path, paths)
    return build_windows_powershell_command(input_path, paths, true)
end

local function build_visible_windows_command(input_path, paths)
    return build_windows_powershell_command(input_path, paths, false)
end

if rawget(_G, "__pykara_bridge_test__") then
    __pykara_bridge_exports__ = {
        build_default_command = build_default_command,
        build_hidden_windows_command = build_hidden_windows_command,
        build_visible_windows_command = build_visible_windows_command,
        current_subtitle_path = current_subtitle_path,
        is_absolute_path = is_absolute_path,
        windows_argument_quote = windows_argument_quote,
        windows_argument_list = windows_argument_list,
    }
end

local function hidden_launcher_failed(launcher_output, stdout_output, stderr_output)
    return launcher_output ~= "" and stdout_output == "" and stderr_output == ""
end

local function read_command_result(paths, succeeded, started)
    return {
        succeeded = succeeded,
        started = started,
        output = read_text_file(paths.output),
        stdout = read_text_file(paths.stdout),
        stderr = read_text_file(paths.stderr),
        launcher_stderr = normalize_launcher_stderr(
            read_text_file(paths.launcher_stderr)
        ),
    }
end

local function run_command_capture(command, paths)
    reset_command_output_paths(paths)
    local succeeded, started = run_shell_command(command)
    return read_command_result(paths, succeeded, started)
end

local function execute_pykara(input_path)
    local paths = new_command_paths()
    local result

    if is_windows() then
        local hidden_command = build_hidden_windows_command(input_path, paths)
        if hidden_command then
            result = run_command_capture(hidden_command, paths)
            if result.started
                and not result.succeeded
                and hidden_launcher_failed(
                    result.launcher_stderr,
                    result.stdout,
                    result.stderr
                )
            then
                remove_file(paths.launcher_stderr)
                local visible_command = build_visible_windows_command(input_path, paths)
                if visible_command then
                    result = run_command_capture(visible_command, paths)
                end
            end

            if result and result.started
                and not result.succeeded
                and hidden_launcher_failed(
                    result.launcher_stderr,
                    result.stdout,
                    result.stderr
                )
            then
                remove_file(paths.launcher_stderr)
                result = run_command_capture(build_default_command(input_path, paths), paths)
                result.launcher_stderr = ""
            end
        end
    end

    if not result then
        result = run_command_capture(build_default_command(input_path, paths), paths)
    end

    result.error_output = combine_outputs(result.launcher_stderr, result.stderr)
    cleanup_command_paths(paths)
    return result
end

local function parse_ass_time(value)
    local hours, minutes, seconds, centiseconds =
        value:match("^(%d+):(%d%d):(%d%d)%.(%d%d)$")
    if not hours then
        error("Invalid ASS time: " .. tostring(value))
    end
    return (
        (((tonumber(hours) * 60) + tonumber(minutes)) * 60 + tonumber(seconds))
        * 1000
    ) + tonumber(centiseconds) * 10
end

local function split_event_fields(value)
    local fields = {}
    local rest = value

    for _ = 1, 9 do
        local current, next_rest = rest:match("^([^,]*),(.*)$")
        if not current then
            break
        end
        table.insert(fields, current)
        rest = next_rest
    end

    table.insert(fields, rest)
    return fields
end

local function parse_generated_line(raw_line)
    local kind, body = raw_line:match("^(%a+):%s*(.*)$")
    if kind ~= "Dialogue" and kind ~= "Comment" then
        error("Unexpected generated event line: " .. tostring(raw_line))
    end

    local fields = split_event_fields(body)
    return {
        class = "dialogue",
        section = "[Events]",
        comment = kind == "Comment",
        layer = tonumber(fields[1]) or 0,
        start_time = parse_ass_time(fields[2] or "0:00:00.00"),
        end_time = parse_ass_time(fields[3] or "0:00:00.00"),
        style = fields[4] or "",
        actor = fields[5] or "",
        margin_l = tonumber(fields[6]) or 0,
        margin_r = tonumber(fields[7]) or 0,
        margin_t = tonumber(fields[8]) or 0,
        effect = fields[9] or "",
        text = fields[10] or "",
        raw = raw_line,
    }
end

local function parse_generated_output(output)
    local generated_lines = {}
    local in_events = false

    for raw_line in (output or ""):gmatch("[^\r\n]+") do
        local trimmed = raw_line:gsub("^%s+", ""):gsub("%s+$", "")
        local section = trimmed:match("^%[[^%]]+%]$")

        if section then
            in_events = section == "[Events]"
        elseif in_events
            and (raw_line:match("^Dialogue: ") or raw_line:match("^Comment: "))
        then
            local ok, parsed_line = pcall(parse_generated_line, raw_line)
            if not ok then
                return nil, format_output_for_dialog(tostring(parsed_line))
            end

            if (parsed_line.effect or ""):lower() == FX_EFFECT then
                table.insert(generated_lines, parsed_line)
            end
        end
    end

    if output == "" then
        return nil, "Pykara did not write an output ASS file."
    end

    return generated_lines, nil
end

local function is_missing_pykara_output(output)
    local text = output or ""
    return text:match("command not found")
        or text:match("not found")
        or text:match("is not recognized as an internal or external command")
        or text:match("cannot find the file specified")
        or text:match("No module named ['\"]pykara['\"]")
        or text:match("ModuleNotFoundError:.-pykara")
end

local function choose_error_output(result)
    if result.error_output ~= "" then
        return result.error_output
    end
    if result.stdout ~= "" then
        return result.stdout
    end
    return ""
end

local function remove_existing_fx_lines(subs)
    for index = #subs, 1, -1 do
        local line = subs[index]
        if line.class == "dialogue" and (line.effect or "") == FX_EFFECT then
            subs.delete(index)
        end
    end
end

local function comment_source_lines(subs)
    for index = 1, #subs do
        local line = subs[index]
        if line.class == "dialogue" and not line.comment then
            local effect = (line.effect or ""):lower()
            if SOURCE_EFFECTS[effect] then
                line.comment = true
                subs[index] = line
            end
        end
    end
end

local function apply_generated_lines(subs, generated_lines)
    remove_existing_fx_lines(subs)

    for _, generated_line in ipairs(generated_lines) do
        subs.append(generated_line)
    end

    comment_source_lines(subs)
end

local function run_bridge(subs)
    local input_path = current_subtitle_path()
    if not input_path then
        show_label_dialog("Could not resolve the current subtitle path.")
        return
    end

    local result = execute_pykara(input_path)
    local command_output = choose_error_output(result)

    if not result.succeeded then
        if command_output ~= "" then
            if is_missing_pykara_output(command_output) then
                show_missing_pykara_message(format_output_for_dialog(command_output))
                return
            end

            show_text_dialog(format_output_for_dialog(command_output))
            return
        end

        if not result.started then
            show_label_dialog("Could not start the `pykara` command in this Aegisub build.")
            return
        end

        show_label_dialog("`pykara` failed without producing any output.")
        return
    end

    local generated_lines, parse_error = parse_generated_output(result.output)
    if not generated_lines then
        show_text_dialog(format_output_for_dialog(
            combine_outputs(parse_error, result.error_output)
        ))
        return
    end

    apply_generated_lines(subs, generated_lines)
    aegisub.set_undo_point("pykara Apply template")

    if result.error_output ~= "" then
        show_text_dialog(format_output_for_dialog(result.error_output))
    end
end

local function remove_fx(subs)
    remove_existing_fx_lines(subs)
    aegisub.set_undo_point("pykara Remove FX")
end

aegisub.register_macro(
    script_name .. "/Apply template",
    script_description,
    run_bridge
)

aegisub.register_macro(
    script_name .. "/Remove FX",
    "Remove dialogue lines whose Effect field is exactly `fx`.",
    remove_fx
)
