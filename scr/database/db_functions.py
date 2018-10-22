from database.alch_db import get_session, init_db, OperationalError, create_db
from app_enums import UserRule, UserOptions, MediaType, LockingStatus


class DbManager:
    from database.alch_db.model import User, MediaData, Serial, Film, UserOptionsT

    def __init__(self, config):

        self.config = config
        self.__enj = None
        self.__session = None

    def __get_connection_str(self):
        return 'mysql+mysqldb://{0}:{1}@{2}:{3}'.format(
            self.config.DATABASE_USER,
            self.config.DATABASE_PASSWORD,
            self.config.DATABASE_HOST,
            self.config.DATABASE_PORT
        )

    @property
    def engine(self):
        if self.__enj is None:
            try:
                self.__enj = init_db(self.__get_connection_str(), self.config.DATABASE_NAME)
            except OperationalError:
                create_db(self.__get_connection_str(), self.config.DATABASE_NAME)
                self.__enj = init_db(self.__get_connection_str(), self.config.DATABASE_NAME)
        return self.__enj

    @property
    def session(self):
        if self.__session is None:
            self.__session = get_session(self.engine)
        return self.__session

    def close_session(self):
        if self.__session is None:
            return
        self.__session.close()
        self.__session = None

    def get_users_for_notification(self):
        data = self.session.query(self.UserOptionsT)\
            .filter_by(option=UserOptions.NOTIFICATION)\
            .filter_by(value=1)\
            .all()
        return [i.user for i in data]

    def find_all_media(self, media_type):
        """
        Находит все данные для поиска по тиапу
        :param type:
        :return:
        """
        data_class = self.Film
        if media_type == MediaType.SERIALS:
            data_class = self.Serial
        data = self.session.query(data_class).filter_by(data_class.status != LockingStatus.ENDED).all()
        return data

    def find_media(self, kinopoisk_id, media_type, season=None):
        """
        Ищет фильм по kinopoisk_id

        :param kinopoisk_id:
        :param media_type:
        :param season:
        :return:
        """
        filter_dict = dict(kinopoisk_id=kinopoisk_id)
        data_class = self.Film
        if media_type == MediaType.SERIALS:
            filter_dict['season'] = season
            data_class = self.Serial
        data = self.session.query(data_class).filter_by(**filter_dict).first()
        self.close_session()
        return data

    def find_media_by_label(self, label, year, media_type, season=None):
        """
        Ищет фильм по стандартным реквизитам

        :param label:
        :param year:
        :param media_type:
        :param season:
        :return:
        """
        filter_dict = dict(label=label, year=year)
        data_class = self.Film
        if media_type == MediaType.SERIALS:
            filter_dict['season'] = season
            data_class = self.Serial
        data = self.session.query(data_class).filter_by(**filter_dict).first()
        self.close_session()
        return data

    def find_user(self, client_id):
        """

        :param client_id:
        :return:
        """
        data = self.session.query(self.User).filter_by(client_id=client_id).first()
        if client_id == int(self.config.TELEGRAMM_BOT_USER_ADMIN):
            if data is None:
                data = self.add_user(client_id)
        # self.close_session()
        return data

    def is_admin(self, client_id):
        return client_id == int(self.config.TELEGRAMM_BOT_USER_ADMIN)

    def update_media_params(self, media_id: int, params: dict, media_type):

        find_dict = {
            'kinopoisk_id': media_id,
            'media_type': media_type,

        }

        if 'season' in params.keys():
            find_dict.update({
                'season': params['season']
            })

        media = self.find_media(**find_dict)

        if media is None:
            raise AttributeError('По kinopoisk_id {} не существует фильма для обновления.'.format(media_id))

        for key in params.keys():
            setattr(media, key, params[key])

        self.session.add(media)
        self.session.commit()
        self.close_session()

    def add_film(self, client_id, kinopoisk_id, label, year, url):
        film = self.Film(kinopoisk_id=kinopoisk_id, label=label, year=year, kinopoisk_url=url)
        user = self.find_user(client_id)
        user.media.append(film)
        self.session.add(film)
        self.session.add(user)
        self.session.commit()
        return film

    def add_serial(self, client_id, kinopoisk_id, label, year, season, url, max_series=0):
        serial = self.Serial(
            kinopoisk_id=kinopoisk_id,
            label=label,
            year=year,
            season=season,
            series=max_series,
            kinopoisk_url=url)
        user = self.find_user(client_id)
        user.media.append(serial)
        self.session.add(serial)
        self.session.add(user)
        self.session.commit()
        return serial

    def add_user(self, clien_id, name='', last_name='', nick_name='', rule=UserRule.USER):
        user = self.User(name=name, last_name=last_name, nick_name=nick_name, client_id=clien_id)
        self.session.add(user)
        self.session.commit()
        return user

    def add_media_to_user_list(self, client_id, kinopoisk_id, media_type, season):
        media = self.find_media(kinopoisk_id, media_type, season)
        user = self.find_user(client_id)
        if media not in user.media:
            user.media.append(media)
        self.session.add(media)
        self.session.add(user)
        self.session.commit()

    def change_user_option(self, clien_id, option_name: UserOptions, value):

        session = self.session

        result = session.query(self.User, self.UserOptionsT).\
                    filter(self.User.id == self.UserOptionsT.user_id).\
                    filter(self.User.client_id == clien_id).\
                    filter(self.UserOptionsT.option == option_name).first()
        if result is None:
            opt = self.UserOptionsT(option=option_name, value=value)
            user = self.session.query(self.User).filter_by(client_id=client_id).first()
            user.options.append(opt)
        else:
            user, opt = result
            opt.value = value
        if user is None:
            raise ValueError('No user with client id {0}'.format(clien_id))

        session.add(opt)
        session.add(user)
        session.commit()
        self.close_session()

if __name__ == '__main__':

    from app import config
    client_id = 123109378
    db = DbManager(config)
