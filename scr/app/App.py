

def create_app_test():
    from multiprocessing import Queue

    from mediator import AppMediator, MediatorActionMessage
    from app_enums import ComponentType, ActionType

    from clients.protocols.bot_protocol import BotProtocol
    from parser.parser_class import Parser
    from crawler import Crawler
    from command_handler.commandhandler_class import CommandMessageHandler
    import app.config as config

    import logging
    import time

    LOG_FILE_NAME = 'main.log'

    logger = logging.getLogger('BotApp')

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
            time.sleep(5)
            if not mediator.is_alive():
                print('Медиатор умер.')
            else:
                pass
                # Сообщение для клиента
                # message = MediatorActionMessage(
                #     action=ActionType.SEND_MESSAGE,
                #     component=ComponentType.CLIENT,
                #     from_component=ComponentType.COMMAND_HANDLER
                # )
                # mediator_q.put(message)
                # Сообщение для парсера
                # message = MediatorActionMessage(
                #     action=ActionType.PARSE,
                #     component=ComponentType.PARSER,
                #     from_component=ComponentType.COMMAND_HANDLER,
                # )
                # mediator_q.put(message)
                # #
                # # Сообщение для craulera
                # message = MediatorActionMessage(
                #     action=ActionType.FORCE_CHECK,
                #     component=ComponentType.CRAWLER,
                #     from_component=ComponentType.COMMAND_HANDLER,
                # )
                # mediator_q.put(message)
                #
                # Сообщеине для commandhandler
                # message = MediatorActionMessage(
                #     action=ActionType.HANDLE_COMMAND,
                #     component=ComponentType.COMMAND_HANDLER,
                #     from_component=ComponentType.CLIENT
                # )
                # mediator_q.put(message)
    finally:
        file_hndl.close()

if __name__ == '__main__':

    create_app_test()

