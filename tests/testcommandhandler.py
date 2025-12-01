from unittest import TestCase, TextTestRunner, defaultTestLoader

from tests.utils import TestEnvCreator

from media_bot_v2 import app_enums
from media_bot_v2.mediator import command_message


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
            'media_type': app_enums.MediaType.FILMS,
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

    def test_update_media_data(self):
        media_id = '12345678'
        media_title = 'Тест 1'

        new_label = 'Тест 2'

        command_data = {
            'client_id': self.test_context.admin_id,
            'kinopoisk_id': media_id,
            'label': media_title,
            'year': 1999,
            'url': 'http://test1'
        }

        self.test_context.add_test_film(
            self.db.session,
            **command_data
        )

        data = {
            'media_id': media_id,
            'media_type': app_enums.MediaType.FILMS,
            'upd_data': {
                'label': new_label
            }
        }

        command = app_enums.ClientCommands.UPDATE_MEDIA
        command_msg = command_message(app_enums.ComponentType.MAIN_APP, command, data, self.client_id)
        self.test_handler.handle_message(command_msg)

        media = self.db.find_media(media_id, app_enums.MediaType.FILMS)

        self.assertTrue(media.title == new_label, 'Наименование не изменилось.')

    def test_add_user(self):
        new_user_id = 12345

        data = {
            'client_id': new_user_id,
            'name': 'Al',
            'last_name': 'Al',
            'nick': 'Al'
        }

        command_msg = command_message(
            app_enums.ComponentType.CLIENT,
            app_enums.ClientCommands.ADD_DATA_USER,
            data,
            self.client_id
        )

        self.test_handler.handle_message(command_msg)

        new_user = self.db.find_user(new_user_id)

        self.assertIsNotNone(new_user, 'Новый пользователь не создан.')

    def test_add_media_to_user(self):
        media_id = '12345678'
        media_title = 'Тест 1'
        client_id = 1225

        film = self.test_context.add_test_film(
            self.db.session,
            **{
                'client_id': self.test_context.admin_id,
                'kinopoisk_id': media_id,
                'label': media_title,
                'year': 1999,
                'url': 'http://test1'
            }
        )

        user = self.db.add_user(client_id, '', '', '')

        data = {
            'kinopoisk_id': media_id,
            'media_type': app_enums.MediaType.FILMS,
            'season': 0
        }

        command_msg = command_message(
            app_enums.ComponentType.CLIENT,
            app_enums.ClientCommands.ADD_MEDIA_TO_USER_LIST,
            data,
            client_id
        )

        self.test_handler.handle_message(command_msg)

        self.assertIn(str(film.kinopoisk_id), [a.kinopoisk_id for a in user.media.all()], 'Фильм не добавлен пользователю')

    def tearDown(self):
        self.test_context.clear_test_db()


def suite():
    return defaultTestLoader.loadTestsFromTestCase(TestCommandHandler)


if __name__ == '__main__':
    testRuner = TextTestRunner()
    testRuner.run(suite())
