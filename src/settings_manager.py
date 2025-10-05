import json


class SettingsManager:
    def __init__(self, settings_file='settings.json'):
        with open(settings_file, 'r', encoding='utf-8') as fp:
            self.settings = json.load(fp)

    def get(self, key, default=None):
        return self.settings.get(key, default)
    
    def set(self, key, value):
        self.settings[key] = value
        with open('settings.json', 'w', encoding='utf-8') as fp:
            json.dump(self.settings, fp, indent=2)