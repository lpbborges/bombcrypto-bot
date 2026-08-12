import os
import re


def fix_mixed_decorators(content, prefix="self.bot.config"):
    # We want to find any `@patch.object(BotConfig, "key", val)`
    # remove it, and append `prefix.key = val` to the start of the next `def test_...` block.

    # We can split the file by `def test_` and process each block
    lines = content.split("\n")
    new_lines = []

    pending_assignments = []

    for i, line in enumerate(lines):
        # Check for patch
        m = re.match(r'^([ \t]*)@patch\.object\(BotConfig,\s*"([^"]+)",\s*(.+)\)', line)
        if m:
            indent = m.group(1)
            key = m.group(2)
            val = m.group(3)
            if val.endswith(")"):
                val = val[:-1]
            pending_assignments.append((indent, key, val))
            continue

        new_lines.append(line)

        # Check for def
        if pending_assignments and re.match(r"^[ \t]*def\s+", line):
            # We found a def, wait until the def block ends (i.e. we see the colon)
            # Actually we can just insert after the docstring or first line
            pass

    # Better approach: parse line by line
    new_lines = []
    pending_assignments = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r'^([ \t]*)@patch\.object\(BotConfig,\s*"([^"]+)",\s*(.+)\)', line)
        if m:
            indent = m.group(1)
            key = m.group(2)
            val = m.group(3)
            if val.endswith(")"):
                val = val[:-1]
            pending_assignments.append((indent, key, val))
            i += 1
            continue

        new_lines.append(line)

        m_def = re.match(r"^([ \t]*)def\s+[a-zA-Z0-9_]+\s*\(", line)
        if pending_assignments and m_def:
            # We must skip until we find the ':'
            while i + 1 < len(lines) and not re.search(r":\s*$", lines[i]):
                i += 1
                new_lines.append(lines[i])

            # now we insert the assignments
            indent = m_def.group(1)
            body_indent = indent + "    "
            for _, key, val in pending_assignments:
                new_lines.append(f"{body_indent}{prefix}.{key} = {val}")
            pending_assignments = []

        i += 1

    return "\n".join(new_lines)


def fix_with_patch(content, prefix="self.bot.config"):
    pattern = re.compile(
        r'([ \t]*)with patch\.object\(BotConfig,\s*"([^"]+)",\s*([^)]+)\):\n((?:(?:\1(?:    |\t).*\n)|(?:[ \t]*\n))*)'
    )

    def repl(m):
        indent = m.group(1)
        key = m.group(2)
        val = m.group(3)
        block = m.group(4)

        new_block_lines = []
        for line in block.split("\n"):
            if line.startswith(indent + "    "):
                new_block_lines.append(line[len(indent) + 4 :])
            elif line.startswith(indent + "\t"):
                new_block_lines.append(line[len(indent) + 1 :])
            else:
                new_block_lines.append(line)
        new_block = "\n".join(new_block_lines[:-1]) + "\n"

        return f"{indent}{prefix}.{key} = {val}\n{new_block}"

    while True:
        new_content = pattern.sub(repl, content)
        if new_content == content:
            break
        content = new_content

    # Handle multiple patch inside a single with
    # Look for:
    # with (
    #     patch.object(BotConfig, "key", val),
    # ...
    # ):
    # It's tricky to regex, let's do a simple replace since test_bot_logic has it
    return content


for root, _, files in os.walk("tests"):
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            with open(path) as f:
                content = f.read()

            if "test_bot_logic.py" in file:
                prefix = "self.bot.config"
            elif "test_actions.py" in file:
                prefix = "self.action_engine.config"
            elif "test_browser.py" in file:
                prefix = "self.browser_manager.config"
            elif "test_vision.py" in file:
                prefix = "self.vision.config"
            else:
                prefix = "config"

            content = fix_mixed_decorators(content, prefix)
            content = fix_with_patch(content, prefix)

            # Additional replace for the grouped `with (`
            # We can just replace `patch.object(BotConfig, "x", y),` with `prefix.x = y`
            # and change `with (` to something harmless.

            with open(path, "w") as f:
                f.write(content)
