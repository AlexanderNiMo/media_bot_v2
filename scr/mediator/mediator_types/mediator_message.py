# -*- coding: utf-8 -*-

"""

Описывает класс сообщений, используемых для медиатора

"""

from app_enums import ActionType, ComponentType, ClientCommands
from mediator.abc_mediator_classes import MediatorMessage


class MediatorActionMessage(MediatorMessage):
    """

    Класс сообщение для общения между компонентами

    """
    def __init__(self, component: ComponentType, action: ActionType, from_component: ComponentType) -> None:

        """

        Создает объект сообщение для отправки в медиатор

        :param component_type: Компонент назначения
        :param action: Выполняемое действие

        """
        self.__component_type = component
        self.__action = action
        self.__from = from_component

    def __str__(self):
        return 'Сообщение от {2} для {0} на выполнение {1}'.format(self.component, self.action, self.from_component)

    def __bool__(self):
        return self.__component_type is not None and self.__data is not None and self.__action is not None

    @property
    def from_component(self):
        return self.__from

    @property
    def component(self):
        return self.__component_type

    @property
    def action(self):
        return self.__action

    @property
    def data(self):
        return {}


class ClientMessage(MediatorActionMessage):

    def __init__(self, from_component: ComponentType, user_id: int, message_text: str, choices: []=list()):

        super(ClientMessage, self).__init__(ComponentType.CLIENT, ActionType.SEND_MESSAGE, from_component)

        self.__user_id = user_id
        self.__message_text = message_text
        self.__choices = choices

    @property
    def message_text(self):
        return self.__message_text

    @property
    def user_id(self):
        return self.__user_id

    @property
    def choices(self):
        return self.__choices

    @property
    def data(self):
        return {
            'user_id': self.user_id,
            'message_text': self.message_text,
            'choices': self.choices,
        }


class CrawlerMessage(MediatorActionMessage):

    def __init__(self, action: ActionType, media_id: str, from_component: ComponentType):

        super(CrawlerMessage, self).__init__(ComponentType.CRAWLER, action, from_component)

        self.__media_id = media_id

    @property
    def data(self):
        return {
            'media_id': self.__media_id,
        }


class ParserMessage(MediatorActionMessage):

    def __init__(self, text: str, sender_id: str, command: ClientCommands, from_component: ComponentType):

        super(ParserMessage, self).__init__(ComponentType.PARSER, ActionType.PARSE, from_component)
        self.__text = text
        self.__sender_id = sender_id
        self.__command = command

    @property
    def text(self):
        return self.__text

    @property
    def command(self):
        return self.__command

    @property
    def sender_id(self):
        return self.__sender_id

    @property
    def data(self):
        return {
            'text': self.__text,
            'sender_id': self.sender_id,
            'command': self.command,
        }


class CommandMessage(MediatorActionMessage):

    def __init__(self, text: str, chat_id: str, command: ClientCommands, from_component: ComponentType):

        super(CommandMessage, self).__init__(
            ComponentType.COMMAND_HANDLER,
            ActionType.HANDLE_COMMAND,
            from_component
        )
        self.__text = text
        self.__chat_id = chat_id
        self.__command = command

    @property
    def data(self):
        return {
            'text': self.__text,
            'chat_id': self.__chat_id,
            'command': self.__command,
        }


if __name__ == '__main__':
    """
    Тест __str__
    """
    m = MediatorActionMessage(ComponentType.PARSER, ActionType.PARSE, ComponentType.CLIENT)
    print(m)


