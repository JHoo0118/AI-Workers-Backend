import re


def replace_ignore_case(text, pattern, replacement):
    regex = re.compile(re.escape(pattern), re.IGNORECASE)
    return regex.sub(replacement, text)
