
import logging
import time
from multiprocessing import pool, Queue

from app_enums import ComponentType, ActionType
from mediator import AppMediatorClient, MediatorActionMessage

logger = logging.getLogger('BotApp')


class Crawler(AppMediatorClient):

    CLIENT_TYPE = ComponentType.CRAWLER
    CLIENT_ACTIONS = [ActionType.FORCE_CHECK, ]

    def __init__(self, in_queue: Queue, out_queue: Queue, config, threads):

        super(Crawler, self).__init__(in_queue, out_queue, config)

        self.__threads = threads

    def handle_message(self, message: MediatorActionMessage):
        logger.info('Полученно новое сообщение. {}'.format(message))
        pass

    def main_actions(self):
        logger.info('Запуск основного потока работы {}'.format(self))
        while True:
            time.sleep(10)
            self.update_jobs()

    def update_jobs(self):
        logger.info('Проверка статуса заданий.')
        pass