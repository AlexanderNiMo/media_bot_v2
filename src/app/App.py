from logging import LogRecord
from multiprocessing import Queue
from threading import Thread

from src.mediator import AppMediator, MediatorActionMessage, crawler_message
from src.app_enums import ComponentType, ActionType

from src.clients import BotProtocol
from src.parser import Parser
from src.crawler import Crawler
from src.command_handler import CommandMessageHandler
from src.app.app_config import default_conf as config

import logging
from logging.handlers import RotatingFileHandler
import time

logger = logging.getLogger()


class TelegramBotFilter(logging.Filter):

    def filter(self, record: LogRecord) -> int:

        return 'telegram' in record.processName


class MediatorMessagesFilter(logging.Filter):

    def filter(self, record: LogRecord) -> int:
        return super().filter(record)


def configure_logger():

    file_handlers = []

    log_file_name = 'main.log'

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')

    consol_hndl = logging.StreamHandler()
    consol_hndl.setFormatter(formatter)

    logger.addHandler(consol_hndl)

    file_hndl = RotatingFileHandler(log_file_name, maxBytes=150000, backupCount=3)
    file_hndl.setFormatter(formatter)

    logger.addHandler(file_hndl)
    file_handlers.append(file_hndl)

    if config.LOGGER_LEVEL == 'info':
        logger.setLevel(logging.INFO)
    elif config.LOGGER_LEVEL == 'error':
        logger.setLevel(logging.ERROR)
    elif config.LOGGER_LEVEL == 'debug':
        logger.setLevel(logging.DEBUG)
        logger.addHandler(consol_hndl)

    log_file_name = 'telegramm.log'

    telegramm_logger = logging.getLogger('telegram')
    telegramm_logger.setLevel(logging.ERROR)

    file_hndl = RotatingFileHandler(log_file_name, maxBytes=150000, backupCount=1)
    file_hndl.setFormatter(formatter)

    logger.addHandler(file_hndl)
    file_handlers.append(file_hndl)

    return file_handlers


def create_app_test():

    file_hndlrs = configure_logger()

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
            if not mediator.is_alive():
                logger.error('Медиатор умер, пеерзапускаю...')
                mediator = AppMediator(mediator_q, mediator.clients)
                reglament_thread = Thread(target=reglament_work, args=[mediator])
                reglament_thread.start()
                mediator.start()
            mediator.check_clients()
    finally:
        for file_hndl in file_hndlrs:
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
        time.sleep(60*60*3)


if __name__ == '__main__':

    create_app_test()

