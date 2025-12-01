import pathlib
from unittest import TestCase, TextTestRunner, defaultTestLoader
import os
from tests.utils import compare_dicts, TestEnvCreator

from media_bot_v2.clients.protocols.bot_protocol import BotCache, BotCommandParser
from media_bot_v2.mediator.mediator_types.mediator_message import MediatorActionMessage, CommandData
from media_bot_v2.app_enums import MediaType, TorrentType, UserOptions


class TestCommandParser(TestCase):
    def setUp(self):
        self.commandParser = BotCommandParser
        self.commands = [comm_text for comm_text in BotCommandParser.get_commands()]
        self.env = TestEnvCreator()
        self.client_id = self.env.admin_id

    def test_get_commands(self):
        for command in self.commands:
            message = self.commandParser.get_command_message(command, self.get_test_data(command), self.client_id)

            self.assertIsInstance(message, MediatorActionMessage, 'Полученно сообщение неизвестного типа.')
            self.assertIsInstance(message.data, CommandData, 'В сообщении содержаться данные неожиданного типа!')

    def get_test_data(self, command):
        if command == '/film':
            res = {'text': 'Игра 1997'}
        elif command == '/auth':
            res = {
                'client_id': self.client_id,
                'name': '',
                'last_name': '',
                'nick': ''
            }
        elif command == '/notify':
            res = {'option': UserOptions.NOTIFICATION}
        elif command == '/serial':
            res = {'text': 'Игра престолов 2011 сезон 1'}
        elif command == '/send_messages_to_all':
            res = {}
        else:
            raise Exception(f'Неизвестный идентификатор команды! {command}')

        return res

    def tearDown(self):
        pass


class TestClientCache(TestCase):

    def setUp(self):
        self.file_db = './cache.db'
        db_file = pathlib.Path(self.file_db)
        if db_file.exists():
            os.remove(db_file)
        db_file.touch(exist_ok=True)

        self.cache = BotCache(self.file_db)
        self.key = None
        self.data = {
            'media_id': 12345678,
            'media_type': MediaType.SERIALS,
            'action': 'kinopoisk',
            'download_url': 'https://',
            'theam_id': 'https://',
            'torrent_tracker': TorrentType.RUTRACKER,
        }

    def testSaveLoadCache(self):
        self.key = self.cache.set(self.data)
        data = self.cache.get(self.key)
        self.assertTrue(compare_dicts(data, self.data), 'Сохраненное значени ене равно сохраняемому!')

    def tearDown(self):
        self.cache = None
        os.remove(self.file_db)


def suite():
    return defaultTestLoader.loadTestsFromTestCase((TestClientCache, TestCommandParser))


if __name__ == '__main__':

    testRuner = TextTestRunner()
    testRuner.run(suite())
