import re


def replace_ignore_case(text, pattern, replacement):
    # Compile a regular expression pattern into a regular expression object,
    # which can be used for matching and other methods, with the re.IGNORECASE flag to ignore case.
    regex = re.compile(re.escape(pattern), re.IGNORECASE)
    # Use the sub() method of the compiled regex object to replace occurrences of the pattern.
    return regex.sub(replacement, text)
