import inspect
import os
import re
from collections import defaultdict
from itertools import chain, groupby
import yaml
from packaging.version import Version, InvalidVersion
import pygments
from pygments.token import Token, Name
from pygments.lexers import get_all_lexers, find_lexer_class_by_name


from parser import convert_to_keywords, ParseException

REQUIRED_TOKEN_TYPES = (Token.Keyword, Name.Builtin)

# Remove '../../' for travis
LANGUAGE_FOLD = os.path.abspath("../../data/Language")

# Read coast language definitions
coast_langs = {}
for lang_file in os.listdir(LANGUAGE_FOLD):
    with open(os.path.join(LANGUAGE_FOLD, lang_file)) as f:
        coast_langs[lang_file.rstrip('.yaml')] = yaml.load(f)


def parse_lang_name(name):
    """Identify the version number of a language if present in its name."""
    try:
        realname, version = name.rsplit(maxsplit=1)
        version = Version(version)
        return realname, version
    except (ValueError, InvalidVersion):  # look for trailing numbers
        match = re.match(r"(?P<realname>.*?)(?P<version>[0-9.]+)$", name)
        if match:
            realname, version = match.groupdict().values()
            try:
                version = Version(version)
                return realname, version
            except InvalidVersion:
                return name, None
        else:
            return name, None


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


def extract_lexer_data(lexer):
    data = {}

    data['name'] = lexer.name

    aliases = getattr(lexer, 'aliases', [])

    if len(aliases) < 10:
        data['aliases'] = aliases
    else:  # dirty workaround for powershell
        print("Too many aliases in", data['name'])
        data['aliases'] = []

    if not data['name'].replace(' ', '').isalnum():
        print(data['name'], data['aliases'], inspect.getsourcefile(lexer))

    filenames = getattr(lexer, 'filenames', [])
    data['extensions'] = []
    data['filenames'] = []
    for name in filenames:
        if '*.' in name:
            ext = name[name.rfind('.') + 1:]
            m = re.match(r'(\w*)\[(\d+)\]$', ext)
            if m:
                name, versions = m.groups()
                if not name:
                    continue
                data['versions'] = []
                for ver in versions:
                    data['extensions'].append(name + ver)
                    data['versions'].append(Version(ver))
            else:
                data['extensions'].append(ext)
        elif '*' not in name:
            data['filenames'].append(name)

    patterns = get_lexer_patterns(lexer, REQUIRED_TOKEN_TYPES)
    keyword_patterns = patterns.get(Token.Keyword)
    if keyword_patterns:
        try:
            keywords = convert_to_keywords(keyword_patterns)
        except ParseException as e:
            # print("Keyword parsing failed for", lexer.name)
            # print('Before parse:', keyword_patterns)
            # print('After parse :', e.keywords)
            data['keywords'] = []
        else:
            data['keywords'] = sorted(keywords)

    return data


def merge_lists(list1, list2):
    return list(sorted(set(list1).union(list2)))


def merge_dict_list(dest, src, param):
    if param not in src:
        return
    dest[param] = merge_lists(dest.get(param, []), src[param])


def merge_versioned_lexers(name, lexers):
    final_data = {'name': name, 'versions': set()}
    for lex in lexers:
        lexer_data = extract_lexer_data(lex)
        merge_dict_list(final_data, lexer_data, 'aliases')
        merge_dict_list(final_data, lexer_data, 'filenames')
        merge_dict_list(final_data, lexer_data, 'extensions')
        merge_dict_list(final_data, lexer_data, 'keywords')
        ver = parse_lang_name(lexer_data['name'])[1]
        if ver:
            final_data['versions'].add(ver)
    final_data['versions'] = list(sorted(final_data['versions']))
    return final_data


def process_lexers():
    pygments_lexers = [find_lexer_class_by_name(lexer[1][0])
                       for lexer in get_all_lexers()]

    grouped_lexers = defaultdict(set)  # group versioned lexers by name
    for name, group in groupby(pygments_lexers,
                               lambda lex: parse_lang_name(lex.name)[0]):
        grouped_lexers[name].update(group)

    for name, lexers in grouped_lexers.items():
        if len(lexers) == 1:
            yield extract_lexer_data(lexers.pop())
        else:
            yield merge_versioned_lexers(name, lexers)


def get_coast_lang(lexer):
    # In case the coast lang identifier matches exactly with the lexer name
    lang = coast_langs.get(lexer['name'])
    if lang is not None:
        return lang

    for lang in coast_langs.values():
        full_name = lang.get('full_name', '').lower()
        if (lexer['name'] == full_name or full_name in lexer['aliases'] or
                lang['identifier'].lower() in lexer['aliases']):
            return lang


def update_coast_def(lang, lexer_data):
    if not lang.get('identifier'):
        lang['identifier'] = lexer_data['name']
        if not lexer_data['name'].replace(' ', '').isalnum():
            lang['identifier'] = lang['identifier'].replace(
                '+', 'Plus').replace('/', '-')

    def update_list(param):
        lex_words = set(lexer_data.get(param, []))
        lang_words = set(lang.get(param, []))
        if lex_words - lang_words:
            lang_words.update(lex_words)
            # print("Updated {} for {}".format(param, lang['identifier']))
            # print("\tBefore:", lang.get(param))
            lang[param] = list(sorted(lang_words))
            # print("\tAfter: ", lang[param])

    update_list('aliases')
    update_list('extensions')
    update_list('filenames')
    update_list('keywords')

    for alias in lang.get('aliases', []):
        if alias.lower() == lexer_data['name'].lower():
            lang['aliases'].remove(alias)


def main():
    for lex_data in process_lexers():
        if '+' in lex_data['name'] and not lex_data.get('keywords'):
            continue
        coast_def = get_coast_lang(lex_data)
        if not coast_def:
            # print("New lexer found:", lex_data['name'])
            coast_def = {}
        update_coast_def(coast_def, lex_data)
        print(coast_def)


if __name__ == '__main__':
    main()
