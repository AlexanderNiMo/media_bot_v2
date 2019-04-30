from abc import ABC, abstractmethod
import inspect
import sys
import logging
from plexapi.server import PlexServer

from src.mediator import (
    AppMediatorClient,
    MediatorActionMessage,
    CommandData,
    parser_message, send_message, crawler_message, command_message
)

from src.app_enums import ClientCommands, ComponentType, ActionType, MediaType
from src.database import DbManager

logger = logging.getLogger(__name__)


class CommandMessageHandler(AppMediatorClient):
    """
    Listening messages from mediator, and redirect them to command handlers

    """

    CLIENT_TYPE = ComponentType.COMMAND_HANDLER
    CLIENT_ACTIONS = [ActionType.HANDLE_COMMAND, ]

    def __init__(self, in_queue, out_queue, config):
        super(self.__class__, self).__init__(in_queue, out_queue, config)
        self.db_manager = DbManager(self.config)

    def run(self):
        """
        Процедура, выполняемая при запуске процесса
        """
        logger.debug('Запуск клиента {}'.format(self.CLIENT_TYPE))
        self.listen()

    def handle_message(self, message: MediatorActionMessage):
        """
        Handle message

        :param message:
        :return:
        """
        logger.debug('Новое сообщение для {0}, от {1} c данными:{2}'.format(
            self.CLIENT_TYPE,
            message.from_component,
            message.data)
        )
        message_data = message.data

        if not isinstance(message_data, CommandData):
            logger.error('Message for command handler must be CommandData type!')
            raise TypeError('Message for command handler must be CommandData type!')

        for handler in get_command_handlers():
            command_dict = handler.get_command_list()

            if message_data.command.value in command_dict.keys():
                messages = handler.exsecute_command(message_data, self.db_manager, self.config)
                for msg in messages:
                    self.send_message(msg)
                break


class AbstractHandler(ABC):

    @classmethod
    @abstractmethod
    def get_command_list(cls)-> dict:
        return {}

    @classmethod
    def exsecute_command(cls, message_data: CommandData, db_manager, config):
        if not cls.check_rule(message_data.client_id, db_manager):
            return [send_message(
                ComponentType.COMMAND_HANDLER,
                {
                    'user_id': message_data.client_id,
                    'message_text': 'Для авторизации скинь свой id Морозу. Вот он: {}'.format(message_data.client_id),
                    'choices': []
                }
            )]
        command_dict = cls.get_command_list()
        message = command_dict[message_data.command.value](message_data, db_manager, config)
        result = []
        if isinstance(message, MediatorActionMessage):
            result.append(message)
        elif isinstance(message, list):
            result = message
        return result

    @classmethod
    def check_rule(cls, client_id: int, db_manager: DbManager):
        session = db_manager.get_session()
        user = db_manager.find_user(client_id, session)
        session.close()
        return user is not None


class FilmHandler(AbstractHandler):

    @classmethod
    def get_command_list(cls):

        return {ClientCommands.ADD_FILM.value: cls.add_film}

    @classmethod
    def add_film(cls, data: CommandData, db_manager: DbManager, config):
        """
        Command add film to base

        :return:
        """
        text = data.command_data['text']
        logger.debug('Поступил новый запрос на поиск фильма, от {0} c данными:{1}'.format(
            data.client_id,
            text)
        )

        message = parser_message(ComponentType.COMMAND_HANDLER, {'query': text, 'serial': False}, data.client_id)

        return message


class SerialHandler(AbstractHandler):

    @classmethod
    def get_command_list(cls):
        return {
            ClientCommands.ADD_SERIAL.value: cls.add_serial,
            ClientCommands.ADD_SERIAL_BY_THEAN.value: cls.add_serial_by_them,
        }

    @classmethod
    def add_serial(cls, data: CommandData, db_manager: DbManager, config):
        """
        Command add serial to base

        :return:
        """
        text = data.command_data['text']

        logger.debug('Поступил новый запрос на поиск сериала, от {0} c данными:{1}'.format(
            data.client_id,
            text)
        )

        message = parser_message(ComponentType.COMMAND_HANDLER, {'query': text, 'serial': True}, data.client_id)

        return message

    @classmethod
    def add_serial_by_them(cls, data: CommandData, db_manager: DbManager, config):
        """
        Command add serial to base

        :return:
        """
        text = data.command_data['text']
        message = parser_message(ComponentType.COMMAND_HANDLER, {'thread': text}, data.client_id)

        return message


class UserHandler(AbstractHandler):

    @classmethod
    def get_command_list(cls):
        return {
            ClientCommands.EDIT_SETTINGS.value: cls.set_user_option,
            ClientCommands.AUTHENTICATION.value: cls.auth_query,
        }

    @classmethod
    def set_user_option(cls, data: CommandData, db_manager: DbManager, config):
        """
        Change some user option
        :return:
        """
        messages = []
        session = db_manager.get_session()
        new_value = db_manager.change_user_option(data.client_id, data.command_data['option'], session=session)
        message_text = 'Статус оповещения установлен. Новое значение "{}"'.format(
            'оповещать' if new_value == 1 else 'не оповещать'
        )
        messages.append(
                send_message(
                    ComponentType.COMMAND_HANDLER,
                    {
                        'user_id': data.client_id, 'message_text': message_text, 'choices': []
                    }
                )
            )
        session.close()
        return messages

    @classmethod
    def auth_query(cls, data: CommandData, db_manager: DbManager, config):
        """
        Query for authentication from new user/
        :param data:
        :param db_manager:
        :return:
        """
        messages = []
        session = db_manager.get_session()
        if db_manager.is_admin(data.client_id):
            messages.append(
                command_message(
                    ComponentType.COMMAND_HANDLER,
                    ClientCommands.ADD_DATA_USER,
                    {
                        'client_id': data.command_data['client_id'],
                        'name': data.command_data['name'],
                        'last_name': data.command_data['last_name'],
                        'nick': data.command_data['nick']
                    },
                    data.client_id
                )
            )
        else:
            message_text = 'У тебя нет прав на добавление пользователей.'
            messages.append(
                send_message(
                    ComponentType.COMMAND_HANDLER,
                    {
                        'user_id': data.client_id, 'message_text': message_text, 'choices': []
                    }
                )
            )
        session.close()
        return messages


class AddDataHandler(AbstractHandler):

    @classmethod
    def get_command_list(cls):
        return {
            ClientCommands.ADD_DATA_FILM.value: cls.add_film,
            ClientCommands.ADD_DATA_SERIAL.value: cls.add_serial,
            ClientCommands.ADD_DATA_USER.value: cls.add_user,
            ClientCommands.UPDATE_MEDIA.value: cls.update_media_data,
            ClientCommands.ADD_MEDIA_TO_USER_LIST.value: cls.add_media_to_user_list,
        }

    @classmethod
    def add_user(cls, data: CommandData, db_manager: DbManager, config):
        """
        Add user to base
        :return:
        """
        messages = []
        session = db_manager.get_session()
        user = db_manager.find_user(data.command_data['client_id'], session)
        if user is not None:
            message_text = 'Пользователь с id:{} уже есть в базе.'.format(data.command_data['client_id'])
            messages.append(
                send_message(
                    ComponentType.COMMAND_HANDLER,
                    {
                        'user_id': data.client_id,
                        'message_text': message_text,
                        'choices': []
                    }
                )
            )
            session.close()
            return messages

        db_manager.add_user(
            data.command_data['client_id'],
            data.command_data['name'],
            data.command_data['last_name'],
            data.command_data['nick'],
            session=session,
        )
        session.close()
        message_text = 'Пользователь с id:{} добавлен.'.format(data.command_data['client_id'])
        messages.append(
            send_message(
                ComponentType.COMMAND_HANDLER,
                {
                    'user_id': data.client_id,
                    'message_text': message_text,
                    'choices': []
                }
            )
        )
        messages.append(
            send_message(
                ComponentType.COMMAND_HANDLER,
                {
                    'user_id': data.command_data['client_id'],
                    'message_text': 'Теперь ты в теме.',
                    'choices': []
                }
            )
        )

        return messages

    @classmethod
    def add_film(cls, data: CommandData, db_manager: DbManager, config):
        session = db_manager.get_session()
        film = db_manager.add_film(
            data.client_id,
            data.command_data['kinopoisk_id'],
            data.command_data['title'],
            data.command_data['year'],
            data.command_data['url'],
            session=session,
        )

        message_text = 'Фильм {0} добавлен к поиску \n {1}'.format(
            data.command_data['title'],
            data.command_data['url']
        )

        messages = [send_message(
            ComponentType.COMMAND_HANDLER,
            {
                'user_id': data.client_id, 'message_text': message_text, 'choices': []
            }
        ), crawler_message(
            ComponentType.COMMAND_HANDLER,
            data.client_id,
            {
                'media_id': film.kinopoisk_id,
                'media_type': MediaType.FILMS
            }
        )]

        session.close()
        return messages

    @classmethod
    def add_serial(cls, data: CommandData, db_manager: DbManager, config):
        session = db_manager.get_session()
        serial = db_manager.add_serial(data.client_id, data.command_data['kinopoisk_id'], data.command_data['title'],
                                       data.command_data['year'], data.command_data['season'], data.command_data['url'],
                                       data.command_data['series'], session=session)

        message_text = 'Сериал {0} сезон {1} добавлен к поиску \n {2}'.format(
            data.command_data['title'],
            data.command_data['season'],
            data.command_data['url']
        )

        messages = [
            send_message(
                ComponentType.COMMAND_HANDLER,
                {'user_id': data.client_id, 'message_text': message_text, 'choices': []}
            ),
            crawler_message(
                ComponentType.COMMAND_HANDLER,
                data.client_id,
                {
                    'media_id': serial.kinopoisk_id,
                    'media_type': MediaType.SERIALS,
                    'season': data.command_data['season']
                }
            )
        ]
        session.close()
        return messages

    @classmethod
    def update_media_data(cls, data: CommandData, db_manager: DbManager, config):
        com_data = data.command_data
        if 'media_id' not in com_data.keys():
            raise AttributeError('Для обновлвения данных необходимо передать kinopoisk_id')

        messages = []
        com_data = data.command_data
        session = db_manager.get_session()
        db_manager.update_media_params(
            com_data['media_id'],
            com_data['upd_data'],
            com_data['media_type'],
            session=session
        )

        if 'next_messages' in com_data.keys() and isinstance(com_data['next_messages'], list):
            messages += com_data['next_messages']
        session.close()
        return messages

    @classmethod
    def add_media_to_user_list(cls, data: CommandData, db_manager: DbManager, config):
        session = db_manager.get_session()
        db_manager.add_media_to_user_list(
            data.client_id,
            data.command_data['kinopoisk_id'],
            data.command_data['media_type'],
            data.command_data['season'],
            session=session,
        )
        session.close()


class PlexServerHandler(AbstractHandler):

    @classmethod
    def get_command_list(cls):
        return {
            ClientCommands.UPDATE_PLEX_LIB.value: cls.update_plex_libraries,
        }

    @classmethod
    def update_plex_libraries(cls, data: CommandData, db_manager: DbManager, config):
        server = PlexServer(
            'http://{0}:{1}'.format(config.PLEX_HOST, config.PLEX_PORT),
            config.PLEX_TOKEN
        )
        server.library.update()


class SendMessageHandler(AbstractHandler):

    @classmethod
    def get_command_list(cls):
        return {
            ClientCommands.SEND_MESSAGES.value: cls.send_message,
            ClientCommands.SEND_MESSAGES_BY_MEDIA.value: cls.send_message_by_media,
        }

    @classmethod
    def send_message_by_media(cls, data: CommandData, db_manager: DbManager, config):
        messages = []

        media_id = data.command_data['media_id']
        media_type = data.command_data['media_type']
        season = data.command_data['season'] if media_type.value == MediaType.SERIALS.value else 0

        recips = db_manager.get_users_for_notification(media_id, media_type, season=season)
        ids = set([i.client_id for i in recips])
        for recip in ids:
            messages.append(
                cls.construct_send_message(
                    recip,
                    data.command_data['message_text'],
                    data.command_data['choices'])
            )
        return messages

    @classmethod
    def send_message(cls, data: CommandData, db_manager: DbManager, config):
        messages = []
        client_id = data.client_id
        recips = cls.get_recipients(client_id, db_manager)

        for recip in recips:
            messages.append(
                cls.construct_send_message(recip, data.command_data['message_text'], data.command_data['choices'])
            )
        return messages

    @classmethod
    def construct_send_message(cls, user_id, message_text, choices):
        return send_message(
            ComponentType.COMMAND_HANDLER,
            {
                'user_id': user_id,
                'message_text': message_text,
                'choices': choices,
            }
        )

    @classmethod
    def get_recipients(cls, client_id, db_manager)-> []:

        if client_id is None:
            return []
        ids = set()

        if client_id == 0:
            result = db_manager.get_all_users()
            ids = set([i.client_id for i in result])
            return ids

        if isinstance(client_id, int):
            ids.add(client_id)
        if isinstance(client_id, list):
            ids.update(client_id)

        result = []
        for id in ids:
            user = db_manager.find_user(id)
            if user is not None:
                result.append(id)
        return result


def get_command_handlers():
    mods = inspect.getmembers(
        sys.modules[__name__],
        lambda x: inspect.isclass(x) and issubclass(x, AbstractHandler)
    )
    for mod in mods:
        yield mod[1]


if __name__ == '__main__':
    pass

