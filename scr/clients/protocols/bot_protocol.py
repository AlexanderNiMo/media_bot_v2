
import logging
import telegram
from telegram.ext import Updater
import json

import app.config as conf
from scr.mediator import AppMediatorClient, MediatorActionMessage, parser_message
from scr.app_enums import ActionType, ComponentType, ClientCommands
from mediator import command_message
from multiprocessing import Process
import pickledb
import time
import uuid

logger = logging.getLogger(__name__)

# TODO refactor inline arguments


class BotProtocol(AppMediatorClient):

    CLIENT_TYPE = ComponentType.CLIENT
    CLIENT_ACTIONS = [ActionType.SEND_MESSAGE, ]

    def main_actions(self):
        logger.debug('Запуск основного потока работы {}'.format(self))

        bot = Bot(self.config, self.config.BOT_MODE, self)
        self.__bot = bot
        start_action = bot.get_start_bot_action()
        p = Process(target=start_action)
        p.daemon = True
        p.start()

        self.listen()

    def send_bot_message(self, text, user_id, choices=[]):
        logger.debug('Отправка сообщение {1} для пользователя {0}'.format(user_id, text))

        self.__bot.send_message(user_id, text, choices)

    def handle_message(self, message: MediatorActionMessage):
        logger.debug('Полученно новое сообщение. {}'.format(message))
        self.send_bot_message(message.data.message_text, message.data.user_id, message.data.choices)


class Bot:

    WEBHOOK_HOST = ''
    WEBHOOK_PORT = ''
    WEBHOOK_SSL_CERT = ''
    WEBHOOK_SSL_PRIV = ''
    WEBHOOK_URL_BASE = ''

    def __init__(self, config, mode, protocol: AppMediatorClient):

        for key in config.WEBHOOK.keys():
            self.__setattr__(key, config.WEBHOOK[key])

        self.token = config.TELEGRAMM_BOT_TOKEN
        self.protocol = protocol

        self.__config = config
        self.__mode = mode
        self.__bot = None
        self.__updater = None
        self.__cache = None

    def get_start_bot_action(self):
        logger.debug('Запуск бота в режиме работы {}'.format(self.__mode))
        if int(self.__mode) == 1:
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
        self.updater.start_polling()

    def send_message(self, chat_id, text, choices=[]):

        self.handle_choice(chat_id, choices)

        self.bot.send_message(chat_id=chat_id, text=text)

    def handle_choice(self, chat_id, choices):

        if len(choices) == 0:
            return

        self.send_choise_messages(chat_id, choices)

        message_text = 'Выбери номер ссылки на фильм.'
        keyboard_markup = self.constract_keyboard(choices)

        self.bot.send_message(
            chat_id=chat_id,
            text=message_text,
            reply_markup=keyboard_markup
        )

    def send_choise_messages(self, chat_id, choices):
        for i, choise in enumerate(choices):
            self.bot.send_message(
                    chat_id=chat_id,
                    text='{1} {0}'.format(choise['message_text'], i)
                )

    def constract_keyboard(self, choices)-> telegram.InlineKeyboardMarkup:

        buttons_in_row = 3
        KeyBoard = []
        row_buttons = []
        a = 1
        for i, choise in enumerate(choices):
            if a > buttons_in_row:
                KeyBoard.append(row_buttons.copy())
                a = 1
                row_buttons = []
            row_buttons.append(
                telegram.InlineKeyboardButton(
                    text=choise['button_text'],
                    callback_data=json.dumps(self.save_callback_data(choise['call_back_data']))
                )
            )

            a += 1
        if a <= buttons_in_row:
            KeyBoard.append(row_buttons.copy())

        return telegram.InlineKeyboardMarkup(KeyBoard)

    def save_callback_data(self, data):

        return self.cache.save(data)

    def get_callback_data(self, key):

        return self.cache.get(key)

    @property
    def cache(self):
        if self.__cache is None:
            self.__cache = BotCache()
        return self.__cache

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
        from telegram.ext import MessageHandler, CommandHandler, Filters, CallbackQueryHandler

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

        call_back_handler  = CallbackQueryHandler(callback=self.call_back_handler)
        dispatcher.add_handler(call_back_handler)

    @staticmethod
    def auth_handler(bot, update):
        """

        Handle autorise command for new user

        :param bot:
        :param update:
        :return:
        """
        print('New user {0}'.format(update.message.text))

    def serial_handler(self, bot, update):
        """

        Handle serial command

        :param bot:
        :param update:
        :return:

        """
        import time
        # bot.send_chat_action(chat_id=update.message.chat_id, action=TorrentBotChatAction.CHECKING_SERIAL)
        # time.sleep(7)
        logger.info('New serial {0}'.format(update.message.text))
        BotCommandParser.start_command('/serial', update.message.text, self.protocol, update.message.chat_id)

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

    def call_back_handler(self, bot, update):
        logger.debug('Пришел inline callback с данными {}'.format(update.callback_query.data))
        cache_data = self.cache.get(json.loads(update.callback_query.data))
        if cache_data is None:
            return
        parser_message(ComponentType.CLIENT, cache_data, update.message.chat_id)


class BotCache:
    """
    Класс реализует логику работы с кэшом для хранения callback данных
    """

    def __init__(self):
        self.dump_name = 'cachedb.db'
        self.base = pickledb.pickledb()
        self.stop = False
        self.base.load(self.dump_name, False)
        p_dump = Process(target=self.dumping())
        p_dump.daemon = True
        p_dump.start()

    def get(self, key):
        self.base.get(key)

    def set(self, value):
        key = uuid.uuid4()
        self.base.set(key, value)
        return key

    def dumping(self):
        while not self.stop:
            time.sleep(10)
            self.base.dump()


class BotCommandParser:
    """
    Разбирает текст сообщения на команду и данные

    """

    @classmethod
    def get_commands(cls):
        return [command['command_text'] for command in cls.message_commands()]

    @classmethod
    def start_command(cls, command: str, text: str, protocol: AppMediatorClient, chat_id: int):
        """
        Send message to command exsecuter
        :param command:
        :param text:
        :param protocol:
        :param chat_id:
        :return:
        """
        text = text.replace(command, '')
        client_command = [x['command'] for x in cls.message_commands() if x['command_text'] == command]
        client_command = client_command[0] if len(client_command) else None

        if client_command is None:
            logging.error('Wrong command for execution {0}'.format(command))
            return

        protocol.send_message(command_message(ComponentType.CLIENT, client_command, text, chat_id))

    @classmethod
    def message_commands(cls)->list:
        return [
            {'command_text': '/film', 'command': ClientCommands.ADD_FILM},
            {'command_text': '/serial', 'command': ClientCommands.ADD_SERIAL},
        ]

if __name__ == '__main__':

    from multiprocessing import Queue

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.DEBUG)

    b = Bot(conf, conf.BOT_MODE, BotProtocol(Queue(), Queue(), conf))

    a = b.get_start_bot_action()
    a()
