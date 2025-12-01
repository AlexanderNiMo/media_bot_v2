from unittest import TestCase, TextTestRunner, defaultTestLoader
import os

from tests.utils import TestEnvCreator
from media_bot_v2.database import MediaData
from media_bot_v2.app_enums import MediaType, UserOptions, LockingStatus


class TestDB(TestCase):
    def setUp(self):
        self.test_content = TestEnvCreator()
        self.conf = self.test_content.conf

        self.db = self.test_content.db

        self.anather_client_id = 2
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
            series=10
        )

    def add_test_user(self, client_id, session):
        user = self.db.add_user(client_id, self.name, self.last_name, self.nick, session=session)
        return user

    def add_test_film(self, session, **kwargs):
        return self.db.add_film(session=session, **kwargs)

    def add_test_serial(self, session, **kwargs):
        return self.db.add_serial(session=session, **kwargs)

    def test_add_user_to_db(self):
        session = self.db.get_session()
        user = self.add_test_user(self.client_id, session)

        self.assertEqual(user.name, self.name, 'Не корректно определено имя!')
        self.assertEqual(user.last_name, self.last_name, 'Не корректно определена фамилия!')
        self.assertEqual(user.nick_name, self.nick, 'Не корректно определен ник!')
        self.assertEqual(user.client_id, self.client_id, 'Не корректно определен client_id!')

        session.close()

    def test_find_user_in_db(self):
        session = self.db.get_session()
        user = self.add_test_user(self.client_id, session)

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
        user = self.add_test_user(self.client_id, session=session)

        serial = self.add_test_serial(
            session=session,
            client_id=self.client_id,
            kinopoisk_id=self.test_serial['kinopoisk_id'],
            label=self.test_serial['title'],
            year=self.test_serial['year'],
            season=self.test_serial['season'],
            url=self.test_serial['url'],
            series=self.test_serial['series'])

        self.assertIsInstance(serial, MediaData, 'Возвращен неверный тип значения!')

        self.assertEqual(serial.year, self.test_serial['year'],
                         'Не корректно определено год в новом сериале!')
        self.assertEqual(serial.media_id, self.test_serial['kinopoisk_id'],
                         'Не корректно определен kinopoisk_id в новом сериале!')
        self.assertEqual(serial.title, self.test_serial['title'],
                         'Не корректно определено наименование в новом сериале!')
        self.assertEqual(serial.season, self.test_serial['season'],
                         'Не корректно определено сезон в новом сериале!')
        self.assertEqual(serial.series, self.test_serial['series'],
                         'Не корректно определено максимальное количество серий в новом сериале!')
        self.assertEqual(serial.kinopoisk_url, self.test_serial['url'],
                         'Не корректно определен url в новом сериале!')
        self.assertEqual(serial.media_type, MediaType.SERIALS,
                         'Не корректно определен тип медиа в новом сериале!')
        self.assertEqual(len(user.media.all()), 1, 'Сериал должен был добавиться в список пользователя')

    def test_find_serial_data(self):
        session = self.db.get_session()
        user = self.add_test_user(self.client_id, session=session)

        self.add_test_serial(
            session=session,
            client_id=self.client_id,
            kinopoisk_id=self.test_serial['kinopoisk_id'],
            label=self.test_serial['title'],
            year=self.test_serial['year'],
            season=self.test_serial['season'],
            url=self.test_serial['url'],
            series=self.test_serial['series'])

        serial = self.db.find_media(
            self.test_serial['kinopoisk_id'],
            MediaType.SERIALS,
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
        self.assertEqual(serial.series, self.test_serial['series'],
                         'Не корректно определено максимальное количество серий при поиске сериала!')
        self.assertEqual(serial.kinopoisk_url, self.test_serial['url'],
                         'Не корректно определен url при поиске сериала!')
        self.assertEqual(serial.media_type, MediaType.SERIALS,
                         'Не корректно определен тип медиа при поиске сериала!')
        self.assertEqual(len(user.media.all()), 1, 'Сериал должен был добавиться в список пользователя')

    def test_add_film_data(self):
        session = self.db.get_session()
        user = self.add_test_user(self.client_id, session=session)

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
        self.assertEqual(film.media_type, MediaType.FILMS,
                         'Не корректно определен тип медиа в новом фильме!')
        self.assertEqual(len(user.media.all()), 1, 'Фильм должен был добавиться в список пользователя')

    def test_find_film_data(self):
        session = self.db.get_session()
        user = self.add_test_user(self.client_id, session=session)

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
            MediaType.FILMS,
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
        self.assertEqual(len(user.media.all()), 1, 'Фильм должен был добавиться в список пользователя')
        self.assertEqual(film.media_type, MediaType.FILMS,
                         'Не корректно определен тип медиа при поиске фильма!')

    def test_update_media(self):
        session = self.db.get_session()
        user = self.add_test_user(self.client_id, session=session)
        self.add_test_film(
            session=session,
            client_id=self.client_id,
            kinopoisk_id=self.test_film['kinopoisk_id'],
            label=self.test_film['title'],
            year=self.test_film['year'],
            url=self.test_film['url'],
        )

        self.db.update_media_params(
            media_id=self.test_film['kinopoisk_id'],
            upd_data={
                'label': '',
                'year': 1988,
                'kinopoisk_url': 'rutr',
                'status': LockingStatus.ENDED,
                'torrent_id': '2',
                'kinopoisk_id': 2
            },
            media_type=MediaType.FILMS,
            session=session)

        film = self.db.find_media(
            2,
            MediaType.FILMS,
            session=session
        )

        self.assertEqual(film.title, '', 'Не изменилось значение нименования.')
        self.assertEqual(film.year, 1988, 'Не изменилось значение года.')
        self.assertEqual(film.kinopoisk_url, 'rutr', 'Не изменилось значение kinopoisk_url.')
        self.assertEqual(film.status, LockingStatus.ENDED, 'Не изменилось значение статуса.')
        self.assertEqual(film.torrent_id, '2', 'Не изменилось значение torrent_id.')
        self.assertEqual(film.media_id, 2, 'Не изменилось значение media_id.')

        self.add_test_serial(
            session=session,
            client_id=self.client_id,
            kinopoisk_id=self.test_serial['kinopoisk_id'],
            label=self.test_serial['title'],
            year=self.test_serial['year'],
            season=self.test_serial['season'],
            url=self.test_serial['url'],
            series=self.test_serial['series'])

        current_series = 10
        self.db.update_media_params(
            media_id=self.test_serial['kinopoisk_id'],
            upd_data={
                'current_series': current_series
            },
            season=self.test_serial['season'],
            media_type=MediaType.SERIALS,
            session=session)

        serial = self.db.find_media(
            kinopoisk_id=self.test_serial['kinopoisk_id'],
            media_type=MediaType.SERIALS,
            season=self.test_serial['season'],
            session=session
        )

        self.assertTrue(serial.current_series == current_series, 'Не изменились данные сериала.')



    def test_user_options(self):
        session = self.db.get_session()
        self.add_test_user(self.client_id, session=session)

        self.db.change_user_option(self.client_id, UserOptions.NOTIFICATION, session=session)
        user = self.db.find_user(self.client_id, session=session)

        self.assertTrue(len(user.options) == 1,
                        'Не верное колличество настроек у пользователя')
        self.assertTrue(user.options[0].option.value == UserOptions.NOTIFICATION.value,
                        'Не верно установлен тип опции.')
        self.assertTrue(user.options[0].value == 1,
                        'Не верно установлено значение опции.')

        self.db.change_user_option(self.client_id, UserOptions.NOTIFICATION, session=session)
        self.assertTrue(user.options[0].value == 0,
                        'Не верно установлено значение опции после изменения.')

    def test_add_media_to_user(self):
        session = self.db.get_session()
        self.add_test_user(self.client_id, session=session)
        test_user = self.add_test_user(self.anather_client_id, session=session)

        self.add_test_film(
            session=session,
            client_id=self.client_id,
            kinopoisk_id=self.test_film['kinopoisk_id'],
            label=self.test_film['title'],
            year=self.test_film['year'],
            url=self.test_film['url'],
        )

        self.db.add_media_to_user_list(
            self.anather_client_id,
            self.test_film['kinopoisk_id'],
            MediaType.FILMS,
            session=session
        )

        self.assertTrue(len(test_user.media.all()) == 1, 'Новый фильм не добавился в список пользователя')

    def test_get_users_by_media_id(self):
        session = self.db.get_session()

        admin = self.add_test_user(self.client_id, session=session)
        self.db.change_user_option(self.client_id, UserOptions.NOTIFICATION, 1, session=session)

        test_user = self.add_test_user(self.anather_client_id, session=session)
        self.db.change_user_option(self.anather_client_id, UserOptions.NOTIFICATION, 1, session=session)

        serial = self.add_test_serial(
            session=session,
            client_id=self.client_id,
            kinopoisk_id=self.test_serial['kinopoisk_id'],
            label=self.test_serial['title'],
            year=self.test_serial['year'],
            season=self.test_serial['season'],
            url=self.test_serial['url'],
            series=self.test_serial['series'])

        users = self.db.get_users_for_notification(media_id=1, media_type=MediaType.SERIALS, season=1, session=session)

        self.assertIn(admin, users, 'Не найден пользователь, который должен быть в выборке')
        self.assertIn(test_user, users, 'Не найден пользователь, который должен быть в выборке')

    def tearDown(self):
        self.test_content.clear_test_db()


def suite():
    return defaultTestLoader.loadTestsFromTestCase(TestDB)


if __name__ == '__main__':

    testRuner = TextTestRunner()
    testRuner.run(suite())
