import os.path
import yaml
from collections import defaultdict
from itertools import chain

import pygments
from pygments.token import Token
from pygments.lexers import get_all_lexers, get_lexer_by_name

LANGUAGE_FOLD = os.path.abspath("/data/Language")


def get_coast_aliases():
    for lang_file in os.listdir(LANGUAGE_FOLD):
        with open(os.path.join(LANGUAGE_FOLD, lang_file)) as f:
            lang = yaml.load(f)
        possible_names = set((lang['identifier'], lang_file.rstrip('.yaml')))
        possible_names.update(lang.get('aliases', []))
        if 'full_name' in lang:
            possible_names.add(lang['full_name'])
        yield list(possible_names)


def get_existing_lexers():
    for aliases in get_coast_aliases():
        for alias in aliases:
            try:
                yield get_lexer_by_name(alias)
                break
            except pygments.util.ClassNotFound:
                pass
        else:
            print("No lexer for ", aliases[0])


def find_new_lexers():
    known_lexers = list(get_existing_lexers())
    all_lexers = [get_lexer_by_name(lexer[1][0]) for lexer in get_all_lexers()]
    print("Number of known lexers:", len(known_lexers))
    print("Number of total pygments lexers:", len(all_lexers))
    for lexer in all_lexers:
        if not any(known_lexer.name == lexer.name
                   for known_lexer in known_lexers):
            yield lexer


def get_lexer_patterns(lexer, required_token_types=[]):
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
        if not isinstance(re_pattern, str):
            print("Invalid re_pattern for ", token_type, re_pattern)
            continue
        patterns[current_token_type].append(re_pattern)
    return patterns


def process_pygments():
    required_token_types = [Token.Comment, Token.Keyword]
    new_lexers = list(find_new_lexers())
    print("Number of unknown lexers:", len(new_lexers))
    lexer_patterns = {}
    for lexer in new_lexers:
        patterns = get_lexer_patterns(lexer, required_token_types)
        if patterns:
            lexer_patterns[lexer] = patterns
    print("Number of new patterns:", len(lexer_patterns))
    print(lexer_patterns)
