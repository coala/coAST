import os.path
import yaml
from collections import defaultdict
from itertools import chain

import pygments
from pygments.token import Token
from pygments.lexers import get_all_lexers, get_lexer_by_name

from parser import convert_to_keywords

REQUIRED_TOKEN_TYPES = (Token.Keyword, )


def read_coast_langs():
    # Remove '../../' for travis
    LANGUAGE_FOLD = os.path.abspath("../../data/Language")

    for lang_file in os.listdir(LANGUAGE_FOLD):
        with open(os.path.join(LANGUAGE_FOLD, lang_file)) as f:
            yield lang_file, yaml.load(f)


coast_langs = dict(read_coast_langs())
pygments_lexers = {lexer[1][0]: get_lexer_by_name(lexer[1][0])
                   for lexer in get_all_lexers()}


def get_coast_aliases():
    for lang_file, lang in coast_langs.items():
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
    print("Number of known lexers:", len(known_lexers))
    print("Number of total pygments lexers:", len(pygments_lexers))
    for lexer in pygments_lexers.values():
        if not any(known_lexer.name == lexer.name
                   for known_lexer in known_lexers):
            yield lexer


def get_lexer_patterns(lexer, required_token_types=()):
    patterns = defaultdict(list)
    if not hasattr(lexer, 'tokens'):
        # print('Skipping {}: no tokens'.format(lexer.name))
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
            patterns[current_token_type].extend(re_pattern.words)
        else:
            patterns[current_token_type].append(re_pattern)
    return patterns


def process_pygments():
    all_keywords = {}
    improper = {}
    for lexer in get_new_lexers():
        patterns = get_lexer_patterns(lexer, REQUIRED_TOKEN_TYPES)
        if not patterns:
            # print('Skipping {}: no required tokens'.format(lexer.name))
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


process_pygments()
