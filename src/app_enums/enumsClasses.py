"""

Словари для работы медиатора

"""
import enum


class MyEnum(enum.Enum):
    pass


class ComponentType(MyEnum):
    """

    Описывает словарь видов компонентов, взаимодействующих друг с другом

    """
    MAIN_APP = 0
    CLIENT = 1
    PARSER = 2
    CRAWLER = 3
    COMMAND_HANDLER = 4


class ActionType(MyEnum):
    """

    Описывает словарь доступных действий

    """

    SEND_MESSAGE = 1
    PARSE = 2
    FORCE_CHECK = 3
    HANDLE_COMMAND = 4
    CHECK_FILMS = 5
    CHECK_SERIALS = 6
    CHECK = 7
    ADD_TORRENT_TO_TORRENT_CLIENT = 8
    ADD_TORRENT_WATCHER = 9
    RETURNED_DATA = 10
    DOWNLOAD_TORRENT = 11


class ClientCommands(MyEnum):
    """
    Описывает команды от клиентов

    """

    ADD_FILM = 1
    ADD_SERIAL = 2
    ADD_SERIAL_BY_THEAN = 3

    AUTHENTICATION = 5

    SEND_MESSAGES_BY_MEDIA = 6
    SEND_MESSAGES = 14
    SEND_MESSAGES_TO_ALL = 15

    EDIT_SETTINGS = 7

    ADD_DATA_FILM = 8
    ADD_DATA_SERIAL = 9
    ADD_DATA_USER = 10
    ADD_MEDIA_TO_USER_LIST = 11

    UPDATE_MEDIA = 12

    UPDATE_PLEX_LIB = 13

    ADD_JOB = 14


class MediaType(MyEnum):
    """
    Типы медиа данных

    """

    BASE_MEDIA = 0
    FILMS = 1
    SERIALS = 2


class UserOptions(MyEnum):
    """
    Опции пользователей

    """

    NOTIFICATION = 1


class LockingStatus(MyEnum):
    """
    Статусы поиска медиа

    """

    IN_PROGRESS = 0
    ENDED = 1
    FIND_TORRENT = 2


class TorrentType(MyEnum):
    """
    Torrent трэкеры

    """

    NONE_TYPE = 0
    RUTRACKER = 1
    RUTOR = 2


class UserRule(MyEnum):
    """
    Права пользователей

    """

    ADMIN = 0
    USER = 1
