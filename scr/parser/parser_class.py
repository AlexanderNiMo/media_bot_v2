# -*- coding: utf-8 -*-

import logging
import re
from multiprocessing import Queue
from abc import ABC, abstractmethod

from app_enums import ActionType, ComponentType, ClientCommands, MediaType
from mediator import AppMediatorClient, MediatorActionMessage, send_message
from mediator.mediator_types.mediator_message import ParserData
from kinopoisk import movie, utils


logger = logging.getLogger(__name__)


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
            result = self.parse(message)
        else:
            return
        # Все завершилось успешно, никаких сообщений
        if result is None:
            return
        # Отправка сообщений, полученный при парсинге
        if isinstance(result, list):
            for elem in result:
                self.send_message(elem)
        else:
            return

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
        logger.debug('Начало парсинга данных {}'.format(message.data.data))
        return self.parser.parse(message.data)


class AbstractParser(ABC):
    """
    Выполняет процесс парсинга медиа данных

    """

    @abstractmethod
    def parse(self, data: ParserData):
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
        self.next_data = []
        self.messages = []

    def parse(self, data: ParserData):

        self.messages.clear()
        self.next_data.clear()

        if not self.can_parse(data.data):
            return self.base.parse(data)
        else:
            end_chain = self.parse_data(data.data)

        if end_chain:
            return self.end_chain(data)
        else:
            data.data = self.next_data
            return self.base.parse(data)

    def parse_data(self, data: dict)->bool:
        return True

    def can_parse(self, data: dict)->bool:
        return True

    def end_chain(self, data)-> dict:
        return None


class KinopoiskParser(BaseParser):
    """
    Производит поиск данных по базе кинопоиска

    """

    def parse_data(self, data: dict)->bool:

        film = True

        if 'season' in data.keys():
            film = False

        if film:
            find_func = self.find_film
        else:
            find_func = self.find_serial

        sucsess = find_func(data)

        return not sucsess

    def find_film(self, data: dict)-> [bool, list]:
        result = movie.Movie.objects.search(data['query'])

        for element in result:
            exact_match = element.title.replace(' ', '').upper() == data['query'].replace(' ', '').upper()
            if exact_match:
                self.next_data.clear()

            self.next_data.append({
                'kinopoisk_id': element.id,
                'title': element.title,
                'year': element.year,
                'url': element.get_url('main_page')
            })
            if exact_match:
                break

        return len(self.next_data) == 1

    def find_serial(self, data: dict)-> [bool, list]:
        result = movie.Movie.objects.search(data['query'])

        for element in result:
            exact_match = element.title.replace(' ', '').upper() == data['query'].replace(' ', '').upper()
            if exact_match:
                self.next_data.clear()
            self.next_data.append({
                'kinopoisk_id': element.id,
                'title': element.title,
                'year': element.year,
                'url': element.get_url('main_page'),
                'season': data['season']
            })
            if exact_match:
                break

        return len(self.next_data) == 1

    def can_parse(self, data: dict):
        return 'query' in data.keys()

    def end_chain(self, data: ParserData)-> list:

        if len(self.next_data) == 0:
            message_text = 'В кинопоиске, по запросу {0}, ' \
                       'ничего не найдено, уточни свой запрос.'.format(data.data['query'])
        else:
            message_text = 'В кинопоиске, по запросу {0}, ' \
                       'найдено более одного совпадения, выбери, что скачать.'.format(data.data['query'])

        choice_list = []
        a = 0
        for elem in self.next_data:
            choice_list.append(
                {
                    'message_text': elem['url'],
                    'button_text': str(a),
                    'call_back_data': elem
                }
            )
            a += 1

        self.messages.append(
            send_message(ComponentType.PARSER,
                         {
                             'user_id': data.client_id,
                             'message_text': message_text,
                             'choices': choice_list
                         }
                         )
        )

        return self.messages


class PlexParser(BaseParser):
    """
    Проверяет есть ли медиа в базе плекса

    """

    def parse_data(self, data: dict):
        pass

    def can_parse(self, data: dict):
        return 'query' in data.keys()


class DataBaseParser(BaseParser):
    """
    Проверяет добавлены ли данные для поиска

    """

    def parse_data(self, data: dict):
        pass

    def can_parse(self, data: dict):
        return 'kinopoisk_id' in data.keys() or all(key in data.keys() for key in ('label', 'year'))


class SerialQueryParser(BaseParser):
    """
    Парсит запрос сереала для дальнейшей обработки
    """

    def parse_data(self, data: dict):
        pass

    def can_parse(self, data: dict):
        return 'serial_query' in data.keys()


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
        SerialQueryParser,
        ParseTrackerThread,
    ]

    prev_elem = None
    res = None

    for elem in class_list:
        res = elem(prev_elem)
        prev_elem = res

    return res

if __name__ == '__main__':

    pParser = KinopoiskParser(BaseParser(None))
    data = ParserData({'query': 'Гарри поттер'}, 1)
    messages = pParser.parse(data)

    а = 1
