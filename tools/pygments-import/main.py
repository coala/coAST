import re
import yaml
import os.path
from collections import defaultdict
from itertools import chain

from packaging.version import Version, InvalidVersion
import pygments
from pygments.token import Token
from pygments.lexers import get_all_lexers, find_lexer_class_by_name

from parser import convert_to_keywords

REQUIRED_TOKEN_TYPES = (Token.Keyword, )

# Remove '../../' for travis
LANGUAGE_FOLD = os.path.abspath("../../data/Language")

# Read coast language definitions
coast_langs = {}
for lang_file in os.listdir(LANGUAGE_FOLD):
    with open(os.path.join(LANGUAGE_FOLD, lang_file)) as f:
        coast_langs[lang_file.rstrip('.yaml')] = yaml.load(f)

# # Get all pygments lexers
pygments_lexers = {find_lexer_class_by_name(lexer[1][0])
                   for lexer in get_all_lexers()}


def get_coast_lang_lexers(lang_filename, lang):
    def gen_versioned_names(name, version):
        try:
            version = Version(version)
            # print(version.)
        except InvalidVersion:
            return
        yield name + " " + str(version.release[0])
        yield name + str(version.release[0])
        yield name + " " + version.base_version
        yield name + version.base_version

    possible_names = {lang_filename, lang['identifier']}
    possible_names.update(lang.get('aliases', []))
    if 'full_name' in lang:
        possible_names.add(lang['full_name'])

    lexers = set()

    for alias in possible_names:
        try:
            lex = find_lexer_class_by_name(alias)
        except pygments.util.ClassNotFound:
            pass
        else:
            lexers.add(lex)
            break
    else:
        print("No lexer for", lang_filename)
        return

    for version in lang.get('versions', '').split(', '):
        for versioned_name in gen_versioned_names(lex.name, version):
            try:
                versioned_lex = find_lexer_class_by_name(versioned_name)
            except pygments.util.ClassNotFound:
                pass
            else:
                lexers.add(versioned_lex)
                break
    return tuple(lexers)


coast_lexers = {lang_file: get_coast_lang_lexers(lang_file, lang)
                for lang_file, lang in coast_langs.items()}


def update_coast_def(lang, lexer):
    lexer_data = extract_lexer_data(lexer)

    def update_list(param):
        lex_keywords = set(lexer_data.get(param, []))
        lang_keywords = set(lang.get(param, []))
        lang_keywords.update(lex_keywords)
        if lang_keywords:
            lang[param] = list(sorted(lang_keywords))

    update_list('keywords')


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
            patterns[current_token_type].extend(re_pattern.words)
        else:
            patterns[current_token_type].append(re_pattern)
    return patterns


def extract_lexer_data(lexer):
    data = {}
    patterns = get_lexer_patterns(lexer, REQUIRED_TOKEN_TYPES)
    if patterns.get(Token.Keyword):
        success, keywords = convert_to_keywords(patterns[Token.Keyword])
        if success:
            data['keywords'] = list(chain(*keywords))
    return data


def detect_versioned_langs(name1, name2):
    realname1, version1 = parse_lang_name(name1)
    realname2, version2 = parse_lang_name(name2)
    if version1 is None and version2 is None:
        return False
    elif realname1 == realname2:
        return True, version1, version2
    return False


def parse_lang_name(name):
    """Identify the version number of a language from its name."""
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


if __name__ == '__main__':
    import json
    import difflib
    c = coast_langs['Python']
    s = json.dumps(c, indent=4).splitlines(keepends=True)
    l = get_coast_lang_lexers('Python', c)
    update_coast_def(c, l[0])
    b = json.dumps(c, indent=4).splitlines(keepends=True)
    print(*difflib.unified_diff(s, b))

    # lexer_product = ((x, y) for i, x in enumerate(pygments_lexers)
    #                  for y in pygments_lexers[i + 1:])
    # versioned_lexers = list(
    #     filter(lambda x: detect_versioned_langs(x[0].name, x[1].name),
    #            lexer_product))
    # print(versioned_lexers)
