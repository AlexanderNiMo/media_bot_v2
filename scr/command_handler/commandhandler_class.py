from abc import ABC, abstractmethod
import inspect
import sys
import logging

from mediator import AppMediatorClient, MediatorActionMessage
from app_enums import ClientCommands, ComponentType, ActionType
from database import DB_Manager

logger = logging.getLogger('BotApp')


class CommandMessageHandler(AppMediatorClient):
    """
    Listening messages from mediator, and redirect them to command handlers

    """

    CLIENT_TYPE = ComponentType.COMMAND_HANDLER
    CLIENT_ACTIONS = [ActionType.HANDLE_COMMAND, ]

    def __init__(self, in_queue, out_queue, config):
        super(self.__class__, self).__init__(in_queue, out_queue, config)
        self.db_manager = DB_Manager(self.config)

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
        if 'command' not in message_data.keys():
            logger.error('Message for command handler must have key command!')
            raise ValueError('Message for command handler must have key command!')

        for handler in get_command_handlers():
            command_dict = handler.get_command_list()
            dict().keys()
            if message_data['command'].value in command_dict.keys():
                command_dict[message_data['command'].value](message_data, self.db_manager)
                break


class AbstractHandler(ABC):

    @classmethod
    @abstractmethod
    def get_command_list(cls)-> dict:
        return {}


class FilmHandler(AbstractHandler):

    @classmethod
    def get_command_list(cls):

        return {ClientCommands.ADD_FILM.value: cls.add_film}

    @classmethod
    def add_film(cls, data: dict, db_manager: DB_Manager):
        """
        Command add film to base

        :return:
        """
        # TODO add command logic
        logger.debug('Поступил новый запрос на поиск фильма, от {0} c данными:{1}'.format(
            data['chat_id'],
            data['text'])
        )
        pass


class SerialHandler(AbstractHandler):

    @classmethod
    def get_command_list(cls):
        return {
            ClientCommands.ADD_SERIAL.value: cls.add_serial,
            ClientCommands.ADD_SERIAL_BY_THEAN.value: cls.add_serial_by_them,
        }

    def add_serial(self, data: dict, db_manager: DB_Manager):
        """
        Command add serial to base

        :return:
        """
        # TODO add command logic
        pass

    def add_serial_by_them(self, data: dict, db_manager: DB_Manager):
        """
        Command add serial to base

        :return:
        """
        # TODO add command logic
        pass


class UserHandler(AbstractHandler):

    @classmethod
    def get_command_list(cls):
        return {
            ClientCommands.ADD_USER.value: cls.add_user,
            ClientCommands.EDIT_SETTINGS.value: cls.set_user_option,
            ClientCommands.AUTHENTICATION.value: cls.auth_query,
        }

    @classmethod
    def add_user(cls, data: dict, db_manager: DB_Manager):
        """
        Add user to base
        :return:
        """
        # TODO add command logic
        pass

    @classmethod
    def set_user_option(cls, data: dict, db_manager: DB_Manager):
        """
        Change some user option
        :return:
        """
        # TODO add command logic
        pass

    @classmethod
    def auth_query(cls, data, db_manager: DB_Manager):
        """
        Query for authentication from new user/
        :param data:
        :return:
        """
        # TODO add command logic
        pass


def get_command_handlers():
    mods = inspect.getmembers(
        sys.modules[__name__],
        lambda x: inspect.isclass(x) and issubclass(x, AbstractHandler)
    )
    for mod in mods:
        yield mod[1]

