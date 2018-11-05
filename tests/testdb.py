from unittest import TestCase, TestSuite, TextTestRunner, defaultTestLoader
from multiprocessing import Queue
import os
from subprocess import Popen

from src.database import DbManager, MediaData
import src


class TestDB(TestCase):
    def setUp(self):
        self.conf = src.app.config
        self.conf.set_config_file(os.path.abspath('./test_config.ini'))
        self.conf.TEST = True
        self.parser = src.parser.Parser(Queue(), Queue(), self.conf)
        self.component = src.app_enums.ComponentType.MAIN_APP
        self.db = DbManager(self.conf)

        self.client_id = 1
        self.name = 'Александр'
        self.last_name = 'Morozov'
        self.nick = 'rollboll'

        self.test_film = dict(
            kinopoisk_id=1,
            title='Игра',
            year=1988,
            url='ru/kinop',
        )
        self.test_serial = dict(
            kinopoisk_id=1,
            title='Игра',
            year=1988,
            season=1,
            url='ru/kinop',
            max_series=10
        )

        self.serial_kinopoisk_id = 1
        self.serial_title = 'Игра'
        self.serial_year = 1988
        self.serial_season = 1
        self.serial_url = 'ru/kinop'
        self.serial_max_series = 10

    def add_test_user(self, session):
        user = self.db.add_user(self.client_id, self.name, self.last_name, self.nick, session=session)
        return user

    def add_test_film(self, session, **kwargs):
        return self.db.add_film(session=session, **kwargs)

    def add_test_serial(self, session, **kwargs):
        return self.db.add_serial(session=session, **kwargs)

    def test_add_user_to_db(self):
        session = self.db.get_session()
        user = self.add_test_user(session)

        self.assertEqual(user.name, self.name, 'Не корректно определено имя!')
        self.assertEqual(user.last_name, self.last_name, 'Не корректно определена фамилия!')
        self.assertEqual(user.nick_name, self.nick, 'Не корректно определен ник!')
        self.assertEqual(user.client_id, self.client_id, 'Не корректно определен client_id!')

        session.close()

    def test_find_user_in_db(self):
        session = self.db.get_session()
        user = self.add_test_user(session)

        founded_user = self.db.find_user(self.client_id, session)

        self.assertEqual(user.name, founded_user.name,
                         'Не корректно определено имя у найденного пользователя!')
        self.assertEqual(user.last_name, founded_user.last_name,
                         'Не корректно определена фамилия у найденного пользователя!')
        self.assertEqual(user.nick_name, founded_user.nick_name,
                         'Не корректно определен ник у найденного пользователя!')
        self.assertEqual(user.id, founded_user.id,
                         'Не корректно определен id у найденного пользователя!')

    def test_add_serial_data(self):
        session = self.db.get_session()
        user = self.add_test_user(session=session)

        serial = self.add_test_serial(
            session=session,
            client_id=self.client_id,
            kinopoisk_id=self.test_serial['kinopoisk_id'],
            label=self.test_serial['title'],
            year=self.test_serial['year'],
            season=self.test_serial['season'],
            url=self.test_serial['url'],
            max_series=self.test_serial['max_series'])

        self.assertIsInstance(serial, MediaData, 'Возвращен неверный тип значения!')

        self.assertEqual(serial.year, self.test_serial['year'],
                         'Не корректно определено год в новом сериале!')
        self.assertEqual(serial.media_id, self.test_serial['kinopoisk_id'],
                         'Не корректно определен kinopoisk_id в новом сериале!')
        self.assertEqual(serial.title, self.test_serial['title'],
                         'Не корректно определено наименование в новом сериале!')
        self.assertEqual(serial.season, self.test_serial['season'],
                         'Не корректно определено сезон в новом сериале!')
        self.assertEqual(serial.max_series, self.test_serial['max_series'],
                         'Не корректно определено максимальное количество серий в новом сериале!')
        self.assertEqual(serial.kinopoisk_url, self.test_serial['url'],
                         'Не корректно определен url в новом сериале!')
        self.assertEqual(serial.media_type, src.app_enums.MediaType.SERIALS,
                         'Не корректно определен тип медиа в новом сериале!')

    def test_find_serial_data(self):
        session = self.db.get_session()
        user = self.add_test_user(session=session)

        self.add_test_serial(
            session=session,
            client_id=self.client_id,
            kinopoisk_id=self.test_serial['kinopoisk_id'],
            label=self.test_serial['title'],
            year=self.test_serial['year'],
            season=self.test_serial['season'],
            url=self.test_serial['url'],
            max_series=self.test_serial['max_series'])

        serial = self.db.find_media(
            self.test_serial['kinopoisk_id'],
            src.app_enums.MediaType.SERIALS,
            self.test_serial['season'],
            session=session
        )

        self.assertIsInstance(serial, MediaData, 'Возвращен неверный тип значения!')

        self.assertEqual(serial.year, self.test_serial['year'],
                         'Не корректно определено год при поиске сериала!')
        self.assertEqual(serial.media_id, self.test_serial['kinopoisk_id'],
                         'Не корректно определен kinopoisk_id при поиске сериала!')
        self.assertEqual(serial.title, self.test_serial['title'],
                         'Не корректно определено наименование при поиске сериала!')
        self.assertEqual(serial.season, self.test_serial['season'],
                         'Не корректно определено сезон при поиске сериала!')
        self.assertEqual(serial.max_series, self.test_serial['max_series'],
                         'Не корректно определено максимальное количество серий при поиске сериала!')
        self.assertEqual(serial.kinopoisk_url, self.test_serial['url'],
                         'Не корректно определен url при поиске сериала!')
        self.assertEqual(serial.media_type, src.app_enums.MediaType.SERIALS,
                         'Не корректно определен тип медиа при поиске сериала!')

    def test_add_film_data(self):
        session = self.db.get_session()
        user = self.add_test_user(session=session)

        film = self.add_test_film(
            session=session,
            client_id=self.client_id,
            kinopoisk_id=self.test_film['kinopoisk_id'],
            label=self.test_film['title'],
            year=self.test_film['year'],
            url=self.test_film['url'],
        )

        self.assertIsInstance(film, MediaData, 'Возвращен неверный тип значения!')

        self.assertEqual(film.year, self.test_film['year'],
                         'Не корректно определено год в новом фильме!')
        self.assertEqual(film.media_id, self.test_film['kinopoisk_id'],
                         'Не корректно определен kinopoisk_id в новом фильме!')
        self.assertEqual(film.title, self.test_film['title'],
                         'Не корректно определено наименование в новом фильме!')
        self.assertEqual(film.kinopoisk_url, self.test_film['url'],
                         'Не корректно определен url в новом фильме!')
        self.assertEqual(film.media_type, src.app_enums.MediaType.FILMS,
                         'Не корректно определен тип медиа в новом фильме!')

    def test_find_film_data(self):
        session = self.db.get_session()
        user = self.add_test_user(session=session)

        self.add_test_film(
            session=session,
            client_id=self.client_id,
            kinopoisk_id=self.test_film['kinopoisk_id'],
            label=self.test_film['title'],
            year=self.test_film['year'],
            url=self.test_film['url'],
        )

        film = self.db.find_media(
            self.test_film['kinopoisk_id'],
            src.app_enums.MediaType.FILMS,
            session=session
        )

        self.assertIsInstance(film, MediaData, 'Возвращен неверный тип значения!')

        self.assertEqual(film.year, self.test_film['year'],
                         'Не корректно определено год при поиске фильма!')
        self.assertEqual(film.media_id, self.test_film['kinopoisk_id'],
                         'Не корректно определен kinopoisk_id при поиске фильма!')
        self.assertEqual(film.title, self.test_film['title'],
                         'Не корректно определено наименование при поиске фильма!')
        self.assertEqual(film.kinopoisk_url, self.test_film['url'],
                         'Не корректно определен url при поиске фильма!')
        self.assertEqual(film.media_type, src.app_enums.MediaType.FILMS,
                         'Не корректно определен тип медиа при поиске фильма!')

    def tearDown(self):
        db_path = '.test.db'
        if os.path.exists(db_path):
            os.remove(db_path)


def suite():
    return defaultTestLoader.loadTestsFromTestCase(TestDB)


if __name__ == '__main__':

    testRuner = TextTestRunner()
    testRuner.run(suite())
