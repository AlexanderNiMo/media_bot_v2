import configparser
from os import path

CONFIG_FILE_NAME = '.config.ini'


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

    with open(CONFIG_FILE_NAME, 'w') as configfile:
        parser.write(configfile)

conf_parser = configparser.ConfigParser()

if path.exists(CONFIG_FILE_NAME):
    conf_parser.read(CONFIG_FILE_NAME)
else:
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


