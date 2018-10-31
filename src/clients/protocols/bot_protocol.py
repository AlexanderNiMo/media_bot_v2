
import logging
import telegram
from telegram import error as teleg_error
from telegram.ext import Updater
import json
import re

from src.mediator import AppMediatorClient, MediatorActionMessage, parser_message
from src.app_enums import ActionType, ComponentType, ClientCommands
from src.mediator import command_message, crawler_message

from multiprocessing import Process, Queue
import threading
import pickledb
import time
import uuid

logger = logging.getLogger(__name__)


class BotProtocol(AppMediatorClient):

    CLIENT_TYPE = ComponentType.CLIENT
    CLIENT_ACTIONS = [ActionType.SEND_MESSAGE, ]

    def __init__(self, in_queue: Queue, out_queue: Queue, config):
        super(self.__class__, self).__init__(in_queue, out_queue, config)
        self.__bot = None
        self.bot_process = None
        self.t_bot_checker = None
        self.importer = None

    def main_actions(self):
        logger.debug('Запуск основного потока работы {}'.format(self))
        self.create_bot()
        self.importer = DataImporter(self.config, self.__bot)
        self.listen()

    def send_bot_message(self, text, user_id, choices=None):
        if choices is None:
            choices = []
        logger.debug('Отправка сообщение {1} для пользователя {0}'.format(user_id, text))

        self.__bot.send_message(user_id, text, choices)

    def handle_message(self, message: MediatorActionMessage):
        logger.debug('Полученно новое сообщение. {}'.format(message))
        self.send_bot_message(message.data.message_text, message.data.user_id, message.data.choices)

    def create_bot(self):
        logger.debug('Создание бота.')
        self.__bot = Bot(self.config, self.config.BOT_MODE, self)
        if self.bot_process is None:
            self.start_bot_process()
        if self.t_bot_checker is None:
            logger.debug('Запуск процесса проверки состояния бота')
            self.t_bot_checker = threading.Thread(target=self.check_bot_instanse)
            self.t_bot_checker.start()

    def start_bot_process(self):
        logger.debug('Запуск процесса прослушивания бота.')
        start_action = self.__bot.get_start_bot_action()
        self.bot_process = Process(target=start_action)
        self.bot_process.start()

    def check_bot_instanse(self):
        while True:
            time.sleep(60)
            logger.debug('Начало проверки состояния процесса bot.')
            if not self.bot_process.is_alive():
                self.start_bot_process()


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

        self.updater.start_webhook(
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

    def send_message(self, chat_id, text, choices):
        if isinstance(choices, list):
            self.handle_choice(chat_id, choices)
            self.bot.send_message(chat_id=chat_id, text=text)
        if isinstance(choices, dict):
            if choices['action'] == 'kinopoisk':
                self.handle_choice(chat_id, choices['data'])
                self.bot.send_message(chat_id=chat_id, text=text)
            elif choices['action'] == 'download_callback':
                row_buttons = [telegram.InlineKeyboardButton(
                    text='Прогресс скачивания.',
                    callback_data=self.save_callback_data(choices['data'])
                )]
                keyboard = telegram.InlineKeyboardMarkup([row_buttons])
                self.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=keyboard
                )

    def handle_choice(self, chat_id, choices):

        if len(choices) == 0:
            return

        self.send_choice_messages(chat_id, choices)

        message_text = 'Выбери номер ссылки на фильм.'
        keyboard_markup = self.construct_keyboard(choices)

        self.bot.send_message(
            chat_id=chat_id,
            text=message_text,
            reply_markup=keyboard_markup
        )

    def send_choice_messages(self, chat_id, choices):
        for i, choise in enumerate(choices):
            self.bot.send_message(
                    chat_id=chat_id,
                    text='{1} {0}'.format(choise['message_text'], i)
                )

    def construct_keyboard(self, choices)-> telegram.InlineKeyboardMarkup:

        buttons_in_row = 3
        key_board = []
        row_buttons = []
        a = 1
        for i, choise in enumerate(choices):
            if a > buttons_in_row:
                key_board.append(row_buttons.copy())
                a = 1
                row_buttons = []
            row_buttons.append(
                telegram.InlineKeyboardButton(
                    text=choise['button_text'],
                    callback_data=self.save_callback_data(choise['call_back_data'])
                )
            )

            a += 1
        if a <= buttons_in_row:
            key_board.append(row_buttons.copy())

        return telegram.InlineKeyboardMarkup(key_board)

    def save_callback_data(self, data):

        return self.cache.set(data)

    def get_callback_data(self, key):

        return self.cache.get(key)

    @property
    def cache(self):
        if self.__cache is None:
            self.__cache = BotCache(self.__config.CACHE_DB_PATH)
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

        cmd_handler = CommandHandler(
            command='notify',
            callback=self.notify_handler
        )
        dispatcher.add_handler(cmd_handler)

        call_back_handler = CallbackQueryHandler(callback=self.call_back_handler)
        dispatcher.add_handler(call_back_handler)

    def ipdater_handler(self, bot, update):

        text = update.message.text.replace('/import', '')
        text.split(':')
        (file_name, data_type, *f) = text.split(':')

        self.protocol.importer.handle_data_from_file(file_name, data_type)

    def notify_handler(self, bot, update):
        """
        Обрабатывает команду на изменение оповещений

        :param bot:
        :param update:
        :return:
        """
        logger.info('Change notification status for user {}'.format(update.message.chat_id))
        BotCommandParser.start_command(
            '/notify',
            {'option': 0},
            self.protocol,
            update.message.chat_id
        )

    @staticmethod
    def text_handler(bot, update):
        """
        Handle messages without command

        :param bot:
        :param update:
        :return:
        """
        logger.info('New message {0} from {1}'.format(update.message.text, update.message.chat_id))
        update.message.reply_text("Эээээ, чето ты хотел этим сказать?")

    def start_handler(self, bot, update):
        """
        Handle add film command

        :param bot:
        :param update:
        :return:
        """
        logger.info('New message /start from {0}'.format(update.message.chat_id))
        update.message.reply_text("Привет! Для начала авторизации набери /auth."
                                  "Для добавления фильма набери /film Название фильма год"
                                  "Для добавления сериала /serial Название сериала сезон N год"
                                  "Для включения уведомлений о новых фильмах и сериалах набери /notyfi")

    def auth_handler(self, bot, update):
        """

        Handle autorise command for new user

        :param bot:
        :param update:
        :return:
        """
        logger.info('New user {0}'.format(update.message.text))

        client_d = re.findall(r'\d{2,}', update.message.text)
        client_id = 0 if len(client_d) == 0 else client_d.pop(0)
        try:
            client_data = bot.get_chat(client_id)
            data = {
                'client_id': client_id,
                'name': client_data.first_name,
                'last_name': client_data.last_name,
                'nick': client_data.username
            }
        except teleg_error.BadRequest:
            data = {'client_id': client_id, 'name': '', 'last_name': '', 'nick': ''}

        BotCommandParser.start_command('/auth', data, self.protocol, update.message.chat_id)

    def serial_handler(self, bot, update):
        """

        Handle serial command

        :param bot:
        :param update:
        :return:

        """
        logger.info('New serial {0}'.format(update.message.text))
        text = update.message.text.replace('/serial', '')
        if not len(re.findall(r'\S', text)):
            return
        BotCommandParser.start_command(
            '/serial',
            {'text': text},
            self.protocol,
            update.message.chat_id
        )

    def film_handler(self, bot, update):
        """
        Handle add film command

        :param bot:
        :param update:
        :return:
        """
        logger.info('New film {0}'.format(update.message.text))
        text = update.message.text.replace('/film', '')
        if not len(re.findall(r'\S', text)):
            return
        BotCommandParser.start_command(
            '/film',
            {'text': text},
            self.protocol,
            update.message.chat_id)

    def call_back_handler(self, bot, update):
        logger.debug('Пришел inline callback с данными {}'.format(update.callback_query.data))
        cache_data = self.cache.get(update.callback_query.data)
        if cache_data is None:
            return
        if 'force' in cache_data.keys():
            cache_data['key_board'] = False
            message = crawler_message(ComponentType.CLIENT,
                                      update.callback_query.from_user.id,
                                      cache_data,
                                      ActionType.ADD_TORRENT_WATCHER)
        elif 'kinopoisk_id' in cache_data.keys():
            message = parser_message(ComponentType.CLIENT, cache_data, update.callback_query.from_user.id)
        else:
            return
        self.protocol.send_message(message)


class BotCache:
    """
    Класс реализует логику работы с кэшом для хранения callback данных
    """

    def __init__(self, db_path):
        self.dump_name = db_path
        self.base = MyPickledb(self.dump_name, True)

    def get(self, key):
        self.base.load(self.dump_name, True)
        return self.base.get(key)

    def set(self, value):
        key = uuid.uuid4().urn
        self.base.set(key, value)
        return key


class MyPickledb(pickledb.pickledb):

    def set_sigterm_handler(self):
        """
        Assigns sigterm_handler for graceful shutdown during dump()
        """
        pass


class BotCommandParser:
    """
    Разбирает текст сообщения на команду и данные

    """

    @classmethod
    def get_commands(cls):
        return [command['command_text'] for command in cls.message_commands()]

    @classmethod
    def start_command(cls, command: str, data: dict, protocol: AppMediatorClient, chat_id: int):
        """
        Send message to command exsecuter
        :param command:
        :param data:
        :param protocol:
        :param chat_id:
        :return:
        """

        client_command = [x['command'] for x in cls.message_commands() if x['command_text'] == command]
        client_command = client_command[0] if len(client_command) else None

        if client_command is None:
            logging.error('Wrong command for execution {0}'.format(command))
            return

        protocol.send_message(command_message(
            ComponentType.CLIENT,
            client_command,
            data,
            chat_id)
        )

    @classmethod
    def message_commands(cls)->list:
        return [
            {'command_text': '/film', 'command': ClientCommands.ADD_FILM},
            {'command_text': '/serial', 'command': ClientCommands.ADD_SERIAL},
            {'command_text': '/auth', 'command': ClientCommands.AUTHENTICATION},
        ]


class DataImporter:

    def __init__(self, config, bot):
        self.bot = bot
        self.config = config
        self.user_id = self.config.TELEGRAMM_BOT_USER_ADMIN

    def handle_data_from_file(self, file_name, data_type):
        with open(file_name, 'br') as file:
            data = file.readlines()
        self.handle_data(data, data_type)

    def handle_data(self, data, data_type):
        for text in data:
            if data_type == 'user':
                self.handle_user(text)
            elif data_type == 'film':
                self.handle_film(text)
            elif data_type == 'serial':
                self.handle_serial(text)

    def handle_user(self, user_id):
        try:
            client_data = self.bot.get_chat(user_id)
            data = {
                'client_id': self.user_id,
                'name': client_data.first_name,
                'last_name': client_data.last_name,
                'nick': client_data.username
            }
        except teleg_error.BadRequest:
            data = {'client_id': self.user_id, 'name': '', 'last_name': '', 'nick': ''}

        self.bot.protocol.send_message(command_message(
            ComponentType.CLIENT,
            ClientCommands.AUTHENTICATION,
            data,
            self.user_id)
        )

    def handle_film(self, query):
        message = command_message(
            ComponentType.CLIENT,
            ClientCommands.ADD_FILM,
            {
                'text': query
            },
            self.user_id)
        self.bot.protocol.send_message(message)

    def handle_serial(self, query):
        message = command_message(
            ComponentType.CLIENT,
            ClientCommands.ADD_SERIAL,
            {
                'text': query
            },
            self.user_id)
        self.bot.protocol.send_message(message)


if __name__ == '__main__':

    from multiprocessing import Queue
    import app.config as conf

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.DEBUG)

    b = Bot(conf, conf.BOT_MODE, BotProtocol(Queue(), Queue(), conf))

    act = b.get_start_bot_action()
    act()
