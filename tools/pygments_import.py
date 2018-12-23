import os.path
import yaml
from collections import defaultdict
from itertools import chain
import re

import pygments
from pygments.token import Token
from pygments.lexers import get_all_lexers, get_lexer_by_name


LANGUAGE_FOLD = os.path.abspath("../data/Language")  # Remove '../' for travis
REQUIRED_TOKEN_TYPES = (Token.Keyword, )


def get_coast_aliases():
    for lang_file in os.listdir(LANGUAGE_FOLD):
        with open(os.path.join(LANGUAGE_FOLD, lang_file)) as f:
            lang = yaml.load(f)
        possible_names = set((lang['identifier'], lang_file.rstrip('.yaml')))
        possible_names.update(lang.get('aliases', []))
        if 'full_name' in lang:
            possible_names.add(lang['full_name'])
        yield list(possible_names)


def get_coast_lexers():
    for aliases in get_coast_aliases():
        for alias in aliases:
            try:
                yield get_lexer_by_name(alias)
                break
            except pygments.util.ClassNotFound:
                pass
        else:
            print("No lexer for", aliases[0])


def get_new_lexers():
    known_lexers = list(get_coast_lexers())
    all_lexers = [get_lexer_by_name(lexer[1][0]) for lexer in get_all_lexers()]
    print("Number of known lexers:", len(known_lexers))
    print("Number of total pygments lexers:", len(all_lexers))
    for lexer in all_lexers:
        if not any(known_lexer.name == lexer.name
                   for known_lexer in known_lexers):
            yield lexer


def get_lexer_patterns(lexer, required_token_types=()):
    patterns = defaultdict(list)
    if not hasattr(lexer, 'tokens'):
        print('Skipping {}: no tokens'.format(lexer.name))
        return patterns

    # no need to handle each section separately
    for token in chain(*lexer.tokens.values()):
        if not isinstance(token, tuple) or len(token) != 2:
            continue
        re_pattern, token_type = token
        current_token_type = None
        if not required_token_types:
            current_token_type = token_type
        for super_type in required_token_types:
            assert super_type in Token
            if token_type in super_type:
                current_token_type = super_type
                break
        if not current_token_type:
            continue
        if isinstance(re_pattern, pygments.lexer.words):
            re_pattern = re_pattern.get()
        patterns[current_token_type].append(re_pattern)
    return patterns


def clean_pattern(pattern):
    """Unescape and remove unecessary parts from the regex pattern."""
    REPLACEMENTS = {
        '?:': '',
        '\\b': '',
        '\\s+': ' ',
        '\\s*': '',
        '\\*': '*',
        '\\-': '-',
        '\\.': '.',
        '\\?': '?',
        '\\\\': '\\'
    }
    for orig, repl in REPLACEMENTS.items():
        pattern = pattern.replace(orig, repl)
    return pattern


def split_on_paren(re_pattern):
    """Split the pattern into three parts, one enclosed by the outermost
       parentheses, one to the left of opening paren, and one to the right."""
    parts = [part for part in re.split(r'(\W)', re_pattern) if part]
    try:
        left_ind = parts.index('(')
    except ValueError:
        left_ind = 0
    try:
        right_ind = -parts[::-1].index(')')
    except ValueError:
        right_ind = 0
    prefix = ''.join(parts[:left_ind])
    middle = ''.join(parts[left_ind:right_ind or len(parts)])
    suffix = ''.join(parts[right_ind:]) if right_ind else ''
    if any(c in suffix or c in prefix for c in '(|)'):
        return '', re_pattern, ''
    return prefix, middle, suffix


def get_subparts(re_pattern, depth=0):
    """Break down the pattern into smaller parts, due to '|'"""

    if not re_pattern:
        return []
    if re_pattern[0] == '(' and re_pattern[-1] == ')':
        re_pattern = re_pattern[1:-1]
    parts = [part for part in re.split(r'(\W)', re_pattern) if part]
    sub_parts = []
    prev_end = 0
    open_paren_count = 0

    # Handle '|' metacharacter, match either of the two
    for index, part in enumerate(parts):
        if part == '(':
            open_paren_count += 1
        elif part == ')':
            open_paren_count -= 1
        elif part == '|' and open_paren_count == depth:
            sub_parts.append(''.join(parts[prev_end:index]))
            prev_end = index + 1
    sub_parts.append(''.join(parts[prev_end:]))

    # Handle '?' metacharacter, either 0 or 1 match
    for index, sub_part in enumerate(sub_parts):
        if sub_part.endswith(')?'):
            prefix, middle, suffix = split_on_paren(sub_part)
            sub_parts[index] = prefix + middle[1:-1]
            sub_parts.append(prefix)

    # Expand '[]' metachars, match any one char inside
    sub_parts_removed = []  # parts to be removed
    for index, sub_part in enumerate(sub_parts):
        if sub_part.startswith('[') and sub_part.endswith(']'):
            prefix, middle, suffix = split_on_paren(sub_part[1:-1])
            parts = []
            if not prefix and not suffix:
                parts = middle
            else:
                prefix.split() + [middle] + suffix.split()
            for part in parts:
                sub_parts.append(part)
            sub_parts_removed.append(index)

    # remove original subpart, which contains [...]
    for ind, to_be_removed in enumerate(sub_parts_removed):
        del sub_parts[to_be_removed - ind]

    return sub_parts


def extract_keywords(re_pattern):
    """Recursively parse the regex pattern to find all the possible
       strings that may match the pattern."""
    if not re_pattern:
        return ['']

    sub_parts = get_subparts(re_pattern)
    if len(sub_parts) == 1 and sub_parts[0] == re_pattern:
        prefix, middle, suffix = split_on_paren(re_pattern)
        if not suffix and not prefix:  # no further splitting is possible
            return sub_parts

    keywords = []
    for part in sub_parts:
        prefix, middle, suffix = split_on_paren(part)
        for keyword in extract_keywords(middle):
            keywords.append(prefix + keyword + suffix)
    return keywords


def convert_to_keywords(lexer_patterns):
    lexer_keywords = defaultdict(list)
    success = True
    for pattern_type, patterns in lexer_patterns.items():
        for pattern in patterns:
            compiled = re.compile(pattern)
            keywords = extract_keywords(clean_pattern(pattern))
            if any(compiled.match(keyword) is None for keyword in keywords):
                success = False
            lexer_keywords[pattern_type].append(keywords)
    return success, lexer_keywords


def process_pygments():
    all_keywords = {}
    improper = {}
    for lexer in get_new_lexers():
        patterns = get_lexer_patterns(lexer, REQUIRED_TOKEN_TYPES)
        if not patterns:
            print('Skipping {}: no required tokens'.format(lexer.name))
            continue
        success, keywords = convert_to_keywords(patterns)
        if success:
            all_keywords[lexer.name] = keywords
        else:
            improper[lexer.name] = (keywords, patterns)

    print("Found new keywords for {} languages.".format(len(all_keywords)))
    print(*all_keywords.keys(), sep='\n' if len(all_keywords) < 10 else ', ')
    print("Couldn't extract keywords for {} languages".format(len(improper)))
    for lexer, data in improper.items():
        print(lexer, data[0], data[1], sep='\n\t')
    return all_keywords, improper


all_keywords, improper = process_pygments()
