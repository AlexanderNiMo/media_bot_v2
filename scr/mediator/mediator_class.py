# -*- coding: utf-8 -*-
"""
Описывает класс посредник для взаимодействия в приложении

"""
from typing import List
from multiprocessing import Queue
from queue import Empty
import logging

from .abc_mediator_classes import MediatorMessage, Mediator, MediatorClient

logger = logging.getLogger('BotApp')


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
        self.__clients = clients
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
        for client in self.__clients:
            # проверка адресации сообщений
            if not (client.CLIENT_TYPE.value == message.component.value and \
                                message.action.value in [a.value for a in client.CLIENT_ACTIONS]):
                continue
            logger.debug('Сообщение с сервера отправлено для {}'.format(client))
            client.queue.put(message)



