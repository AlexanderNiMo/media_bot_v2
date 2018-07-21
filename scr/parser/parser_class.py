# -*- coding: utf-8 -*-

import logging
import re
from multiprocessing import Queue
from abc import ABC, abstractmethod

from app_enums import ActionType, ComponentType, ClientCommands, MediaType
from mediator import AppMediatorClient, MediatorActionMessage


logger = logging.getLogger('BotApp')


class Parser(AppMediatorClient):

    CLIENT_TYPE = ComponentType.PARSER
    CLIENT_ACTIONS = [ActionType.PARSE, ]

    def __init__(self, in_queue: Queue, out_queue: Queue, config):
        super(Parser, self).__init__(in_queue, out_queue, config)
        self.parser = get_parser_chain()

    def handle_message(self, message: MediatorActionMessage):
        """
        Обрабатывает входящие сообщения
        """
        logger.debug('Полученно новое сообщение в {}'.format(message))
        if message.action == ActionType.PARSE:
            self.parse(message)

    def run(self):
        """
        Процедура, выполняемая при запуске процесса
        """
        logger.debug('Запуск клиента {}'.format(self.CLIENT_TYPE))
        self.listen()

    def parse(self, message: MediatorActionMessage):
        """
        Выполняет парсинг данных
        """
        logger.debug('Начало парсинга данных {}'.format(message.data))
        self.parser.parse(message.data)


class AbstractParser(ABC):
    """
    Выполняет процесс парсинга медиа данных

    """

    @abstractmethod
    def parse(self, data):
        """
        Производит парсинг входящих данных

        :param data:
        :return:
        """
        pass

    @abstractmethod
    def parse_data(self, data: dict):
        """
        Производит парсинг входящих данных

        :param data:
        :return:
        """
        pass

    @abstractmethod
    def can_parse(self, data: dict):
        """
        Проверяет возможна ли обработка входящий данных данным парсером

        :param data:
        :return:
        """
        pass


class BaseParser(AbstractParser):

    def __init__(self, base: AbstractParser):
        self.base = base

    def parse(self, data):

        if not self.can_parse(data):
            return self.base.parse_data(data)
        else:
            success = self.parse_data(data)

        if success:
            return self.base.parse_data(data)
        else:
            return data

    def parse_data(self, data: dict):
        return data

    def can_parse(self, data: dict):
        return True


class NoneParser(AbstractParser):

    def __init__(self):
        pass

    def parse(self, data):
        return data

    def parse_data(self, data: dict):
        pass

    def can_parse(self, data: dict):
        pass


class KinopoiskParser(BaseParser):
    """
    Производит поиск данныхпо базе кинопоиска

    """
    def parse_data(self, data: dict):
        pass

    def can_parse(self, data: dict):
        return 'query' in data.keys()


class PlexParser(BaseParser):
    """
    Проверяет есть ли медиа в базе плекса

    """
    def parse_data(self, data: dict):
        pass

    def can_parse(self, data: dict):
        return 'label' in data.keys()


class DataBaseParser(BaseParser):
    """
    Проверяет добавлены ли данные для поиска

    """
    def parse_data(self, data: dict):
        pass

    def can_parse(self, data: dict):
        return 'kinopoisk_id' in data.keys() or all(key in data.keys() for key in ('label', 'year'))


class ParseTrackerThread(BaseParser):
    """
    Распарсивает тему трекера для добавления по конкреной теме с трекера

    """
    def parse_data(self, data: dict):
        pass

    def can_parse(self, data: dict):
        return 'thread' in data.keys()


def get_parser_chain()-> AbstractParser:
    """
    Возвращает цепочку парсеров в порядке их выполнения

    :return:
    """

    class_list = [
        BaseParser,
        PlexParser,
        DataBaseParser,
        KinopoiskParser,
        ParseTrackerThread,
    ]

    prev_elem = None
    res = None

    for elem in class_list:
        if prev_elem is None:
            prev_elem = NoneParser()
        res = elem(prev_elem)
        prev_elem = res

    return res


