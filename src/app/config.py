import configparser
from os import path
import os

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
        'port': '',
        'user': '',
        'password': '',
    }

    with open(CONFIG_FILE_NAME, 'w') as configfile:
        parser.write(configfile)

conf_parser = configparser.ConfigParser()

if path.exists(CONFIG_FILE_NAME):
    conf_parser.read(CONFIG_FILE_NAME)
else:
    if not path.exists(path.dirname(CONFIG_FILE_NAME)):
        os.mkdir(path.dirname(CONFIG_FILE_NAME))
    create_default_config(conf_parser)


TELEGRAMM_BOT_TOKEN = conf_parser['client']['bot_token']
BOT_MODE = conf_parser['client']['bot_mode']
TELEGRAMM_BOT_USER_ADMIN = conf_parser['client']['admin_id']

PROXY_URL = conf_parser['proxy']['url']
PROXY_USER = conf_parser['proxy']['user']
PROXY_PASS = conf_parser['proxy']['pass']

WEBHOOK = {
    'WEBHOOK_HOST': conf_parser['webhook']['host'],
    'WEBHOOK_PORT': int(conf_parser['webhook']['port']),
    'WEBHOOK_SSL_CERT': conf_parser['webhook']['ssl_cert'],
    'WEBHOOK_SSL_PRIV': conf_parser['webhook']['ssl_prv_key'],
    'WEBHOOK_URL_BASE': conf_parser['webhook']['url_base'],
}

PLEX_HOST = conf_parser['plex']['host']
PLEX_PORT = conf_parser['plex']['port']
PLEX_TOKEN = conf_parser['plex']['token']

DATABASE_HOST = conf_parser['database']['host']
DATABASE_PORT = conf_parser['database']['port']
DATABASE_USER = conf_parser['database']['user']
DATABASE_PASSWORD = conf_parser['database']['password']
DATABASE_NAME = conf_parser['database']['base_name']

TORRENTS = {
    'rutracker': {
        'user_name': conf_parser['rutracker']['user_name'],
        'password': conf_parser['rutracker']['password']
    }
}

TORRENT_TEMP_PATH = path.normpath(
    '{0}/data'.format(path.dirname(__file__))
)
if not path.exists(TORRENT_TEMP_PATH):
    os.mkdir(TORRENT_TEMP_PATH)

CACHE_DB_PATH = path.normpath(
    '{0}/data/{1}'.format(path.abspath(path.dirname(__file__)), 'cachedb.db')
)

TORRENT_FILM_PATH = path.normpath(conf_parser['Torrents_folders']['film_folder'])
if not path.exists(TORRENT_FILM_PATH):
    os.mkdir(TORRENT_FILM_PATH)

TORRENT_SERIAL_PATH = path.normpath(conf_parser['Torrents_folders']['serial_folder'])
if not path.exists(TORRENT_SERIAL_PATH):
    os.mkdir(TORRENT_SERIAL_PATH)

LOGGER_LEVEL = conf_parser['logger']['logger_level']

DELUGE_HOST = conf_parser['deluge']['host']
DELUGE_PORT = conf_parser['deluge']['port']
DELUGE_USER = conf_parser['deluge']['user']
DELUGE_PASS = conf_parser['deluge']['password']