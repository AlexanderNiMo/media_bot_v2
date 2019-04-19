from unittest import TestCase, TextTestRunner, defaultTestLoader

from src import app_enums
from tests.utils import TestEnvCreator
from src.mediator import command_message


class TestCommandHandler(TestCase):
    def setUp(self):

        self.test_context = TestEnvCreator()
        self.test_context.construct_test_db()
        self.parser = self.test_context.parser

        self.client_id = 1

    @property
    def test_handler(self):
        return self.test_context.command_handler

    @property
    def mediator(self):
        return self.test_context.mediator

    @property
    def db(self):
        return self.test_context.db

    def test_command_change_notification(self):

        notif_option = app_enums.UserOptions.NOTIFICATION

        command_data = {
            'option': notif_option
        }

        command = app_enums.ClientCommands.EDIT_SETTINGS
        command_msg = command_message(app_enums.ComponentType.MAIN_APP, command, command_data, self.client_id)
        self.test_handler.handle_message(command_msg)

        val = self.db.get_user_option(self.client_id, notif_option)
        self.assertTrue(val == 1, 'Статус не изменился')

    def test_command_send_messages(self):
        media_id = '12345678'
        media_title = 'Тест 1'

        self.test_context.add_test_film(
            self.db.session,
            **{
                'client_id': self.test_context.admin_id,
                'kinopoisk_id': media_id,
                'label': media_title,
                'year': 1999,
                'url': 'http://test1'
            }
        )

        data = {
            'client_id': self.test_context.admin_id,
            'message_text': media_title,
            'choices': []
        }
        comm_message = command_message(
            app_enums.ComponentType.MAIN_APP,
            app_enums.ClientCommands.SEND_MESSAGES,
            data,
            self.test_context.admin_id
        )
        self.test_handler.handle_message(comm_message)

    def test_command_send_messages_by_media(self):
        media_id = '12345678'
        media_title = 'Тест 1'

        self.test_context.add_test_film(
            self.db.session,
            **{
                'client_id': self.test_context.admin_id,
                'kinopoisk_id': media_id,
                'label': media_title,
                'year': 1999,
                'url': 'http://test1'
            }
        )

        data = {
            'media_id': media_id,
            'message_text': media_title,
            'choices': []
        }
        comm_message = command_message(
            app_enums.ComponentType.MAIN_APP,
            app_enums.ClientCommands.SEND_MESSAGES_BY_MEDIA,
            data,
            self.test_context.admin_id
        )
        self.test_handler.handle_message(comm_message)

    def test_command_add_serial(self):

        self.mediator.start()
        self.parser.start()
        self.test_handler.start()

        command_data = dict(
            text='Игра'
        )
        command = app_enums.ClientCommands.ADD_SERIAL

        command_msg = command_message(app_enums.ComponentType.MAIN_APP, command, command_data, self.client_id)
        self.test_handler.handle_message(command_msg)

    def tearDown(self):
        self.test_context.clear_test_db()


def suite():
    return defaultTestLoader.loadTestsFromTestCase(TestCommandHandler)


if __name__ == '__main__':
    testRuner = TextTestRunner()
    testRuner.run(suite())
