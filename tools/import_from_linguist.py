import requests
import yaml
import os

req = requests.get('https://raw.githubusercontent.com/github/linguist/master/lib/linguist/languages.yml')

languages_yml = yaml.safe_load(req.text)

for language in languages_yml:
    if language[0].upper()+language[1:].replace(' ', '')+'.yaml' not in os.listdir('data/Language'):
        # This language doesn't have a data file yet
        language_yml = languages_yml[language]
        new_language = {
            'identifier': language[0].upper()+language[1:].replace(' ', ''),
            'github_language_id': language_yml['language_id']
        }

        if 'aliases' in language_yml:
            new_language['aliases'] = language_yml['aliases']
        if 'extensions' in language_yml:
            new_language['extensions'] = language_yml['extensions']
        if 'type' in language_yml:
            new_language['type'] = language_yml['type']
        if 'interpreters' in language_yml:
            new_language['interpreters'] = language_yml['interpreters']

        stream = open('data/Language/'+language[0].upper()+language[1:].replace(' ', '')+'.yaml', 'w')
        yaml.dump(new_language, stream)
