from typing import List, Optional, Union

from media_bot_v2.app_enums import LockingStatus, MediaType, UserOptions, UserRule
from media_bot_v2.config import DbConfig

from .alch_db import (
    OperationalError,
    StaticPool,
    User,
    create_db,
    get_session,
    init_db,
)


class DbManager:
    from media_bot_v2.database.alch_db.model import (
        Film,
        MediaData,
        Serial,
        User,
        UserOptionsT,
    )

    def __init__(self, config: DbConfig):
        self.config = config
        self.__enj = None
        self.__session = None

    def __get_connection_str(self):
        return self.config.dns

    @property
    def engine(self):
        args = {}
        connection_str = self.__get_connection_str()
        if "sqlite" not in self.config.dns:
            args["poolclass"] = StaticPool
        try:
            enj = init_db(connection_str, **args)
        except OperationalError:
            create_db(self.__get_connection_str(), self.config.db_name)
            enj = init_db(connection_str, echo=True, **args)
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

    def get_user(self, user_id: str, session=None) -> User:
        close_session = False
        if session is None:
            session = self.get_session()
            close_session = True
        user = session.get(User, user_id)

        if close_session:
            self.close_session()
        return user

    def get_users_for_notification(
        self, media_id, media_type, season=0, session=None
    ) -> list:
        if session is None:
            session = self.session
        users = []

        if media_type.value == MediaType.SERIALS:
            media_users = (
                session.query(self.User)
                .join(self.User.media)
                .filter(self.Serial.kinopoisk_id == media_id)
                .filter(self.Serial.season == season)
                .all()
            )
        else:
            media_users = (
                session.query(self.User)
                .join(self.User.media)
                .filter(self.Film.kinopoisk_id == media_id)
                .all()
            )

        for i in media_users:
            users.append(i)

        data = (
            session.query(self.UserOptionsT)
            .filter_by(option=UserOptions.NOTIFICATION)
            .filter_by(value=1)
            .all()
        )
        users += [i.user for i in data]
        return users

    @staticmethod
    def construct_media_by_orm_object(elem: Union[Film, Serial]) -> Optional[MediaData]:
        if elem is None:
            return None
        media_type = MediaType.FILMS
        try:
            season = elem.season
            current_series = elem.current_series
            media_type = MediaType.SERIALS
        except AttributeError:
            season = ""
            current_series = 0

        try:
            series = elem.series
        except AttributeError:
            series = 0

        data_dict = {
            "media_id": elem.kinopoisk_id,
            "title": elem.label,
            "year": elem.year,
            "download_url": elem.download_url,
            "torrent_tracker": elem.torrent_tracker,
            "torrent_id": elem.torrent_id,
            "theam_id": elem.theam_id,
            "kinopoisk_url": elem.kinopoisk_url,
            "media_type": media_type,
            "series": series,
            "season": season,
            "status": elem.status,
            "current_series": current_series,
            "img_link": elem.img_link,
        }
        return MediaData(**data_dict)

    def find_all_media(self, media_type, session=None) -> List[MediaData]:
        result = []
        data = self._find_all_media(media_type, session)
        for elem in data:
            result.append(self.construct_media_by_orm_object(elem))
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
        data = (
            session.query(data_class)
            .filter(data_class.status != LockingStatus.ENDED)
            .all()
        )
        return data

    def find_media(
        self, kinopoisk_id, media_type, season=None, session=None
    ) -> MediaData:
        data = self._find_media(kinopoisk_id, media_type, season, session)
        return self.construct_media_by_orm_object(data)

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
            filter_dict["season"] = season
            data_class = self.Serial
        data = session.query(data_class).filter_by(**filter_dict).first()
        return data

    def find_media_by_label(
        self, label, year, media_type, season=None, session=None
    ) -> MediaData:
        data = self._find_media_by_label(label, year, media_type, season, session)
        return self.construct_media_by_orm_object(data)

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
            filter_dict["season"] = season
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
        if self.is_admin(client_id):
            if data is None:
                data = self.add_user(client_id, session=session)
        return data

    def get_all_users(self, session: session = None) -> list:
        """
        Return all users id in db
        :param session:
        """
        if session is None:
            session = self.session
        data = session.query(self.User).all()
        return data

    def is_admin(self, client_id):
        return client_id == int(self.config.admin_id)

    def update_media_params(
        self,
        media_id: int,
        upd_data: dict,
        media_type,
        season: int = 0,
        session=None,
        *args,
        **kwargs,
    ):
        close = False
        if session is None:
            close = True
            session = self.session
        find_dict = {
            "kinopoisk_id": media_id,
            "media_type": media_type,
            "session": session,
        }

        if season != 0:
            find_dict.update({"season": season})

        media = self._find_media(**find_dict)

        if media is None:
            raise AttributeError(
                "По kinopoisk_id {} не существует медиа для обновления.".format(
                    media_id
                )
            )

        for key in upd_data.keys():
            setattr(media, key, upd_data[key])

        session.add(media)
        session.commit()
        if close:
            session.close()

    def add_film(
        self, client_id, kinopoisk_id, label, year, url, session=None, cover_url=""
    ) -> MediaData:
        if session is None:
            session = self.session
        film = self.Film(
            kinopoisk_id=kinopoisk_id,
            label=label,
            year=year,
            kinopoisk_url=url,
            img_link=cover_url,
        )
        user = self.find_user(client_id, session=session)
        user.media.append(film)
        if user is None:
            raise EnvironmentError(f"No user by id {client_id}")
        session.add(film)
        session.add(user)
        session.commit()
        res_film = self.construct_media_by_orm_object(film)
        return res_film

    def add_serial(
        self,
        client_id,
        kinopoisk_id,
        label,
        year,
        season,
        url,
        series=0,
        session=None,
        cover_url="",
    ) -> MediaData:
        if session is None:
            session = self.session
        serial = self.Serial(
            kinopoisk_id=kinopoisk_id,
            label=label,
            year=year,
            season=season,
            series=series,
            kinopoisk_url=url,
            img_link=cover_url,
        )
        user = self.find_user(client_id, session=session)
        if user is None:
            raise EnvironmentError(f"No user by id {client_id}")
        user.media.append(serial)
        session.add(serial)
        session.add(user)
        session.commit()
        res_serial = self.construct_media_by_orm_object(serial)
        return res_serial

    def add_user(self, client_id, name="", last_name="", nick_name="", session=None):
        if session is None:
            session = self.session
        user = self.User(
            name=name, last_name=last_name, nick_name=nick_name, client_id=client_id
        )
        session.add(user)
        session.commit()
        return user

    def add_media_to_user_list(
        self, client_id, kinopoisk_id, media_type, season=0, session=None
    ):
        if session is None:
            session = self.session
        media = self._find_media(kinopoisk_id, media_type, season, session=session)
        user = self.find_user(client_id, session=session)
        if media not in user.media:
            user.media.append(media)
        session.add(media)
        session.add(user)
        session.commit()

    def change_user_option(
        self, client_id, option_name: UserOptions, value=0, session=None
    ):
        result = self._get_user_options(client_id, option_name, session)
        if result is None:
            opt = self.UserOptionsT(option=option_name, value=1)
            user = self.find_user(client_id, session)
            user.options.append(opt)
        else:
            user, opt = result
            opt.value = value if value != 0 else not opt.value
        if user is None:
            raise ValueError("No user with client id {0}".format(client_id))
        new_value = opt.value
        session.add(opt)
        session.add(user)
        session.commit()
        return new_value

    def _get_user_options(self, client_id, option_name, session):
        if session is None:
            session = self.session
        result = (
            session.query(self.User, self.UserOptionsT)
            .filter(self.User.id == self.UserOptionsT.user_id)
            .filter(self.User.client_id == client_id)
            .filter(self.UserOptionsT.option == option_name)
            .first()
        )
        return result

    def get_user_option(self, client_id, option_name: UserOptions, session=None):
        result = self._get_user_options(client_id, option_name, session)
        if result is None:
            return 0
        else:
            user, opt = result
            return opt.value

    def delete_media(self, kinopoisk_id, season, media_type: MediaType, session=None):
        data = self._find_media(
            kinopoisk_id=kinopoisk_id,
            media_type=media_type,
            season=season,
            session=session,
        )
        session.delete(data)
        session.commit()
        self.close_session()


class MediaData:
    """
    Store media data for return from db adapter

    """

    def __init__(
        self,
        media_id,
        title,
        year,
        download_url,
        torrent_tracker,
        theam_id,
        kinopoisk_url,
        torrent_id,
        media_type,
        status,
        season="",
        series=0,
        current_series=0,
        img_link="",
    ):
        m_id = 0
        try:
            m_id = int(media_id)
        except Exception:
            m_id = int(media_id[2:])
        self.media_id = m_id
        self.title = title
        self.download_url = download_url
        self.torrent_tracker = torrent_tracker
        self.theam_id = theam_id
        self.season = season
        self.year = year
        self.kinopoisk_url = kinopoisk_url
        self.series = series
        self.current_series = current_series
        self.torrent_id = torrent_id
        self.media_type = media_type
        self.status = status
        self.img_link = img_link

    @property
    def kinopoisk_id(self):
        return self.media_id


if __name__ == "__main__":
    pass
