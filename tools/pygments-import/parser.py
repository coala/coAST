import re
import sre_yield

REPLACEMENTS = {
    '?:': '',
    '\\s': ' ',
    '\\t': ' ',
    '\\r': ' ',
    '\\n': ' ',
    '\\!': '!',
    '\\=': '=',
    '\\<': '<',
    '\\>': '>',
    '\\b': '',
    '\\w': ''
}


def clean_pattern(pattern):
    """Unescape and remove unecessary parts from the regex pattern."""
    pattern = re.sub(r'(?<!\\)(?:(\\\\)*)[*+.$^]', '', pattern)
    pattern = re.sub(r'\[\^.\]', '', pattern)
    # pattern = re.sub(r'\\r')
    for orig, repl in REPLACEMENTS.items():
        pattern = pattern.replace(orig, repl)
    pattern = re.sub(r'\[\]', '', pattern)
    return pattern


def convert_to_keywords(pats):
    kw = []
    for pattern in pats:
        pat = clean_pattern(pattern)
        try:
            kw.extend(sre_yield.AllStrings(pat))
        except (MemoryError, OverflowError, sre_yield.ParseError, re.error) as e:
            print(e)
            print(pat, pattern)

    return kw
