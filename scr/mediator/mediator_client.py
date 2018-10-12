
from multiprocessing import Queue
from queue import Empty
import logging

import app_enums
from mediator.abc_mediator_classes import MediatorClient, MediatorMessage
from mediator.mediator_types import mediator_message

logger = logging.getLogger(__name__)


class AppMediatorClient(MediatorClient):
    
    def __init__(self, in_queue: Queue, out_queue: Queue, config):
        
        super(AppMediatorClient, self).__init__()

        self.__in_queue = in_queue
        self.__out_queue = out_queue
        self.__config = config
        self.__listening_thread = None
        logger.debug('Создание клиента {}'.format(self.CLIENT_TYPE))

    def run(self):
        import threading

        logger.debug('Запуск клиента {}'.format(self.CLIENT_TYPE))

        self.__listening_thread = threading.Thread(target=self.listen)
        self.__listening_thread.start()

        self.main_actions()

    def listen(self):
        logger.debug('Клиент {} готов к приему сообщений.'.format(self.CLIENT_TYPE))
        while True:
            try:
                self.handle_message(self.queue.get())
            except Empty:
                pass
            except Exception as ex:
                logger.error('Error while listning for new message! {}'.format(ex))

    def send_message(self, message: MediatorMessage):
        logger.debug('Отправка сообщения. {}'.format(message))
        self.__out_queue.put(message)

    def handle_message(self, message: MediatorMessage):
        logger.debug('Полученно новое сообщение. {}'.format(message))
        pass

    def main_actions(self):
        logger.debug('Запуск основного потока работы {}'.format(self.CLIENT_TYPE))
        pass

    @property
    def config(self):
        return self.__config

    @property
    def queue(self)-> Queue:
        return self.__in_queue

    def __str__(self):
        return '{} {}'.format(self.CLIENT_TYPE, ' '.join(str(action) for action in self.CLIENT_ACTIONS))


def parser_message(
        client_from: app_enums.ComponentType,
        data: dict,
        client_id: int)->MediatorMessage:

    """
    send message to parser


    :param client_from:
    :param data:
    :param client_id:
    :return:
    """

    message = mediator_message.MediatorActionMessage(app_enums.ComponentType.PARSER,
                                                     app_enums.ActionType.PARSE,
                                                     client_from)

    message.data = mediator_message.ParserData(data, client_id)

    return message


def command_message(
        client_from: app_enums.ComponentType,
        command: app_enums.ClientCommands,
        command_data: dict,
        client_id: int)->MediatorMessage:
    """
    Send message to command handler

    :param client_from:
    :param command:
    :param command_data:
    :param client_id:
    :return:
    """

    message = mediator_message.MediatorActionMessage(app_enums.ComponentType.COMMAND_HANDLER,
                                                     app_enums.ActionType.HANDLE_COMMAND,
                                                     client_from)

    message.data = mediator_message.CommandData(command_data, client_id, command)

    return message


def send_message(
        client_from: app_enums.ComponentType,
        message_data: dict)->MediatorMessage:
    """
    Send message to command handler

    :param client_from:
    :param message_data: dict :{user_id, message_text, choices}
    :return:
    """

    message = mediator_message.MediatorActionMessage(
        app_enums.ComponentType.CLIENT,
        app_enums.ActionType.SEND_MESSAGE,
        client_from)

    message.data = mediator_message.ClientData(**message_data)

    return message


def crawler_message(
        client_from: app_enums.ComponentType,
        media_id: int=0)->MediatorMessage:
    """
    Send message to crawler
    :param client_from:
    :param media_id:
    :return:
    """

    message = mediator_message.MediatorActionMessage(
        app_enums.ComponentType.CRAWLER,
        app_enums.ActionType.FORCE_CHECK,
        client_from)

    message.data = mediator_message.CrawlerData(media_id)

    return message

if __name__ == '__main__':

    q_in = Queue()
    q_out = Queue()

    client = AppMediatorClient(q_in, q_out)
    print(client)
