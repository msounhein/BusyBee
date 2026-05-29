# Helpers for the LLM API integration
import re
import json


def strip_thinking_tags(text):
    if not text:
        return text
    return re.sub(r'<thinking>.*?</thinking>\s*', '', text, flags=re.DOTALL).strip()


def _extract_json_object(text):
    start = text.find('{')
    if start == -1:
        return None, 0
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == chr(92) and in_string:
            escape = True
            continue
        if c == chr(34) and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return text[start:i+1], i+1
    return None, 0


def _parse_parameter_tags(content):
    """Parse grouped parameter tags into tool calls.

    Model sometimes outputs parameter tags on one line:
        <parameter name="company">WSI</parameter> <parameter name="section">experience</parameter> <parameter name="text">Built...</parameter>

    All tags are found via findall() regardless of line breaks.
    Tags are grouped into tool call dicts by proximity/sequence.
    When a group has 'text' and 'section' keys, it maps to 'add_resume_bullet'.
    Returns (display_text, list_of_tool_dicts).
    """
    if not content:
        return content, []

    tools = []

    # Find ALL parameter tags regardless of line breaks
    param_pattern = r'<parameter\s+name="([^"]+)">\s*([^<]*?)\s*</parameter>'
    matches = re.findall(param_pattern, content)

    if not matches:
        return content, []

    # Group consecutive parameters into tool calls.
    # We treat ALL matched parameters as one group (they appear sequentially).
    # If there are natural breaks (e.g. double newlines between groups), we split.
    # For the common case of all-on-one-line, it's one group.

    # Strategy: find all tag positions to detect group boundaries
    tag_positions = list(re.finditer(param_pattern, content))

    groups = []
    current_group = []

    for idx, pos_match in enumerate(tag_positions):
        key, value = pos_match.group(1), pos_match.group(2)
        if idx > 0:
            # Check the text between previous tag end and this tag start
            prev_end = tag_positions[idx - 1].end()
            curr_start = pos_match.start()
            gap_text = content[prev_end:curr_start]
            # If there's a blank line (double newline) in the gap, start a new group
            if '\n\n' in gap_text:
                if current_group:
                    groups.append(current_group)
                    current_group = []
        current_group.append((key.strip(), value.strip()))

    if current_group:
        groups.append(current_group)

    for group in groups:
        params = {k: v for k, v in group}
        if 'text' in params and 'section' in params:
            # Emit the mapped tool call AND a generic one
            tools.append({'tool': 'add_resume_bullet', 'args': params})
            tools.append({'tool': 'generic_parameter_call', 'args': params})
        else:
            tool_name = 'generic_parameter_call'
            tools.append({'tool': tool_name, 'args': params})

    # Strip all parameter tags from display text
    display = re.sub(param_pattern, '', content)
    # Clean up leftover whitespace
    display = re.sub(r'[ \t]+', ' ', display)
    display = re.sub(r'\n\s*\n', '\n', display)
    display = display.strip()

    return display, tools


def parse_tool_calls_from_content(content):
    """Parse tool calls from model output.

    Handles ACTION blocks, minimax:invoke XML, and parameter tags.
    Returns (clean_display_text, list_of_parsed_tool_dicts).
    """
    if not content:
        return content, []

    tools = []

    # 1. Parse ACTION blocks
    for match in re.finditer(r'<<ACTION>>', content):
        after_action = content[match.end():]
        json_str, _ = _extract_json_object(after_action)
        if json_str:
            try:
                action = json.loads(json_str)
                tools.append(action)
            except json.JSONDecodeError:
                pass

    # 2. Parse minimax:invoke XML
    xml_pattern = r'<minimax:invoke\s+name=\"([^\"]+)\">\s*(.*?)\s*</minimax:invoke>'
    for match in re.finditer(xml_pattern, content, re.DOTALL):
        tool_name = match.group(1)
        args_raw = match.group(2).strip()
        try:
            tool_args = json.loads(args_raw)
            tools.append({'tool': tool_name, 'args': tool_args})
        except json.JSONDecodeError:
            tools.append({'tool': tool_name, 'args': {}})

    # 3. Parse parameter tags (grouped)
    param_display, param_tools = _parse_parameter_tags(content)
    tools.extend(param_tools)
    content = param_display

    # 4. Deduplicate
    seen = set()
    unique_tools = []
    for t in tools:
        key = (t.get('tool'), json.dumps(t.get('args', {}), sort_keys=True))
        if key not in seen:
            seen.add(key)
            unique_tools.append(t)
    tools = unique_tools

    # 5. Strip artifacts
    display = content
    display = re.sub(r'<<ACTION>>.*?(?:<</ACTION>>|$)', '', display, flags=re.DOTALL)
    display = re.sub(r'<minimax:invoke[^>]*>.*?</minimax:invoke>', '', display, flags=re.DOTALL)
    display = re.sub(r'</?(?:minimax:invoke|minimax:tool_call|invoke)[^>]*>', '', display)
    display = strip_thinking_tags(display)
    display = display.strip()

    return display, tools
