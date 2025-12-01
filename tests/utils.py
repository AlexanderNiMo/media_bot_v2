import multiprocessing
import csv
import os
import pathlib


from media_bot_v2.app.logging import configure_logger
from media_bot_v2.config import read_config
from media_bot_v2.database import DbManager
from media_bot_v2.app_enums import ComponentType
from media_bot_v2.mediator import AppMediator
from media_bot_v2.parser import Parser
from media_bot_v2.crawler import Crawler
from media_bot_v2.command_handler import CommandMessageHandler
from media_bot_v2.clients import BotProtocol


def disable_http_proxy_env():
    os.environ.pop('http_proxy', None)
    os.environ.pop('http_proxy'.upper(), None)
    os.environ.pop('https_proxy', None)
    os.environ.pop('https_proxy'.upper(), None)


class TestEnvCreator:

    def __init__(self):
        self.conf = self.get_test_conf()
        disable_http_proxy_env()
        configure_logger(self.conf)
        self.admin_id = self.conf.tg_cfg.admin_user

        self.mediator_q = None
        self._mediator = None
        self._db = None
        self._parser = None
        self._crawler = None
        self._client = None
        self._command_handler = None

    @property
    def db(self):
        if self._db is None:
            test_db_path = pathlib.Path("test_db.db")
            if test_db_path.exists():
                os.remove(test_db_path)
            test_db_path.touch(exist_ok=True)
            self._db = DbManager(self.conf.db_cfg)
        return self._db

    @property
    def parser(self):
        m = self.mediator
        if self._parser is None:
            self._parser = self.get_client(ComponentType.PARSER)
            self.mediator.add_client(self._parser)
        return self._parser

    @property
    def crawler(self):
        m = self.mediator
        if self._crawler is None:
            self._crawler = self.get_client(ComponentType.CRAWLER)
            self.mediator.add_client(self._crawler)
        return self._crawler

    @property
    def command_handler(self):
        m = self.mediator
        if self._command_handler is None:
            self._command_handler = self.get_client(ComponentType.COMMAND_HANDLER)
            self.mediator.add_client(self._command_handler)
        return self._command_handler

    @property
    def client(self):
        m = self.mediator
        if self._client is None:
            self._client = self.get_client(ComponentType.CLIENT)
            self.mediator.add_client(self._client)
        return self._client

    @property
    def mediator(self):
        if self._mediator is None:
            self.mediator_q = multiprocessing.Queue()
            self._mediator = AppMediator(self.mediator_q, [])
        return self._mediator

    def get_client(self, component_type):
        if component_type == ComponentType.PARSER:
            return Parser(multiprocessing.Queue(), self.mediator_q, self.conf)
        elif component_type == ComponentType.CRAWLER:
            return Crawler(
                multiprocessing.Queue(), self.mediator_q, self.conf, 2
            )
        elif component_type == ComponentType.COMMAND_HANDLER:
            return CommandMessageHandler(
                multiprocessing.Queue(), self.mediator_q, self.conf
            )
        elif component_type == ComponentType.CLIENT:
            return BotProtocol(
                multiprocessing.Queue(), self.mediator_q, self.conf.tg_cfg
            )

    def get_test_conf(self):
        conf = read_config(pathlib.Path("./test_config.json"))
        return conf

    def add_test_user(self, client_id, session, **kwargs):
        user = self.db.add_user(client_id, session=session, **kwargs)
        return user

    def add_test_film(self, session, **kwargs):
        return self.db.add_film(session=session, **kwargs)

    def add_test_serial(self, session, **kwargs):
        return self.db.add_serial(session=session, **kwargs)

    def get_data(self, file_name):
        with open(file_name) as file:
            file_data = csv.DictReader(file, delimiter=';')
            for row in file_data:
                yield row

    def construct_test_db(self):
        session = self.db.get_session()
        admin = self.add_test_user(session=session, client_id=self.admin_id)
        test_data_dir = pathlib.Path(__file__).parent / 'test_db_data'
        for user in self.get_data(test_data_dir / 'users.csv'):
            self.add_test_user(session=session, **user)

        for film in self.get_data(test_data_dir / 'films.csv'):
            self.add_test_film(session=session, client_id=self.admin_id, **film)

        for serial in self.get_data(test_data_dir / 'serials.csv'):
            self.add_test_serial(session=session, client_id=self.admin_id, **serial)

        session.close()

    def clear_test_db(self):
        db_path = '.test.db'
        if os.path.exists(db_path):
            os.remove(db_path)

        if self.mediator.is_alive():
            self.mediator.terminate()

        if self.client.is_alive():
            self.client.terminate()

        if self.parser.is_alive():
            self.parser.terminate()

        if self.crawler.is_alive():
            self.crawler.terminate()


def compare_dicts(dict1: dict, dict2: dict)-> bool:
    return all(dict1[a] == dict2[a] for a in dict1.keys()) and all(dict1[a] == dict2[a] for a in dict2.keys())


if __name__ == '__main__':

    t = TestEnvCreator()
    t.construct_test_db()
