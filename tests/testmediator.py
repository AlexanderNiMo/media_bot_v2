from unittest import TestCase, TestSuite, TextTestRunner, defaultTestLoader
from src.mediator import *
from src.app_enums import ComponentType, ActionType
from src.app import app_config as config
from multiprocessing import Queue


class TestMediator(TestCase):

    def setUp(self):
        client_quine = Queue()
        mediator_quine = Queue()
        self.test_client = AppMediatorClient(client_quine, mediator_quine, config)
        self.test_client.CLIENT_TYPE = ComponentType.MAIN_APP
        self.test_client.CLIENT_ACTIONS = [ActionType.SEND_MESSAGE]
        self.mediator = AppMediator(mediator_quine, [self.test_client])

    def test_send_message(self):

        msg = MediatorActionMessage(ComponentType.MAIN_APP, ActionType.SEND_MESSAGE, ComponentType.MAIN_APP)
        msg.data = ClientData(1, 'test', [])

        self.test_client.send_message(message=msg)
        messages = [self.mediator.in_queue.get()]
        self.assertEqual(len(messages), 1, 'Сообщение не дошло до медиатора')

        self.mediator.send_message(message=msg)
        messages = [self.test_client.queue.get()]
        self.assertEqual(len(messages), 1, 'Сообщение не дошло до клиента')

    def tearDown(self):
        print('Test end')


def suite():
    return defaultTestLoader.loadTestsFromTestCase(TestMediator)


if __name__ == '__main__':

    testRuner = TextTestRunner()
    testRuner.run(suite())
