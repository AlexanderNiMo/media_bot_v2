

def create_app_test():
    from multiprocessing import Queue

    from scr.mediator import AppMediator, MediatorActionMessage
    from scr.app_enums import ComponentType, ActionType

    from scr.clients.protocols.bot_protocol import BotProtocol
    from scr.parser.parser_class import Parser
    from scr.crawler import Crawler
    from scr.command_handler import CommandMessageHandler
    import app.config as config

    import logging
    import time

    LOG_FILE_NAME = 'main.log'

    logger = logging.getLogger()

    consol_hndl = logging.StreamHandler()
    file_hndl = logging.FileHandler(LOG_FILE_NAME)

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

    file_hndl.setFormatter(formatter)
    consol_hndl.setFormatter(formatter)

    logger.addHandler(file_hndl)
    logger.addHandler(consol_hndl)
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

    try:
        while True:
            time.sleep(30)
            logger.debug('Проверка активности медиатора....')
            if not mediator.is_alive():
                logger.error('Медиатор умер, пеерзапускаю...')
                mediator = AppMediator(mediator_q, mediator.clients)
                mediator.start()
            mediator.check_clients()
    finally:
        file_hndl.close()

if __name__ == '__main__':

    create_app_test()

