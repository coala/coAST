import os
import re
from collections import defaultdict, OrderedDict
from itertools import chain, groupby
import yaml
from yaml.dumper import SafeDumper
from yaml.loader import SafeLoader
from packaging.version import Version, InvalidVersion
import pygments
from pygments.token import Token, Name
from pygments.lexers import get_all_lexers, find_lexer_class_by_name

from parser import convert_to_keywords
DEFAULT_MAPPING_TAG = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG


class YAMLLoader(SafeLoader):
    """Custom loader for YAML to preserve ordering of keys."""

    def construct_ordered_dict(self, node):
        return OrderedDict(self.construct_pairs(node))


class YAMLDumper(SafeDumper):
    """Custom dumper for YAML to match coAST style"""

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)

    def represent_ordered_dict(self, data):
        return self.represent_dict(data.items())


YAMLLoader.add_constructor(
    DEFAULT_MAPPING_TAG, YAMLLoader.construct_ordered_dict)
YAMLDumper.add_representer(OrderedDict, YAMLDumper.represent_ordered_dict)

REQUIRED_TOKEN_TYPES = (Token.Keyword, Name.Builtin)

LANGUAGE_FOLD = os.path.abspath("../../data/Language")

# Read coast language definitions
coast_langs = {}
for lang_file in os.listdir(LANGUAGE_FOLD):
    name = lang_file[:lang_file.rfind('.yaml')]
    with open(os.path.join(LANGUAGE_FOLD, lang_file)) as f:
        coast_langs[name] = yaml.load(f, Loader=YAMLLoader)


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

    data['name'] = lexer.name

    aliases = getattr(lexer, 'aliases', [])
    try:
        aliases.remove(data['name'].lower())
    except ValueError:
        pass

    if len(aliases) < 10:
        data['aliases'] = aliases
    else:  # dirty workaround for powershell
        print("Too many aliases in", data['name'])
        data['aliases'] = []

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
        keywords = convert_to_keywords(keyword_patterns)
        data['keywords'] = list(sorted(set(keywords)))

    return data


def merge_versioned_lexers(name, lexers):
    final_data = {'name': name, 'versions': set()}
    for lex in lexers:
        lexer_data = extract_lexer_data(lex)

        def update_list(param):
            data = set(final_data.get(param, [])).union(
                lexer_data.get(param, []))
            final_data[param] = list(sorted(data))

        update_list('aliases')
        update_list('filenames')
        update_list('extensions')
        update_list('keywords')
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


def filter_lexer(lex_data):
    """Determine if the lexer data should be added to coast definitions."""
    return not lex_data.get('keywords') and (
        any(word in lex_data['name'] for word in ('+', 'Template', 'ANTLR')) or
        (len(lex_data.get('aliases', [])) < 2 and
            len(lex_data.get('extensions', [])) < 2)
    )


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
            print("Updated {} for {}".format(param, lang['identifier']))
            print("\tBefore:", lang.get(param))
            lang[param] = list(sorted(lang_words))
            print("\tAfter: ", lang[param])

    update_list('aliases')
    update_list('extensions')
    update_list('filenames')
    update_list('keywords')


def write_yaml(coast_def):
    file_name = coast_def['identifier'] + '.yaml'
    with open(os.path.join(LANGUAGE_FOLD, file_name), 'w') as f:
        yaml.dump(coast_def, f, allow_unicode=True,
                  default_flow_style=False, Dumper=YAMLDumper)


def main():
    for lex_data in filter(lambda l: not filter_lexer(l), process_lexers()):
        coast_def = get_coast_lang(lex_data)
        if not coast_def:
            coast_def = {}
        coast_def = OrderedDict(coast_def)
        update_coast_def(coast_def, lex_data)
        write_yaml(coast_def)


if __name__ == '__main__':
    main()
