import unittest
import src
import multiprocessing


class TestParser(unittest.TestCase):

    def setUp(self):
        self.parser = src.parser.Parser(multiprocessing.Queue(), multiprocessing.Queue(), src.app.config)
        self.component = src.app_enums.ComponentType.MAIN_APP

    def test_get_data_text(self):

        needed_data = ['year', 'query', 'season']

        msg = src.mediator.MediatorActionMessage(src.app_enums.ComponentType.PARSER,
                                                 src.app_enums.ActionType.PARSE,
                                                 self.component
                                                 )
        msg.data = src.mediator.ParserData(
            {'query': 'Игра престолов сезон 1 2011'},
            src.app.config.TELEGRAMM_BOT_USER_ADMIN,
            data_needed=needed_data
        )
        returned_data = self.parser.parse(msg)

        self.assertIsInstance(returned_data, list, 'Парсер вернул результат неожиданнго типа!')
        self.assertNotEqual(len(returned_data), 0, 'Парсер вернул пустой результат!')

        target_message = None
        for message in returned_data:
            if message.action == src.app_enums.ActionType.RETURNED_DATA and message.component == self.component:
                target_message = message
        self.assertIsNotNone(target_message, 'В резульата не обнаруженно сообщение с данными возврата')

        returned_keys = target_message.data.data.keys()

        self.assertTrue(all(map((lambda x: x in returned_keys), needed_data)), 'Не все данные полученны!')

        self.assertEqual(target_message.data.data['year'], 2011, 'Год найден не верно!')
        self.assertEqual(target_message.data.data['query'], 'ИГРА ПРЕСТОЛОВ СЕЗОН 1', 'Запрос определен не верно!')
        self.assertEqual(target_message.data.data['season'], 1, 'Сезон определен не верно!')


def suite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(TestParser)


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
