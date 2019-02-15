from unittest import TestCase, TextTestRunner, defaultTestLoader
from src.mediator import *
from src.app_enums import ComponentType, ActionType

from tests.utils import TestEnvCreator


class TestMediator(TestCase):

    def setUp(self):
        self.test_content = TestEnvCreator()
        self.test_client = self.test_content.client
        self.mediator = self.test_content.mediator

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
