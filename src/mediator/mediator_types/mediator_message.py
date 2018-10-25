# -*- coding: utf-8 -*-

"""

Описывает класс сообщений, используемых для медиатора

"""

from src.app_enums import ActionType, ComponentType, ClientCommands, MediaType
from src.mediator.abc_mediator_classes import MediatorMessage, MessageData


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
        self.__data = None

    def __repr__(self):
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
        return self.__data

    @data.setter
    def data(self, value: MessageData):
        self.__data = value


class ClientData(MessageData):

    def __init__(self, user_id, message_text, choices):
        self.user_id = user_id
        self.message_text = message_text
        self.choices = choices

    def __repr__(self):
        return '<ClienData сообщение для пользователя {0} с текстом {1}>'.format(
            self.user_id,
            self.message_text
        )


class CrawlerData(MessageData):

    def __init__(self, client_id, media_id, season=0, force=False, media_type=MediaType.BASE_MEDIA, *args, **kwargs):
        self.media_id = media_id
        self.force = force
        self.media_type = media_type
        self.client_id = client_id
        self.season = season

        self.torrent_data = None
        self.torrent_id = None

        if 'torrent_data' in kwargs.keys():
            self.torrent_data = kwargs['torrent_data']
        if 'torrent_id' in kwargs.keys():
            self.torrent_id = kwargs['torrent_id']
        if len(kwargs.keys()) == 0:
            self.data = {}
        else:
            self.data = kwargs

    def __repr__(self):
        return '<CrawlerData from_user:{0}, kinopoisk_id:{1}, force:{2}>'.format(
            self.client_id,
            self.media_id,
            self.force
        )


class CommandData(MessageData):

    def __init__(self, command_data: dict, client_id: int, command: ClientCommands):
        self.command_data = command_data
        self.client_id = client_id
        self.command = command

    def __repr__(self):
        return '<CommandData Запрос на выаолнение команды {} от {}>'.format(
            self.command,
            self.client_id
        )


class ParserData(MessageData):

    def __init__(self, data: dict, client_id: int):
        self.data = data
        self.client_id = client_id


if __name__ == '__main__':
    """
    Тест __str__
    """
    m = MediatorActionMessage(ComponentType.PARSER, ActionType.PARSE, ComponentType.CLIENT)
    print(m)


