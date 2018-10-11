from .alch_db import get_session, init_db
from app_enums import UserRule, UserOptions


class DbManager:
    from .alch_db.model import User, Serial, Film, UserOptionsT

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
        Ищет фильм по стандартным реквизитам

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
        return self.session.query(self.User).filter_by(client_id=client_id).first()

    def add_film(self, kinopoisk_id, label, year):
        pass

    def add_serial(self, kinopoisk_id, label, year, season, max_series=0):
        pass

    def add_user(self, clien_id, name='', last_name='', nick_name='', rule=UserRule.USER):
        pass

    def change_user_option(self, clien_id, option_name: UserOptions, value):

        session = self.session

        result = session.query(self.User, self.UserOptionsT).\
                    filter(self.User.id == self.UserOptionsT.user_id).\
                    filter(self.User.client_id == clien_id).\
                    filter(self.UserOptionsT.option == option_name).first()
        if result is None:
            opt = self.UserOptionsT(option=option_name, value=value)
            user = self.find_user(client_id=clien_id)
            user.options.append(opt)
        else:
            user, opt = result
            opt.value = value
        if user is None:
            raise ValueError('No user with client id {0}'.format(clien_id))

        session.add(opt)
        session.add(user)
        session.commit()

if __name__ == '__main__':

    from .alch_db.model import User
    from .alch_db.model import create_test_env

    s = create_test_env()

    result = s.query(User).\
                    filter(User.id == '111').first()
    print(result)

