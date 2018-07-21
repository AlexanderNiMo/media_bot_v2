
import logging
import telegram
from telegram.ext import Updater

import app.config as conf
from scr.mediator import AppMediatorClient
from scr.app_enums import ActionType, ComponentType, ClientCommands
from mediator.mediator_types.mediator_message import ParserMessage
from mediator import command_message

logger = logging.getLogger('BotApp')
# TODO refactor inline arguments


class WebHookServer:
    """
    Server for webhook telegram bot
    """
    WEBHOOK_HOST = ''
    WEBHOOK_LISTEN = ''
    WEBHOOK_PORT = ''
    WEBHOOK_SSL_CERT = ''
    WEBHOOK_SSL_PRIV = ''
    WEBHOOK_URL_PATH = ''
    WEBHOOK_URL_BASE = ''

    def __init__(self, config, bot):
        for key in config.WEBHOOK.keys():
            self.__setattr__(key, config.WEBHOOK[key])

        self.WEBHOOK_URL_PATH = "https://{0}:{1}".format(self.WEBHOOK_HOST, self.WEBHOOK_PORT)
        self.WEBHOOK_URL_BASE = "/{}/".format(bot.token)

        updater = Updater(bot=bot.bot)
        updater.start_webhook(listen=self.WEBHOOK_HOST,
                              port=self.WEBHOOK_PORT,
                              cert=self.WEBHOOK_SSL_CERT,
                              key=self.WEBHOOK_SSL_PRIV
                              )


class BotProtocol(AppMediatorClient):

    CLIENT_TYPE = ComponentType.CLIENT
    CLIENT_ACTIONS = [ActionType.SEND_MESSAGE, ]

    def main_actions(self):
        logger.debug('Запуск основного потока работы {}'.format(self))

        bot = Bot(self.config, 1, self)

        self.__bot = bot

        start_action = bot.get_start_bot_action()
        start_action()

    def send_bot_message(self, text, user_id, choices=[]):
        logger.debug('Отправка сообщение {1} для пользователя {0} новое сообщение в {}'.format(user_id, text))
        if not len(choices):
            self.__bot.send_message(user_id, text)
        else:
            pass

    def handle_message(self, message):
        logger.debug('Полученно новое сообщение. {}'.format(message))
        self.send_bot_message(message.data['text'], message.data['chst_id'], message.data['choices'])


class Bot:

    WEBHOOK_HOST = ''
    WEBHOOK_PORT = ''
    WEBHOOK_SSL_CERT = ''
    WEBHOOK_SSL_PRIV = ''
    WEBHOOK_URL_BASE = ''

    def __init__(self, config, mode, protocol:AppMediatorClient):

        for key in config.WEBHOOK.keys():
            self.__setattr__(key, config.WEBHOOK[key])

        self.__config = config
        self.token = config.TELEGRAMM_BOT_TOKEN
        self.__mode = mode
        self.protocol = protocol
        self.__bot = None
        self.__updater = None

    def get_start_bot_action(self):
        logger.debug('Запуск бота в режиме работы {}'.format(self.__mode))
        if self.__mode == 1:
            return self._start_webhook_server
        else:
            return self._start_pooling

    def _start_webhook_server(self):
        """
        start bot using webhook
        :return:
        """

        url_path = 'TOKEN'

        upd_q = self.updater.start_webhook(
            listen=self.WEBHOOK_HOST,
            port=self.WEBHOOK_PORT,
            url_path=url_path
        )

        self.updater.bot.set_webhook(
            url='{0}/{1}'.format(self.WEBHOOK_URL_BASE, url_path),
            certificate=open(self.WEBHOOK_SSL_CERT, 'rb')
        )
        self.updater.idle()

    def _start_pooling(self):
        """
        start bot using polling
        :return:
        """
        self.__updater = telegram.ext.Updater(bot=self.bot)
        self.__updater.start_polling()

    def send_message(self, chat_id, text):
        self.__bot.send_message(chat_id=chat_id, text=text)

    @property
    def updater(self):
        if self.__updater is None:
            r_kw = {
                'proxy_url': self.__config.PROXY_URL,
                'urllib3_proxy_kwargs': {"username": self.__config.PROXY_USER, "password": self.__config.PROXY_PASS}
            }
            self.__updater = telegram.ext.Updater(token=self.token, request_kwargs=r_kw)
            self.set_bot_hendlers(self.__updater.dispatcher)

        return self.__updater

    @property
    def bot(self):
        if self.__bot is None:
            self.__bot = self.updater.bot
        return self.__bot

    @staticmethod
    def bot_commands():
        return BotCommandParser.get_commands()

    def set_bot_hendlers(self, dispatcher):
        from telegram.ext import MessageHandler, CommandHandler, Filters

        message_handler = MessageHandler(
            filters=Filters.text,
            callback=self.text_handler
        )
        dispatcher.add_handler(message_handler)

        cmd_handler = CommandHandler(
            command='film',
            callback=self.film_handler
        )
        dispatcher.add_handler(cmd_handler)

        cmd_handler = CommandHandler(
            command='serial',
            callback=self.serial_handler
        )
        dispatcher.add_handler(cmd_handler)

        cmd_handler = CommandHandler(
            command='auth',
            callback=self.auth_handler
        )
        dispatcher.add_handler(cmd_handler)

    @staticmethod
    def auth_handler(bot, update):
        """

        Handle autorise command for new user

        :param bot:
        :param update:
        :return:
        """
        print('New user {0}'.format(update.message.text))

    @staticmethod
    def serial_handler(bot, update):
        """

        Handle serial command

        :param bot:
        :param update:
        :return:

        """
        import time
        # bot.send_chat_action(chat_id=update.message.chat_id, action=TorrentBotChatAction.CHECKING_SERIAL)
        # time.sleep(7)
        print('New serial {0}'.format(update.message.text))

    def film_handler(self, bot, update):
        """
        Handle add film command

        :param bot:
        :param update:
        :return:
        """
        logger.info('New film {0}'.format(update.message.text))
        BotCommandParser.start_command('/film', update.message.text, self.protocol, update.message.chat_id)

    @staticmethod
    def text_handler(bot, update):
        """
        Handle messages without command

        :param bot:
        :param update:
        :return:
        """
        update.message.reply_text("Эээээ, чето ты хотел этим сказать?")


class BotCommandParser:
    """
    Разбирает текст сообщения на команду и данные

    """

    @classmethod
    def get_commands(cls):
        return [command['command_text'] for command in cls.message_commands()]

    @classmethod
    def start_command(cls, command: str, text: str, protocol: AppMediatorClient, chat_id: str):
        """
        Send message to command exsecuter
        :param command:
        :param text:
        :param protocol:
        :return:
        """
        text = text.replace(command, '')
        client_command = [x['command'] for x in cls.message_commands() if x['command_text'] == command]
        client_command = client_command[0] if len(client_command) else None

        if client_command is None:
            logging.error('Wrong command for execution {0}'.format(command))
            return

        protocol.send_message(command_message(ComponentType.CLIENT, client_command, text, chat_id))

        pass

    def construct_command_message(self, text: str, user_id: str):

        command_type = None
        message_text = text
        for command in self.message_commands():
            if text.find(command['command_text']):
                command_type, message_text = command['command'], text.replace(command['command_text'])
                break

        return ParserMessage(message_text, user_id, command_type, ComponentType.CLIENT)

    @classmethod
    def message_commands(cls)->list:
        return [
            {'command_text': '/film', 'command': ClientCommands.ADD_FILM},
            {'command_text': '/serial', 'command': ClientCommands.ADD_SERIAL},
        ]

if __name__ == '__main__':

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

    b = Bot(conf, 1)

    a = b.get_start_bot_action()
    a()
