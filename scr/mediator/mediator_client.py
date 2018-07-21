
from multiprocessing import Queue
from queue import Empty
import logging

import app_enums
from mediator.abc_mediator_classes import MediatorClient, MediatorMessage
from mediator.mediator_types import mediator_message

logger = logging.getLogger('BotApp')


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


def command_message(
        client_from: app_enums.ComponentType,
        command: app_enums.ActionType,
        text: str,
        chat_id: str)->MediatorMessage:
    """
    Send message to command handler

    :param client_from:
    :param command:
    :param text:
    :return:
    """
    return mediator_message.CommandMessage(text, chat_id, command, client_from)

if __name__ == '__main__':

    q_in = Queue()
    q_out = Queue()

    client = AppMediatorClient(q_in, q_out)
    print(client)
