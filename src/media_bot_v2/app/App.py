import logging
import time
from logging import LogRecord
from multiprocessing import Queue
from threading import Thread

from media_bot_v2.app.logging import configure_logger
from media_bot_v2.app_enums import ActionType, ComponentType
from media_bot_v2.clients import BotProtocol
from media_bot_v2.command_handler import CommandMessageHandler
from media_bot_v2.config import Config
from media_bot_v2.crawler import Crawler
from media_bot_v2.mediator import AppMediator, crawler_message
from media_bot_v2.parser import Parser

logger = logging.getLogger()


class TelegramBotFilter(logging.Filter):
    def filter(self, record: LogRecord) -> int:
        return "telegram" in record.processName


class MediatorMessagesFilter(logging.Filter):
    def filter(self, record: LogRecord) -> int:
        return super().filter(record)


def start_app(cfg: Config):
    file_hndlrs = configure_logger(cfg)

    mediator_q = Queue()

    clients = [
        Parser(Queue(), mediator_q, cfg),
        BotProtocol(Queue(), mediator_q, cfg),
        Crawler(Queue(), mediator_q, cfg, 10),
        CommandMessageHandler(Queue(), mediator_q, cfg),
    ]

    mediator = AppMediator(mediator_q, clients)
    mediator.start()

    for client in clients:
        client.start()
    reglament_thread = Thread(target=reglament_work, args=[mediator, cfg])
    reglament_thread.start()
    try:
        while True:
            time.sleep(30)
            if not mediator.is_alive():
                logger.error("Медиатор умер, пеерзапускаю...")
                mediator = AppMediator(mediator_q, mediator.clients)
                reglament_thread = Thread(target=reglament_work, args=[mediator, cfg])
                reglament_thread.start()
                mediator.start()
            mediator.check_clients()
    finally:
        if file_hndlrs:
            for file_hndl in file_hndlrs:
                file_hndl.close()


def reglament_work(mediator: AppMediator, config: Config):
    while True:
        if not mediator.is_alive():
            return
        mediator.send_message(
            crawler_message(
                ComponentType.MAIN_APP,
                config.db_cfg.admin_id,
                {},
                ActionType.CHECK,
            )
        )
        # time.sleep(60*60*3)
        time.sleep(60 * 60 * 3)


if __name__ == "__main__":
    start_app()
