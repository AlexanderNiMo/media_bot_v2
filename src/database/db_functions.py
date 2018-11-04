from src.database.alch_db import get_session, init_db, OperationalError, create_db
from src.app_enums import UserRule, UserOptions, MediaType, LockingStatus


class DbManager:
    from src.database.alch_db.model import User, MediaData, Serial, Film, UserOptionsT

    def __init__(self, config):

        self.config = config
        self.__enj = None
        self.__session = None
        self.test = config.TEST

    def __get_connection_str(self):
        if self.test:
            return 'sqlite://'
        else:
            return 'mysql+mysqldb://{0}:{1}@{2}:{3}'.format(
                self.config.DATABASE_USER,
                self.config.DATABASE_PASSWORD,
                self.config.DATABASE_HOST,
                self.config.DATABASE_PORT
            )

    @property
    def engine(self):
        if not self.test:
            connection_str = '{0}/{1}?charset=utf8'.format(self.__get_connection_str(), self.config.DATABASE_NAME)
        else:
            connection_str = self.__get_connection_str()
        try:
            enj = init_db(connection_str)
        except OperationalError:
            create_db(self.__get_connection_str(), self.config.DATABASE_NAME)
            enj = init_db(connection_str)
        return enj

    @property
    def session(self):
        if self.__session is None:
            self.__session = get_session(self.engine)
        return self.__session

    def get_session(self):
        return get_session(self.engine)

    def close_session(self):
        if self.__session is None:
            return
        self.__session.close()
        self.__session = None

    def get_users_for_notification(self, media_id, session=None):
        if session is None:
            session = self.session
        users = []
        media_users = session.query(self.User).join(self.User.media). \
            filter(self.MediaData.kinopoisk_id == media_id).all()
        for i in media_users:
            users.append(i)

        data = session.query(self.UserOptionsT) \
            .filter_by(option=UserOptions.NOTIFICATION) \
            .filter_by(value=1) \
            .all()
        users += [i.user for i in data]
        return users

    @staticmethod
    def construct_media_by_ohm_object(elem):
        if elem is None:
            return None
        media_type = MediaType.FILMS
        try:
            season = elem.season
            media_type = MediaType.SERIALS
        except AttributeError:
            season = ''

        try:
            max_series = elem.series
        except AttributeError:
            max_series = 0

        data_dict = {
            'media_id': elem.kinopoisk_id,
            'title': elem.label,
            'year': elem.year,
            'download_url': elem.download_url,
            'torrent_tracker': elem.torrent_tracker,
            'torrent_id': elem.torrent_id,
            'theam_id': elem.theam_id,
            'kinopoisk_url': elem.kinopoisk_url,
            'media_type': media_type,
            'max_series': max_series,
            'season': season,
            'status': elem.status,
        }
        return MediaData(**data_dict)

    def find_all_media(self, media_type, session=None):
        result = []
        data = self._find_all_media(media_type, session)
        for elem in data:
            result.append(self.construct_media_by_ohm_object(elem))
        return result

    def _find_all_media(self, media_type, session=None):
        """
        Находит все данные для поиска по тиапу
        :param media_type:
        :param session:
        :return:
        """
        if session is None:
            session = self.session
        data_class = self.Film
        if media_type == MediaType.SERIALS:
            data_class = self.Serial
        elif media_type == MediaType.BASE_MEDIA:
            data_class = self.MediaData
        data = session.query(data_class).filter(data_class.status != LockingStatus.ENDED).all()
        return data

    def find_media(self, kinopoisk_id, media_type, season=None, session=None):
        data = self._find_media(kinopoisk_id, media_type, season, session)
        return self.construct_media_by_ohm_object(data)

    def _find_media(self, kinopoisk_id, media_type, season=None, session=None):
        """
        Ищет фильм по kinopoisk_id

        :param kinopoisk_id:
        :param media_type:
        :param season:
        :return:
        """
        if session is None:
            session = self.session
        filter_dict = dict(kinopoisk_id=kinopoisk_id)
        data_class = self.Film
        if media_type == MediaType.SERIALS:
            filter_dict['season'] = season
            data_class = self.Serial
        data = session.query(data_class).filter_by(**filter_dict).first()
        self.close_session()
        return data

    def find_media_by_label(self, label, year, media_type, season=None, session=None):
        data = self._find_media_by_label(label, year, media_type, season, session)
        return self.construct_media_by_ohm_object(data)

    def _find_media_by_label(self, label, year, media_type, season=None, session=None):
        """
        Ищет фильм по стандартным реквизитам

        :param label:
        :param year:
        :param media_type:
        :param season:
        :return:
        """
        if session is None:
            session = self.session
        filter_dict = dict(label=label, year=year)
        data_class = self.Film
        if media_type == MediaType.SERIALS:
            filter_dict['season'] = season
            data_class = self.Serial
        data = session.query(data_class).filter_by(**filter_dict).first()
        self.close_session()
        return data

    def find_user(self, client_id, session=None):
        """

        :param client_id:
        :param session:
        :return:
        """
        if session is None:
            session = self.session
        data = session.query(self.User).filter_by(client_id=client_id).first()
        if client_id == int(self.config.TELEGRAMM_BOT_USER_ADMIN):
            if data is None:
                data = self.add_user(client_id, session)
        return data

    def is_admin(self, client_id):
        return client_id == int(self.config.TELEGRAMM_BOT_USER_ADMIN)

    def update_media_params(self, media_id: int, params: dict, media_type, session=None):
        if session is None:
            session = self.session
        find_dict = {
            'kinopoisk_id': media_id,
            'media_type': media_type,
            'session': session,
        }

        if 'season' in params.keys():
            find_dict.update({
                'season': params['season']
            })

        media = self._find_media(**find_dict)

        if media is None:
            raise AttributeError('По kinopoisk_id {} не существует фильма для обновления.'.format(media_id))

        for key in params.keys():
            setattr(media, key, params[key])

        session.add(media)
        session.commit()
        self.close_session()

    def add_film(self, client_id, kinopoisk_id, label, year, url, session=None):
        if session is None:
            session = self.session
        film = self.Film(kinopoisk_id=kinopoisk_id, label=label, year=year, kinopoisk_url=url)
        user = self.find_user(client_id, session=session)
        user.media.append(film)
        session.add(film)
        session.add(user)
        session.commit()
        return film

    def add_serial(self, client_id, kinopoisk_id, label, year, season, url, max_series=0, session=None):
        if session is None:
            session = self.session
        serial = self.Serial(
            kinopoisk_id=kinopoisk_id,
            label=label,
            year=year,
            season=season,
            series=max_series,
            kinopoisk_url=url)
        user = self.find_user(client_id, session=session)
        user.media.append(serial)
        session.add(serial)
        session.add(user)
        session.commit()
        return serial

    def add_user(self, clien_id, name='', last_name='', nick_name='', rule=UserRule.USER, session=None):
        if session is None:
            session = self.session
        user = self.User(name=name, last_name=last_name, nick_name=nick_name, client_id=clien_id)
        session.add(user)
        session.commit()
        return user

    def add_media_to_user_list(self, client_id, kinopoisk_id, media_type, season, session=None):
        if session is None:
            session = self.session
        media = self._find_media(kinopoisk_id, media_type, season, session=session)
        user = self.find_user(client_id, session=session)
        if media not in user.media:
            user.media.append(media)
        session.add(media)
        session.add(user)
        session.commit()

    def change_user_option(self, client_id, option_name: UserOptions, value=0, session=None):
        if session is None:
            session = self.session
        result = session.query(self.User, self.UserOptionsT). \
            filter(self.User.id == self.UserOptionsT.user_id). \
            filter(self.User.client_id == client_id). \
            filter(self.UserOptionsT.option == option_name).first()
        if result is None:
            opt = self.UserOptionsT(option=option_name, value=value)
            user = self.find_user(client_id, session)
            user.options.append(opt)
        else:
            user, opt = result
            opt.value = value if value != 0 else not opt.value
        if user is None:
            raise ValueError('No user with client id {0}'.format(client_id))
        new_value = opt.value
        session.add(opt)
        session.add(user)
        session.commit()
        return new_value


class MediaData:
    """
    Store media data for return from db adapter

    """

    def __init__(self, media_id, title, year,
                 download_url, torrent_tracker,
                 theam_id, kinopoisk_url, torrent_id,
                 media_type, status, season='', max_series=0):
        self.media_id = media_id
        self.title = title
        self.download_url = download_url
        self.torrent_tracker = torrent_tracker
        self.theam_id = theam_id
        self.season = season
        self.year = year
        self.kinopoisk_url = kinopoisk_url
        self.max_series = max_series
        self.torrent_id = torrent_id
        self.media_type = media_type
        self.status = status


if __name__ == '__main__':
    pass
