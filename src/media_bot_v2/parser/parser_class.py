# -*- coding: utf-8 -*-

import logging
import re
from multiprocessing import Queue
from abc import ABC, abstractmethod

import requests
import telebot
from telebot import apihelper
from plexapi.server import PlexServer
import tmdbsimple

from telegram import error as teleg_error, Bot


from media_bot_v2.config import Config
from media_bot_v2.database import DbManager
from media_bot_v2.app_enums import ActionType, ComponentType, ClientCommands, MediaType, LockingStatus
from media_bot_v2.mediator import AppMediatorClient, MediatorActionMessage, send_message, parser_message, command_message
from media_bot_v2.mediator import ParserData

logger = logging.getLogger(__name__)


class Parser(AppMediatorClient):
    CLIENT_TYPE = ComponentType.PARSER
    CLIENT_ACTIONS = [ActionType.PARSE, ]

    def __init__(self, in_queue: Queue, out_queue: Queue, config):
        super(Parser, self).__init__(in_queue, out_queue, config)
        self.parser = get_parser_chain(config)

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
        if len(message.data.data_needed) == 0:
            return self.parser.parse(message.data)
        else:
            t_parser = TargetParser(self.config)
            return t_parser.parse(message)


class TargetParser:
    """
    Производит поиск заказанных данных
    """
    def __init__(self ,conf: Config):
        self.config = conf
        self.parser_class_list = [
            TextQueryParser(None, self.config),
            PlexParser(None, self.config),
            MovieDBParser(None, self.config),
            TextQueryParser(None, self.config),
            ParseTrackerThread(None, self.config),
            TelegrammParser(None, self.config),
            DataBaseParser(None, self.config),
        ]

    def parse(self, message: MediatorActionMessage):
        data = message.data
        for parser in self.parser_class_list:
            if parser.can_get_data(data.data_needed, data.data):
                error = parser.get_data(data)
                if not error:
                    data.data.update(parser.next_data)
                else:
                    parser.end_chain(data)

        msg = MediatorActionMessage(message.from_component, ActionType.RETURNED_DATA, ComponentType.PARSER)
        msg.data = data

        return [msg]


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

    def __init__(self, base: AbstractParser, conf: Config):
        self.base = base
        self.next_data = {}
        self.messages = []
        self.config: Config = conf
        self.cache_data = None

    def parse(self, data: ParserData):

        self.messages.clear()
        self.next_data.clear()

        if not self.can_parse(data.data):
            return self.base.parse(data)
        else:
            try:
                sucsess = self.parse_data(data.data)
            except Exception as ex:
                logger.error(f'Error while parsing by {self.__class__.__name__} , {ex}')
                raise ex

        if sucsess:
            data.data = self.next_data
            return self.base.parse(data)
        else:
            return self.end_chain(data)

    def parse_data(self, data: dict) -> bool:
        return False

    def can_parse(self, data: dict) -> bool:
        return True

    def end_chain(self, data: ParserData) -> list:

        command = ClientCommands.ADD_DATA_FILM if 'serial' in data.data.keys() and \
                                                  not data.data['serial'] else ClientCommands.ADD_DATA_SERIAL

        self.messages.append(
            command_message(ComponentType.PARSER, command, data.data, data.client_id)
        )
        return self.messages

    @staticmethod
    def _get_words(text: str) -> list:
        """
        Получает список слов из текста

        :param text: текст для обработки
        :return: список слов из запроса
        """
        data = re.findall(r'\S+', text)
        return data

    def _normalize_query_text(self, query: str) -> str:
        """
        Нормализует текст запроса

        :param query: - текст для обработки
        :return: - Нормализованый запрос для хранения и поиска
        """
        res = u' '
        return res.join(self._get_words(query))

    def can_get_data(self, needed_data: list, data: dict):
        return all(map(lambda x: x in data.keys(), self.needed_data())) \
               and any(map(lambda x: x in self.returned_data(), needed_data))

    def get_data(self, data: ParserData):
        if self.can_get_data(data.data_needed, data.data):
            errors, result_data = self.get_needed_data(data.data, data.data_needed)
            data.data.update(result_data)
            self.next_data = data.data
            return errors
        else:
            return False

    def get_needed_data(self, data: dict,  data_needed: list)-> (bool, dict):
        return False, {}

    @staticmethod
    def needed_data():
        return []

    @staticmethod
    def returned_data():
        return []


class MovieDBParser(BaseParser):
    """
    Производит поиск данных по базе кинопоиска

    """

    def __init__(self, base: AbstractParser, conf: Config):
        super(MovieDBParser, self).__init__(base, conf)
        tmdbsimple.API_KEY = conf.tmdb_cfg.api_key
        sess = requests.session()
        sess.proxies = {
            "http": conf.proxy_cfg.build_proxy_str(),
            "https": conf.proxy_cfg.build_proxy_str(),
        }
        tmdbsimple.REQUESTS_SESSION = sess
        self.ia = tmdbsimple.Search()

    def parse_data(self, data: dict) -> bool:

        film = True

        if 'serial' in data.keys():
            film = not data['serial']

        if film:
            find_func = self.find_film
        else:
            find_func = self.find_serial

        sucsess = find_func(data)

        return sucsess

    def find_film(self, data: dict) -> tuple[bool, list]:
        result = self.ia.movie(language='ru', query=data['query'])

        if len(result.get('results')) == 0:
            logger.warning('No info on query %s', data['query'])
            self.next_data = data.copy()
            if not 'choices' in self.next_data:
                self.next_data['choices'] = []
        else:
            self.next_data = {'choices': []}

        for element in result.get('results', []):
            logger.info('got %s', element)
            film = tmdbsimple.Movies(element.get("id"))
            film_info = film.info()
            if film.imdb_id is None:
                continue

            title = element.get("title",data['query'])
            year = element.get('release_date', None)
            if year is None:
                logger.debug(f"Skip element {element} (no year)")
                continue
            year = int(year[:4])

            exact_match = self.check_title_match_query_data(title, year, data)

            if exact_match:
                self.next_data['choices'].clear()

            cover_url = 'https://image.tmdb.org/t/p/w342' + film_info.get('poster_path', "")

            imdb_url = "https://www.imdb.com/title/"+film.imdb_id

            choise = {
                'kinopoisk_id': film.imdb_id,
                'title': self._normalize_query_text(title),
                'year': year,
                'url': imdb_url,
                'kinopoisk_url': imdb_url,
                'serial': False,
                'cover_url': cover_url
            }
            self.next_data['choices'].append(choise)
            if exact_match:
                break

        if len(self.next_data['choices']) == 1:
            data_to_add = self.next_data['choices'][0]
            self.next_data = data.copy()
            self.next_data.update(data_to_add)

        return 'choices' not in self.next_data.keys()

    def find_serial(self, data: dict) -> [bool, list]:
        result = self.ia.tv(language='ru', query=data['query'])

        if len(result.get('results', [])) == 0:
            self.next_data = data.copy()
            return False
        else:
            self.next_data = {'choices': []}

        for element in result.get('results', []):
            logger.debug(f"Get element: {element}")

            title = element.get("name",data['query'])
            year = element.get('first_air_date', None)
            if year is None:
                logger.debug(f"Skip element {element} (no year)")
                continue
            year = int(year[0:4]) 
            if 'year' in data and not year == data.get('year', None):
                logger.debug(f"Skip element {element} (year != )")
                continue 

            media_id = element.get('id', None)
            serial = tmdbsimple.TV(media_id)

            serial_info = serial.info()
            season = data['season']
            seasons = serial_info.get("seasons", [])
            if not seasons:
                logger.debug(f"Skip element {element} (no seasons)")
                continue
            season_info = next(filter(lambda x: x.get('season_number', 0) == season, seasons), None)
            if not season_info:
                logger.debug(f"Skip element {element} (no season)")
                continue
            series = season_info.get('episode_count')
            p_path = season_info.get('poster_path', serial_info.get("poster_path", ""))
            cover_url = 'https://image.tmdb.org/t/p/w342' + p_path if p_path else ''
            s_year = season_info.get('air_date')
            if s_year:
                year = int(s_year[:4])
            imdb_id = serial.external_ids().get('imdb_id')
            if not imdb_id:
                continue
            imdb_url = "https://www.imdb.com/title/" + imdb_id

            exact_match = self.check_title_match_query_data(title, year, data)
            if exact_match:
                self.next_data['choices'].clear()

            self.next_data['choices'].append({
                'kinopoisk_id': imdb_id,
                'title': self._normalize_query_text(title),
                'year': year,
                'kinopoisk_url': imdb_url,
                'url': imdb_url,
                'season': data['season'],
                'serial': True,
                'cover_url': cover_url,
                'series': series,
            })
            
            if exact_match:
                break
        if self.next_data.get('choices') is None:
            return False 
        if len(self.next_data.get('choices')) == 1:
            data_to_add = self.next_data['choices'][0]
            self.next_data = data.copy()
            self.next_data.update(data_to_add)

        return 'choices' not in self.next_data.keys()

    def check_title_match_query_data(self, tittle: str, year, data):
        title_match = self._normalize_query_text(tittle.upper()) == self._normalize_query_text(data['query']).upper()
        year_match = ('year' in data.keys() and year == data['year']) or 'year' not in data.keys()

        return title_match and year_match

    def _get_ru_tittle(self, imdb_obj, lang: str = 'RU') -> str:
        titles = self.ia.get_movie_main(imdb_obj.getID())
        if 'akas' not in titles['data']:
            return imdb_obj.data['title']
        ru_tittle = next(
            map(
                lambda x: x['title'],
                filter(lambda x:  x.get('region', None) == lang, titles['data']['akas'])
            ),
            imdb_obj.data['title']
        )
        return ru_tittle

    def can_parse(self, data: dict):
        return 'query' in data.keys()

    def end_chain(self, data: ParserData) -> list:
        action_name = 'kinopoisk'
        if self.next_data.get('choices') is None or len(self.next_data['choices']) == 0:
            message_text = 'В кинопоиске, по запросу {0}, ' \
                           'ничего не найдено, уточни свой запрос.'.format(data.data['query'])
            self.next_data['choices'] = []
        else:
            message_text = 'В кинопоиске, по запросу {0}, ' \
                           'найдено более одного совпадения, выбери, что скачать.'.format(data.data['query'])

        choice_list = []
        a = 0
        for elem in self.next_data['choices']:
            elem.update({'action': action_name})
            choice_list.append(
                {
                    'message_text': elem['url'],
                    'button_text': str(a),
                    'call_back_data': elem,
                }
            )
            a += 1

        choices = {
            'action': action_name,
            'data': choice_list
        }

        self.messages.append(
            send_message(ComponentType.PARSER,
                         {
                             'user_id': data.client_id,
                             'message_text': message_text,
                             'choices': choices
                         }
                         )
        )

        return self.messages

    def get_needed_data(self, data: dict,  data_needed: list)-> (bool, dict):
        if data['media_type'] == MediaType.FILMS:
            find_func = self.find_film
        else:
            find_func = self.find_serial

        sucsess = find_func(data)

        return not sucsess, self.next_data

    def needed_data(self):
        res = ['media_type', 'query']
        return res

    @staticmethod
    def returned_data():
        return ['kinopoisk_url', 'kinopoisk_id', 'title']


class PlexParser(BaseParser):
    """
    Проверяет есть ли медиа в базе плекса

    """

    def parse_data(self, data: dict):
        try:
            server = PlexServer(
                'http://{0}:{1}'.format(self.config.plex_cfg.host, self.config.plex_cfg.port),
                self.config.plex_cfg.token
            )

            plex_data = server.search(data['title'])
            self.next_data = data.copy()

            if 'serial' in data.keys() and data['serial']:
                result = self.check_serials(plex_data, data)
            else:
                result = self.check_film(plex_data, data)

            return len(result) == 0
        except Exception as ex:
            logger.debug(ex)
            self.next_data = data.copy()
            return True

    def can_parse(self, data: dict):

        return 'title' in data.keys()

    def end_chain(self, data):
        message_text = '{1} {0} уже есть на plex.'.format(data.data['title'],
                                                          'Фильм' if 'serial' in data.data.keys()
                                                                     and not data.data['serial'] else 'Сериал'
                                                          )

        self.messages.append(
            send_message(ComponentType.PARSER,
                         {
                             'user_id': data.client_id,
                             'message_text': message_text,
                             'choices': []
                         }
                         )
        )

        return self.messages

    def check_film(self, plex_data: list, data: dict) -> list:
        return list(filter(lambda x: x.title.upper() == data['title'].upper() and x.year == data['year'], plex_data))

    def check_serials(self, plex_data: list, data: dict) -> list:
        result = []
        for element in plex_data:
            if not element.TYPE == 'show':
                continue
            title_match = self._normalize_query_text(element.title) == self._normalize_query_text(data['title']) \
                          and element.year == data['year']
            if not title_match:
                continue
            season_in_show = True
            if 'season' in data.keys():
                seasons = element.seasons()
                season_in_show = any(i.seasonNumber == data['season'] for i in seasons)
            if season_in_show:
                result.append(element)
        return result

    def check_film(self, plex_data: list, data: dict) -> list:
        return list(filter(
                lambda x: x.title.upper() == data['title'].upper() and x.year == data['year'],
                plex_data
            ))

    def get_needed_data(self, data: dict,  data_needed: list)-> (bool, dict):
        session = requests.session()
        session.proxies = {}
        server = PlexServer(
            'http://{0}:{1}'.format(self.config.plex_cfg.host, self.config.plex_cfg.port),
            self.config.plex_cfg.token,
            session
        )
        plex_data = server.search(data['title'])
        if data['media_type'] == MediaType.FILMS:
            result = self.check_film(plex_data, data)
        else:
            result = self.check_serials(plex_data, data)

        return not len(result) == 0, {'media_in_plex': not len(result) == 0}

    def needed_data(self):
        res = ['media_type', 'title', 'year']
        return res

    @staticmethod
    def returned_data():
        return ['media_in_plex']


class DataBaseParser(BaseParser):
    """
    Проверяет добавлены ли данные для поиска

    """

    def parse_data(self, data: dict):

        result = True

        db = DbManager(self.config.db_cfg)
        media_type = MediaType.FILMS if not data['serial'] else MediaType.SERIALS
        session = db.get_session()
        if 'kinopoisk_id' in data.keys():
            args = dict(session=session)
            if media_type == MediaType.SERIALS:
                args.update(dict(season=data['season']))
            media = db.find_media(data['kinopoisk_id'], media_type, **args)
        elif all(key in data.keys() for key in ('label', 'year')):
            media = db.find_media_by_label(data['label'], data['year'], media_type, session=session)
        else:
            media = None
        if media is not None:
            data.update({'media_status': media.status, 'media_type': media_type})
            result = False
        session.close()
        self.next_data = data.copy()

        return result

    def can_parse(self, data: dict):
        return 'kinopoisk_id' in data.keys() or all(key in data.keys() for key in ('label', 'year'))

    def end_chain(self, data):
        text_type = 'Фильм' if data.data['media_type'].value == MediaType.FILMS.value else 'Сериал'
        title = data.data['title']
        if data.data['media_status'] != LockingStatus.ENDED:
            message_text = f'{text_type} {title} уже ищется.'
        else:
            message_text = f'Поиск {text_type}а по запросу {title} завершен.'

        self.messages.append(
            send_message(ComponentType.PARSER,
                         {
                             'user_id': data.client_id,
                             'message_text': message_text,
                             'choices': []
                         }
                         )
        )

        self.messages.append(
            command_message(
                ComponentType.PARSER,
                ClientCommands.ADD_MEDIA_TO_USER_LIST,
                {
                    'kinopoisk_id': data.data['kinopoisk_id'],
                    'media_type': MediaType.FILMS if 'serial' in data.data.keys()
                                                     and not data.data['serial'] else MediaType.SERIALS,
                    'season': data.data['season'] if 'season' in data.data.keys() else 0,
                },
                data.client_id,
            )
        )

        return self.messages

    def get_needed_data(self, data: dict, data_needed: list) -> (bool, dict):

        if not 'media_in_db' in data_needed:
            return False, self.next_data
        error = False

        db = DbManager(self.config.db_cfg)
        media_type = data['media_type']
        session = db.get_session()

        if 'kinopoisk_id' in data.keys():
            args = dict(session=session)
            if media_type == MediaType.SERIALS:
                args.update(dict(season=data['season']))
            media = db.find_media(data['kinopoisk_id'], media_type, **args)
        else:
            media = None
            error = True
        self.next_data = data.copy()
        self.next_data['media_in_db'] = media is not None
        session.close()

        return error, self.next_data

    def needed_data(self):
        res = ['media_type', 'kinopoisk_id']
        return res

    @staticmethod
    def returned_data():
        return ['media_in_db']


class TextQueryParser(BaseParser):
    """
    Парсит текстовый запрос для дальнейшей обработки
    """

    def __init__(self, base: AbstractParser, conf):
        super(__class__, self).__init__(base, conf)
        self.serial = False
        self.season = None
        self.year = None

    def parse_data(self, data: dict):

        errors = False

        query_text = self._normalize_query_text(data['query'])
        self.next_data = data.copy()

        # Проверка года в запросе
        year = self._get_year(query_text)
        if year is None:
            errors = True
        else:
            self.next_data['year'] = year
            self.year = year

        # Проверка сезона в запросе
        if 'serial' in data.keys() and data['serial']:
            self.serial = True
            season = self._get_season(query_text)
            if season is None:
                errors = True
            else:
                self.next_data['season'] = season
                self.season = season

        # Замена текста года и сезона
        query_text = self._replase_data_in_query(query_text, [year, 'сезон {}'.format(self.season)])

        self.next_data['query'] = query_text
        self.next_data['query_ok'] = True

        return not errors

    def can_parse(self, data: dict):
        return 'query_ok' not in data.keys() and 'query' in data.keys()

    def end_chain(self, data: ParserData):
        if self.year is None:
            self.messages.append(
                send_message(
                    ComponentType.PARSER, {
                        'user_id': data.client_id,
                        'message_text': 'В следующий раз добавляй год к поиску, для более точного поиска',
                        'choices': []
                    }
                )
            )
        if self.serial:
            if self.season is None:
                self.messages.append(
                    send_message(
                        ComponentType.PARSER, {
                            'user_id': data.client_id,
                            'message_text': 'Для поиска сериала, необходимо указать сезон!'
                                            ' Пример: /serial Игра престолов 2011 сезон 1',
                            'choices': []
                        }
                    )
                )

        if (self.serial and self.season is not None) or not self.serial:
            self.messages.append(
                parser_message(ComponentType.PARSER, self.next_data, data.client_id)

            )
        return self.messages

    @staticmethod
    def needed_data():
        return ['query']

    @staticmethod
    def returned_data():
        return ['year', 'query', 'season']

    def get_needed_data(self, data: dict, needed_data: list)-> (bool, dict):
        text = data['query']
        errors = False
        result = {}
        normal_query = self._normalize_query_text(text)
        replace_data = []

        if 'year' in needed_data:
            year = self._get_year(normal_query)
            result['year'] = data.get('year', year)
            replace_data.append(year)

        if 'season' in needed_data:
            season = self._get_season(normal_query)
            if season is None:
                errors = True
            else:
                result['season'] = season
                replace_data.append('сезон {}'.format(self.season))

        # Замена текста года и сезона
        query_text = self._replase_data_in_query(normal_query, replace_data)

        if 'query' in needed_data:
            result['query'] = query_text

        return errors, result

    @staticmethod
    def _get_year(text: str) -> int or None:
        """
        Выделяет год из запроса
        :param text:
        :return:
        """
        year_data = re.findall(r'\s\d{4}', text)
        if len(year_data) == 0:
            return None
        return int(year_data[0])

    def _get_season(self, text):
        if not self._check_word_in_text(text.upper(), u'сезон'.upper()):
            return None
        data = re.findall(r'СЕЗОН\s+\d{1,2}', text.upper())
        if len(data) == 0:
            data = re.findall(r'\d{1,2}\s+СЕЗОН', text.upper())
        if len(data) == 0:
            return None
        return int(re.findall(r'\d{1,2}', data[0])[0])

    def _check_word_in_text(self, message, text, words=None):
        if words is None:
            words = []
        if len(words) == 0:
            words = self._get_words(message.upper())
        return text.upper() in words

    def _replase_data_in_query(self, text: str, data):
        result = text
        if isinstance(data, list):
            for e in data:
                result = self._normalize_query_text(result.upper().replace(str(e).upper(), u''))
        else:
            result = self._normalize_query_text(result.upper().replace(str(data).upper(), u''))
        return result


class ParseTrackerThread(BaseParser):
    """
    Распарсивает тему трекера для добавления по конкреной теме с трекера

    """

    def parse_data(self, data: dict):
        pass

    def can_parse(self, data: dict):
        return 'thread' in data.keys()


class TelegrammParser(BaseParser):

    def __init__(self, base: AbstractParser, conf: Config):
        super(__class__, self).__init__(base, conf)
        self.config = conf.tg_cfg
        self.bot = self._get_bot()

    def _get_bot(self):
        apihelper.proxy = {
            'https': self.config.proxy_cfg.build_proxy_str(),
            'http': self.config.proxy_cfg.build_proxy_str(),
        }
        return telebot.TeleBot(self.config.bot_token)

    def parse_data(self, data: dict):
        user_id = data['telegramm_client']
        try:
            client_data = self.bot.get_chat(user_id)
            next_data = {
                'client_id': user_id,
                'name': client_data.first_name,
                'last_name': client_data.last_name,
                'nick': client_data.username
            }
        except teleg_error.BadRequest:
            next_data = {'client_id': user_id, 'name': '', 'last_name': '', 'nick': ''}

        self.next_data = data.copy()
        self.next_data.update(next_data)
        return False

    def can_parse(self, data: dict):
        return 'telegramm_client' in data.keys()

    def end_chain(self, data: ParserData):
        return self.messages

    @staticmethod
    def needed_data():
        return ['client_id']

    @staticmethod
    def returned_data():
        return ['nick', 'name', 'last_name']

    def get_needed_data(self, data: dict, needed_data: list)-> (bool, dict):
        user_id = data['client_id']
        try:
            client_data = self.bot.get_chat(user_id)
            next_data = {
                'client_id': user_id,
                'name': client_data.first_name,
                'last_name': client_data.last_name,
                'nick': client_data.username
            }
        except teleg_error.BadRequest:
            next_data = {'client_id': user_id, 'name': '', 'last_name': '', 'nick': ''}

        self.next_data = data.copy()
        self.next_data.update(next_data)
        return False, self.next_data


def get_parser_chain(config) -> BaseParser:
    """
    Возвращает цепочку парсеров в порядке их выполнения

    :return:
    """

    class_list = [
        BaseParser,
        DataBaseParser,
        PlexParser,
        MovieDBParser,
        TextQueryParser,
        ParseTrackerThread,
    ]

    prev_elem = None
    res = None

    for elem in class_list:
        res = elem(prev_elem, config)
        prev_elem = res

    return res


if __name__ == '__main__':

    from src.app import config as _conf

    _class_list = [
        BaseParser,
        PlexParser,
        MovieDBParser,
        TextQueryParser,
    ]

    _prev_elem = None
    _res = None

    for _elem in _class_list:
        _res = _elem(_prev_elem, _conf)
        _prev_elem = _res

    _data = ParserData(
        {
            'query': 'Игра престолов 2011 сезон 15',
            'serial': True,
            'season': 15,
            'year': 2011
        },
        1
    )
    msg = _prev_elem.parse(_data)
