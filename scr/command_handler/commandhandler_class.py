from abc import ABC, abstractmethod
import inspect
import sys
import logging

from mediator import AppMediatorClient, MediatorActionMessage, CommandData, parser_message, send_message
from app_enums import ClientCommands, ComponentType, ActionType
from database import DbManager

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
                message = command_dict[message_data.command.value](message_data, self.db_manager)
                if message is not None:
                    self.send_message(message)
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
    def add_film(cls, data: CommandData, db_manager: DbManager):
        """
        Command add film to base

        :return:
        """

        # TODO add command logic
        logger.debug('Поступил новый запрос на поиск фильма, от {0} c данными:{1}'.format(
            data.client_id,
            data.text)
        )

        message = parser_message(ComponentType.COMMAND_HANDLER, {'query': data.text}, data.client_id)

        return message


class SerialHandler(AbstractHandler):

    @classmethod
    def get_command_list(cls):
        return {
            ClientCommands.ADD_SERIAL.value: cls.add_serial,
            ClientCommands.ADD_SERIAL_BY_THEAN.value: cls.add_serial_by_them,
        }

    @classmethod
    def add_serial(cls, data: CommandData, db_manager: DbManager):
        """
        Command add serial to base

        :return:
        """
        # TODO add command logic
        logger.debug('Поступил новый запрос на поиск сериала, от {0} c данными:{1}'.format(
            data.client_id,
            data.text)
        )

        message = parser_message(ComponentType.COMMAND_HANDLER, {'serial_query': data.text}, data.client_id)

        return message

    @classmethod
    def add_serial_by_them(cls, data: CommandData, db_manager: DbManager):
        """
        Command add serial to base

        :return:
        """
        # TODO add command logic
        message = parser_message(ComponentType.COMMAND_HANDLER, {'thread': data.text}, data.client_id)

        return message

class UserHandler(AbstractHandler):

    @classmethod
    def get_command_list(cls):
        return {
            ClientCommands.ADD_USER.value: cls.add_user,
            ClientCommands.EDIT_SETTINGS.value: cls.set_user_option,
            ClientCommands.AUTHENTICATION.value: cls.auth_query,
        }

    @classmethod
    def add_user(cls, data: CommandData, db_manager: DbManager):
        """
        Add user to base
        :return:
        """
        user = db_manager.find_user(data.client_id)
        if user is not None:
            pass
        # TODO add command logic
        pass

    @classmethod
    def set_user_option(cls, data: CommandData, db_manager: DbManager):
        """
        Change some user option
        :return:
        """
        # TODO add command logic
        pass

    @classmethod
    def auth_query(cls, data: CommandData, db_manager: DbManager):
        """
        Query for authentication from new user/
        :param data:
        :param db_manager:
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

