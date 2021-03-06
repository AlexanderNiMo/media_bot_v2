import unittest
import src
import os


from tests.utils import TestEnvCreator


class TestParser(unittest.TestCase):

    def setUp(self):
        self.test_content = TestEnvCreator()
        self.conf = self.test_content.conf

        self.parser = self.test_content.parser
        self.component = src.app_enums.ComponentType.MAIN_APP
        self.db = self.test_content.db

    def get_message(self):
        return src.mediator.MediatorActionMessage(
            src.app_enums.ComponentType.PARSER,
            src.app_enums.ActionType.PARSE,
            self.component
        )

    def get_target_message(self, returned_data):
        target_message = None
        for message in returned_data:
            if message.action == src.app_enums.ActionType.RETURNED_DATA and message.component == self.component:
                target_message = message
        self.assertIsNotNone(target_message, 'В резульата не обнаруженно сообщение с данными возврата')
        return target_message

    def check_parser_answer(self, returned_data):
        self.assertIsInstance(returned_data, list, 'Парсер вернул результат неожиданнго типа!')
        self.assertNotEqual(len(returned_data), 0, 'Парсер вернул пустой результат!')

    def check_target_message(self, target_message, needed_data):
        returned_keys = target_message.data.data.keys()
        self.assertTrue(all(map((lambda x: x in returned_keys), needed_data)), 'Не все данные полученны!')

    def parse_data(self, needed_data, data_dict):
        msg = self.get_message()

        msg.data = src.mediator.ParserData(
            data_dict,
            self.conf.TELEGRAMM_BOT_USER_ADMIN,
            data_needed=needed_data
        )
        returned_data = self.parser.parse(msg)

        self.check_parser_answer(returned_data)
        target_message = self.get_target_message(returned_data)
        self.check_target_message(target_message, needed_data)
        return target_message

    def configure_db_data(self):
        client_id = self.conf.TELEGRAMM_BOT_USER_ADMIN
        session = self.db.get_session()
        user = self.db.add_user(client_id, session=session)
        serial = self.db.add_serial(client_id, 685246, 'Рик и Морти', 2013, 1, 'http://www.kinopoisk.ru/film/685246/',
                                    session=session)
        film = self.db.add_film(
            client_id,
            689,
            'Гарри Поттер и философский камень',
            2001,
            'http://www.kinopoisk.ru/film/689/',
            session=session
        )
        session.close()

    def test_get_data_text(self):

        needed_data = ['year', 'query', 'season']
        target_message = self.parse_data(needed_data, {'query': 'Игра престолов сезон 1 2011'})

        self.assertEqual(target_message.data.data['year'], 2011, 'Год найден не верно!')
        self.assertEqual(target_message.data.data['query'], 'ИГРА ПРЕСТОЛОВ СЕЗОН 1', 'Запрос определен не верно!')
        self.assertEqual(target_message.data.data['season'], 1, 'Сезон определен не верно!')

    def test_get_data_kinopoisk(self):

        needed_data = ['title', 'kinopoisk_id', 'kinopoisk_url']
        target_message = self.parse_data(
            needed_data,
            {
                'media_type': src.app_enums.MediaType.SERIALS,
                'query': 'Рик и Морти'.upper(),
                'season': 1,
                'year': 2013
            }
        )

        self.assertEqual(target_message.data.data['title'], 'Рик и Морти', 'Наименвоание определено не верно!')
        self.assertEqual(target_message.data.data['kinopoisk_id'], '2861424', 'Id определен не верно!')
        self.assertEqual(target_message.data.data['kinopoisk_url'],
                         'https://www.imdb.com/title/tt2861424/',
                         'не верено определен url')
        self.assertEqual(target_message.data.data['cover_url'],
                         'https://m.media-amazon.com/images/M/MV5BZjRjOTFkOTktZWUzMi00YzMyLThkMmYtM'
                         'jEwNmQyNzliYTNmXkEyXkFqcGdeQXVyNzQ1ODk3MTQ@._V1_UX32_CR0,0,32,44_AL_.jpg',
                         'не верено определен url изображения')

        target_message = self.parse_data(
            needed_data,
            {
                'media_type': src.app_enums.MediaType.FILMS,
                'query': 'Гарри Поттер и философский камень'.upper(),
                'year': 2001
            }
        )

        self.assertEqual(target_message.data.data['title'], 'Гарри Поттер и философский камень',
                         'Наименвоание определено не верно!')
        self.assertEqual(target_message.data.data['kinopoisk_id'], '0241527', 'Id определен не верно!')
        self.assertEqual(target_message.data.data['kinopoisk_url'],
                         'https://www.imdb.com/title/tt0241527/',
                         'не верено определен url')

        target_message = self.parse_data(
            needed_data,
            {
                'media_type': src.app_enums.MediaType.SERIALS,
                'query': 'Полуночная проповедь'.upper(),
                'season': 1,
                'year': 2020
            }
        )

        target_message = self.parse_data(
            needed_data,
            {
                'media_type': src.app_enums.MediaType.SERIALS,
                'query': 'WANDAVISION'.upper(),
                'season': 1,
                'year': 2021
            }
        )


    def test_get_data_telegramm(self):
        needed_data = ['nick', 'name', 'last_name']
        target_message = self.parse_data(
            needed_data,
            {
                'client_id': self.conf.TELEGRAMM_BOT_USER_ADMIN
            }
        )

        self.assertEqual(target_message.data.data['nick'], 'rollboll', 'Ник определено не верно!')
        self.assertEqual(target_message.data.data['name'], 'Александр', 'Имя определено не верно!')
        self.assertEqual(target_message.data.data['last_name'], 'Морозов', 'Фамилия определена не верно')

    def test_get_data_plex(self):
        needed_data = ['media_in_plex']
        target_message = self.parse_data(
                    needed_data,
                    {
                        'media_type': src.app_enums.MediaType.FILMS,
                        'title': 'Под покровом ночи',
                        'year': 2007
                    }
        )

        self.assertFalse(target_message.data.data['media_in_plex'], 'Фильм должен отсутствовать в plex!')

        target_message = self.parse_data(
                    needed_data,
                    {
                        'media_type': src.app_enums.MediaType.SERIALS,
                        'title': 'Игра престолов',
                        'season': 1,
                        'year': 2010
                    }
        )

        self.assertTrue(target_message.data.data['media_in_plex'], 'Сериал должен присутствовать в plex!')

    def test_get_data_database(self):

        self.configure_db_data()
        needed_data = ['media_in_db']
        target_message = self.parse_data(
                    needed_data,
                    {
                        'media_type': src.app_enums.MediaType.SERIALS,
                        'kinopoisk_id': 685246,
                        'year': 2013,
                        'season': 1
                    }
        )

        self.assertTrue(target_message.data.data['media_in_db'], 'Сериал должен присутствовать в db!')

        target_message = self.parse_data(
                    needed_data,
                    {
                        'media_type': src.app_enums.MediaType.FILMS,
                        'kinopoisk_id': 685246,
                        'year': 2013
                    }
        )

        self.assertFalse(target_message.data.data['media_in_db'], 'Фильм должен отсутствовать в db!')

        target_message = self.parse_data(
                    needed_data,
                    {
                        'media_type': src.app_enums.MediaType.FILMS,
                        'kinopoisk_id': 689,
                        'year': 2001
                    }
        )

        self.assertTrue(target_message.data.data['media_in_db'], 'Фильм должен присутствовать в db!')

    def tearDown(self):
        self.test_content.clear_test_db()
        self.test_content = None
        self.parser = None
        self.component = None
        self.db = None


def test_imdb():
    from imdb import IMDb

    # create an instance of the IMDb class
    ia = IMDb()

    # get a movie and print its director(s)
    the_matrix = ia.search_movie('Полуночная проповедь')
    for director in the_matrix['directors']:
        print(director['name'])

    # show all information that are currently available for a movie
    print(sorted(the_matrix.keys()))

    # show all information sets that can be fetched for a movie
    print(ia.get_movie_infoset())

    # update a Movie object with more information
    ia.update(the_matrix, ['technical'])
    # show which keys were added by the information set
    print(the_matrix.infoset2keys['technical'])
    # print one of the new keys
    print(the_matrix.get('tech'))


def suite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(TestParser)


if __name__ == '__main__':

    runner = unittest.TextTestRunner()
    runner.run(suite())
