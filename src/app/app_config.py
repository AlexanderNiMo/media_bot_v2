import configparser
from os import path
import os
from os.path import exists

CONFIG_FILE_NAME = path.normpath(
    '{0}/conf/{1}'.format(path.dirname(__file__), '.config.ini')
)


def create_default_config(parser: configparser.ConfigParser):
    parser['client'] = {
        'bot_token': '',
        'bot_mode': 1,
        'admin_id': 1
    }
    parser['proxy'] = {
        'url': '',
        'user': '',
        'pass': '',
    }
    parser['webhook'] = {
        'host': '127.0.0.1',
        'port': '5000',
        'ssl_cert': '',
        'ssl_prv_key': '',
        'url_base': '',
    }

    parser['plex'] = {
        'host': '127.0.0.1',
        'port': '32400',
        'token': '',
    }

    parser['database'] = {
        'host': '127.0.0.1',
        'port': '3306',
        'user': 'root',
        'password': 'qwerty',
        'base_name': 'media_data',
    }

    parser['rutracker'] = {
        'user_name': '',
        'password': ''
    }

    parser['Torrents_folders'] = {
        'film_folder': '',
        'serial_folder': ''
    }

    parser['logger'] = {'logger_level': 'info'}

    parser['deluge'] = {
        'host': '',
        'port': 0,
        'user': '',
        'password': '',
    }

    with open(CONFIG_FILE_NAME, 'w') as configfile:
        parser.write(configfile)


class Config:
    conf_parser = configparser.ConfigParser()

    def __init__(self):
        self.base_folder = path.dirname(__file__)
        self.test = None

    @classmethod
    def set_config_file(cls, file=CONFIG_FILE_NAME):
        if path.exists(file):
            cls.conf_parser.read(file)
        else:
            if not path.exists(path.dirname(file)):
                os.mkdir(path.dirname(file))
            create_default_config(cls.conf_parser)

    @classmethod
    def get_parser_data(cls, data_path: list):
        dict_data = cls.conf_parser
        for elem in data_path:
            dict_data = dict_data[elem]
        return dict_data

    def get_path_data(self, pattern):
        data_path = path.normpath(
            pattern.format(path.dirname(self.base_folder))
        )

        if not path.exists(data_path):
            if not path.exists(path.dirname(data_path)):
                os.mkdir(path.dirname(data_path))

        return data_path

    def __getattr__(self, item):
        if item in self.__class__.__dict__.keys():
            return super(self.__class__, self).__getattribute__(item)
        data_dict = {
            'TELEGRAMM_BOT_TOKEN': ['client', 'bot_token'],
            'BOT_MODE': ['client', 'bot_mode'],
            'TELEGRAMM_BOT_USER_ADMIN': ['client', 'admin_id'],
            'PROXY_URL': ['proxy', 'url'],
            'PROXY_USER': ['proxy', 'user'],
            'PROXY_PASS': ['proxy', 'pass'],
            'PLEX_HOST': ['plex', 'host'],
            'PLEX_PORT': ['plex', 'port'],
            'PLEX_TOKEN': ['plex', 'token'],
            'DATABASE_HOST': ['database', 'host'],
            'DATABASE_PORT': ['database', 'port'],
            'DATABASE_USER': ['database', 'user'],
            'DATABASE_PASSWORD': ['database', 'password'],
            'DATABASE_NAME': ['database', 'base_name'],
            'TORRENT_FILM_PATH': ['Torrents_folders', 'film_folder'],
            'TORRENT_SERIAL_PATH': ['Torrents_folders', 'serial_folder'],
            'LOGGER_LEVEL': ['logger', 'logger_level'],
            'DELUGE_HOST': ['deluge', 'host'],
            'DELUGE_PORT': ['deluge', 'port'],
            'DELUGE_USER': ['deluge', 'user'],
            'DELUGE_PASS': ['deluge', 'password'],
        }

        if item in data_dict.keys():
            return self.get_parser_data(data_dict[item])

        path_dict = {
            'TORRENT_FILM_PATH': ['Torrents_folders', 'film_folder'],
            'TORRENT_SERIAL_PATH': ['Torrents_folders', 'serial_folder'],
        }

        if item in path_dict.keys():
            return path.normpath(self.get_parser_data(path_dict[item]))

        base_path_dict = {
            'TORRENT_TEMP_PATH': '{0}/data',
            'CACHE_DB_PATH': '{0}/data/cachedb.db',
        }

        if item in base_path_dict.keys():
            return self.get_path_data(base_path_dict[item])

    @property
    def TEST(self):
        if self.test is None:
            try:
                self.test = self.get_parser_data(['Test'])
            except KeyError:
                self.test = False
        return self.test

    @TEST.setter
    def TEST(self, value):
        self.test = value

    @property
    def TORRENTS(self):
        return {
            'rutracker': {
                'user_name': self.get_parser_data(['rutracker', 'user_name']),
                'password': self.get_parser_data(['rutracker', 'password'])
            }
        }

    @property
    def WEBHOOK(self):
        return {
            'WEBHOOK_HOST': self.get_parser_data(['webhook', 'host']),
            'WEBHOOK_PORT': int(self.get_parser_data(['webhook', 'port'])),
            'WEBHOOK_SSL_CERT': self.get_parser_data(['webhook', 'ssl_cert']),
            'WEBHOOK_SSL_PRIV': self.get_parser_data(['webhook', 'ssl_prv_key']),
            'WEBHOOK_URL_BASE': self.get_parser_data(['webhook', 'url_base']),
        }


default_conf = Config()
default_conf.set_config_file()
