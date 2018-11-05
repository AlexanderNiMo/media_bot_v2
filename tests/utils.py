import multiprocessing
import csv
import os

import src
from src.database import DbManager, MediaData


class TestEnvCreator:

    def __init__(self):
        self.conf = self.get_test_conf()
        self.admin_id = self.conf.TELEGRAMM_BOT_USER_ADMIN
        self.mediator_q = multiprocessing.Queue()
        self.db = DbManager(self.conf)
        self.parser = self.get_client(src.app_enums.ComponentType.PARSER)

    def get_client(self, component_type):
        if component_type == src.app_enums.ComponentType.PARSER:
            return src.parser.Parser(multiprocessing.Queue(), self.mediator_q, self.conf)

    def get_test_conf(self):
        conf = src.app.config
        conf.set_config_file(os.path.abspath('./test_config.ini'))
        conf.TEST = True
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
        for user in self.get_data('./test_db_data/users.csv'):
            self.add_test_user(session=session, **user)

        for film in self.get_data('./test_db_data/films.csv'):
            self.add_test_film(session=session, client_id=self.admin_id, **film)

        for serial in self.get_data('./test_db_data/serials.csv'):
            self.add_test_serial(session=session, client_id=self.admin_id, **serial)

        session.close()


if __name__ == '__main__':

    t = TestEnvCreator()
    t.construct_test_db()