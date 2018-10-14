# -*- coding: utf-8 -*-
"""
Описывает класс посредник для взаимодействия в приложении

"""
from typing import List
from multiprocessing import Queue
from queue import Empty
import logging

from .abc_mediator_classes import MediatorMessage, Mediator, MediatorClient

logger = logging.getLogger(__name__)


class AppMediator(Mediator):
    """
    Класс посредник в приложении

    """
    def __init__(self, in_queue: Queue, clients: List[MediatorClient]) -> None:
        """

        Инициализирует класс поля класса

        __app - ссылка на приложение

        """
        super(AppMediator, self).__init__()
        self.__in_queue = in_queue
        self.__clients = []
        for client in clients:
            self.__clients.append({
                'client_type': client.CLIENT_TYPE,
                'client': client
            })
        logger.debug('Создание объекта посредника для сообщений')

    def run(self):
        logger.debug('Запуск процесса прослушивания в медиаторе.')
        while True:
            try:
                message = self.__in_queue.get()
                logger.debug('Полученно новое сообщение в медиаторе {}'.format(message))
                self.send_message(message)
            except Empty:
                pass

    def send_message(self, message: MediatorMessage) -> None:
        """

        посылает сообщение для компонента системы


        """
        for d_client in self.__clients:
            client = d_client['client']
            # проверка адресации сообщений
            if not (client.CLIENT_TYPE.value == message.component.value and \
                                message.action.value in [a.value for a in client.CLIENT_ACTIONS]):
                continue
            logger.debug('Сообщение с сервера отправлено для {}'.format(client))
            client.queue.put(message)

    def _get_new_client(self, client: MediatorClient):
        """
        Возвращает новый экземпляр клиента, для перезапуска процесса

        :param client:
        :return:
        """
        logger.debug('СОздана новая копия клиента {}'.format(client.CLIENT_TYPE))
        return client.__class__(client.queue, self.in_queue, client.config)

    def __set_client(self, new_client: MediatorClient):
        """
        Устанавливает нового клиента в список клиентов

        :param new_client:
        :return:
        """
        for client in self.__clients:
            if client['client_type'] == new_client.CLIENT_TYPE:
                client['client'] = new_client

    @property
    def in_queue(self):
        return self.__in_queue

    @property
    def clients(self):
        return (i['client'] for i in self.__clients)

    def check_clients(self):
        """

        Выполняет проверку живы ли клиенты и перезапускает из при необходимости
        :return:
        """
        logger.debug('Начало проверки состояния процессов клиентов')
        for d_client in self.__clients:
            client = d_client['client']

            if not client.is_alive():

                logger.error('Клиент {} умер, реанимирую...'.format(client.CLIENT_TYPE))
                try:
                    client = self._get_new_client(client)
                    client.start()
                    self.__set_client(client)
                except:
                    logger.error('Реанимация клиента {} не удалась...'.format(client.CLIENT_TYPE))


