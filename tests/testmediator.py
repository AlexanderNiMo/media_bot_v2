from queue import Empty
from unittest import TestCase, TextTestRunner, defaultTestLoader
from media_bot_v2.mediator import *
from media_bot_v2.app_enums import ComponentType, ActionType

from tests.utils import TestEnvCreator


class TestMediator(TestCase):

    def setUp(self):
        self.test_content = TestEnvCreator()
        self.mediator = self.test_content.mediator
        self.test_client = self.test_content.client

    def test_send_message(self):

        msg = MediatorActionMessage(ComponentType.CLIENT, ActionType.SEND_MESSAGE, ComponentType.CLIENT)
        msg.data = ClientData(1, 'test', [])

        self.test_client.send_message(message=msg)

        try:
            messages = [self.mediator.in_queue.get(timeout=3)]
            self.assertEqual(len(messages), 1, 'Сообщение не дошло до медиатора')
        except Empty:
            self.assertTrue(False, 'Сообщение не дошло до медиатора')

        self.mediator.send_message(message=msg)

        try:
            messages = [self.test_client.queue.get(timeout=3)]
            self.assertEqual(len(messages), 1, 'Сообщение не дошло до клиента')
        except Empty:
            self.assertTrue(False, 'Сообщение не дошло до клиента')

    def tearDown(self):
        self.test_content.clear_test_db()
        print('Test end')


def suite():
    return defaultTestLoader.loadTestsFromTestCase(TestMediator)


if __name__ == '__main__':

    testRuner = TextTestRunner()
    testRuner.run(suite())
