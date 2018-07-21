from .alch_db import get_session, init_db
from app_enums import UserRule


class DB_Manager():

    def __init__(self, config):

        self.config = config
        self.__enj = None

    def __get_connection_str(self):
        return ''

    @property
    def engine(self):
        if self.__enj is None:
            return init_db(self.__get_connection_str())

    @property
    def session(self):
        return get_session(self.engine)()

    def find_media(self, kinopoisk_id, type):
        """
        Ищет фильм по kinopoisk_id

        :param kinopoisk_id:
        :return:
        """
        pass

    def find_media_by_label(self, label, year, type):
        """


        :param label:
        :param year:
        :param type:
        :return:
        """
        pass

    def find_user(self, client_id):
        """

        :param client_id:
        :return:
        """
        pass


    def add_film(self, kinopoisk_id, label, year):
        pass


    def add_serial(self, kinopoisk_id, label, year, season, max_series):
        pass


    def add_user(self, clien_id, name='', last_name='', nick_name='', rule=UserRule.USER):
        pass


    def change_user_option(self, clien_id, option, value):
        pass


