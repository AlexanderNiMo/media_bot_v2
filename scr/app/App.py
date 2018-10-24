from multiprocessing import Queue
from threading import Thread

from scr.mediator import AppMediator, MediatorActionMessage, crawler_message
from scr.app_enums import ComponentType, ActionType

from scr.clients import BotProtocol
from scr.parser import Parser
from scr.crawler import Crawler
from scr.command_handler import CommandMessageHandler
from scr.app import config

import logging
import time


def create_app_test():

    LOG_FILE_NAME = 'main.log'

    logger = logging.getLogger()

    consol_hndl = logging.StreamHandler()
    file_hndl = logging.FileHandler(LOG_FILE_NAME)

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')

    file_hndl.setFormatter(formatter)
    consol_hndl.setFormatter(formatter)

    logger.addHandler(file_hndl)
    logger.addHandler(consol_hndl)
    if config.LOGGER_LEVEL == 'info':
        logger.setLevel(logging.INFO)
    elif config.LOGGER_LEVEL == 'error':
        logger.setLevel(logging.ERROR)
    elif config.LOGGER_LEVEL == 'debug':
        logger.setLevel(logging.DEBUG)

    mediator_q = Queue()

    clients = [
        Parser(Queue(), mediator_q, config),
        BotProtocol(Queue(), mediator_q, config),
        Crawler(Queue(), mediator_q, config, 10),
        CommandMessageHandler(Queue(), mediator_q, config),
    ]

    mediator = AppMediator(mediator_q, clients)
    mediator.start()

    for client in clients:
        client.start()
    reglament_thread = Thread(target=reglament_work, args=[mediator])
    reglament_thread.start()
    try:
        while True:
            time.sleep(30)
            logger.debug('Проверка активности медиатора....')
            if not mediator.is_alive():
                logger.error('Медиатор умер, пеерзапускаю...')
                mediator = AppMediator(mediator_q, mediator.clients)
                reglament_thread = Thread(target=reglament_work, args=[mediator])
                reglament_thread.start()
                mediator.start()
            mediator.check_clients()
    finally:
        file_hndl.close()


def reglament_work(mediator: AppMediator):

    while True:
        if not mediator.is_alive():
            return
        mediator.send_message(crawler_message(
            ComponentType.MAIN_APP,
            config.TELEGRAMM_BOT_USER_ADMIN,
            {},
            ActionType.CHECK
        ))
        # time.sleep(60*60*3)
        time.sleep(60*3)


if __name__ == '__main__':

    create_app_test()

