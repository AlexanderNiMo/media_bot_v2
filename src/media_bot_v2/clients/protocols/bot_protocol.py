import json
import logging
import re
import threading
import time
import typing
import uuid
from multiprocessing import Process, Queue

import pickledb
import requests.exceptions
import telebot
from telebot import apihelper

from media_bot_v2.app_enums import (
    ActionType,
    ClientCommands,
    ComponentType,
    MediaType,
    TorrentType,
    UserOptions,
)
from media_bot_v2.config import Config, TelegrammConfig
from media_bot_v2.mediator import (
    AppMediatorClient,
    ClientData,
    MediatorActionMessage,
    command_message,
    crawler_message,
    parser_message,
)

logger = logging.getLogger(__name__)

PUBLIC_ENUMS = {
    "ActionType": ActionType,
    "ComponentType": ComponentType,
    "ClientCommands": ClientCommands,
    "UserOptions": UserOptions,
    "MediaType": MediaType,
    "TorrentType": TorrentType,
}


class BotProtocol(AppMediatorClient):
    CLIENT_TYPE = ComponentType.CLIENT
    CLIENT_ACTIONS = [
        ActionType.SEND_MESSAGE,
    ]

    def __init__(self, in_queue: Queue, out_queue: Queue, config: Config):
        super(self.__class__, self).__init__(in_queue, out_queue, config)
        self.__bot: Bot | None = None
        self.bot_process = None
        self.t_bot_checker = None
        self.importer = None

    def main_actions(self):
        logger.debug("Запуск основного потока работы {}".format(self))
        self.create_bot()
        assert self.__bot is not None
        self.importer = DataImporter(self.config, self.__bot)
        self.listen()

    def send_bot_message(self, text, user_id, choices=None):
        if choices is None:
            choices = []
        logger.debug(
            "Отправка сообщение {1} для пользователя {0}".format(user_id, text)
        )
        assert self.__bot is not None
        self.__bot.send_message(user_id, text, choices)

    def handle_message(self, message: MediatorActionMessage):
        logger.info("Полученно новое сообщение. {}".format(message))
        assert isinstance(message.data, ClientData)
        self.send_bot_message(
            message.data.message_text, message.data.user_id, message.data.choices
        )

    def create_bot(self):
        logger.debug("Создание бота.")
        self.__bot = Bot(self.config.tg_cfg, self)
        if self.bot_process is None:
            self.start_bot_process()
        if self.t_bot_checker is None:
            logger.debug("Запуск процесса проверки состояния бота")
            self.t_bot_checker = threading.Thread(target=self.check_bot_instanse)
            self.t_bot_checker.start()

    def start_bot_process(self):
        logger.debug("Запуск процесса прослушивания бота.")
        assert self.__bot is not None
        start_action = self.__bot.get_start_bot_action()
        self.bot_process = threading.Thread(target=start_action)
        self.bot_process.start()

    def check_bot_instanse(self):
        while True:
            time.sleep(60)
            if self.bot_process is None or not self.bot_process.is_alive():
                logger.error("Bot мертв, перезапускаю.")
                self.start_bot_process()


class Bot:
    def __init__(self, config: TelegrammConfig, protocol: AppMediatorClient):
        self.token = config.bot_token
        self.protocol = protocol

        self.__config: TelegrammConfig = config
        self.__mode = config.mode
        self.__bot = None
        self.__updater = None
        self.__cache = None

    def get_start_bot_action(self):
        logger.debug("Запуск бота в режиме работы {}".format(self.__mode))
        self.set_bot_handlers(None)
        return self._start_pooling

    def _start_pooling(self):
        """
        start bot using polling
        :return:
        """
        self.bot.infinity_polling()

    def send_message(self, chat_id, text, choices):
        if isinstance(choices, list):
            self.handle_choice(chat_id, choices)
            self.bot.send_message(chat_id=chat_id, text=text)
        if isinstance(choices, dict):
            if choices["action"] in ["kinopoisk", "select_torrent"]:
                self.handle_choice(chat_id, choices["data"], choices["action"])
                self.bot.send_message(chat_id=chat_id, text=text)
            elif choices["action"] == "download_callback":
                row_buttons = [
                    telebot.types.InlineKeyboardButton(
                        text="Прогресс скачивания.",
                        callback_data=self.save_callback_data(choices["data"]),
                    )
                ]
                keyboard = telebot.types.InlineKeyboardMarkup([row_buttons])
                self.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)

    def handle_choice(self, chat_id, choices, action=""):
        if len(choices) == 0:
            return

        self.send_choice_messages(chat_id, choices)
        message = ""
        if action == "kinopoisk":
            message = "Выбери номер ссылки на фильм."
        elif action == "select_torrent":
            message = "Выбери торрент."
        keyboard_markup = self.construct_keyboard(choices)

        self.bot.send_message(
            chat_id=chat_id, text=message, reply_markup=keyboard_markup
        )

    def send_choice_messages(self, chat_id, choices):
        for i, choice in enumerate(choices):
            self.bot.send_message(
                chat_id=chat_id, text="{1} {0}".format(choice["message_text"], i)
            )

    def construct_keyboard(self, choices) -> telebot.types.InlineKeyboardMarkup:
        buttons_in_row = 3
        key_board = []
        row_buttons = []
        a = 0
        for i, choise in enumerate(choices):
            if a > buttons_in_row:
                key_board.append(row_buttons.copy())
                a = 0
                row_buttons = []
            row_buttons.append(
                telebot.types.InlineKeyboardButton(
                    text=choise["button_text"],
                    callback_data=self.save_callback_data(choise["call_back_data"]),
                )
            )

            a += 1
        if a <= buttons_in_row or (len(key_board) == 0 and len(row_buttons) != 0):
            key_board.append(row_buttons.copy())

        return telebot.types.InlineKeyboardMarkup(key_board)

    def save_callback_data(self, data):
        return self.cache.set(data)

    def get_callback_data(self, key):
        return self.cache.get(key)

    @property
    def cache(self):
        if self.__cache is None:
            self.__cache = BotCache(self.__config.cache_db_path)
        return self.__cache

    @property
    def bot(self) -> telebot.TeleBot:
        if self.__bot is None:
            assert self.__config.proxy_cfg is not None
            apihelper.proxy = {
                "https": self.__config.proxy_cfg.build_proxy_str(),
                "http": self.__config.proxy_cfg.build_proxy_str(),
            }
            self.__bot = telebot.TeleBot(self.__config.bot_token, threaded=False)
        return self.__bot

    @staticmethod
    def bot_commands():
        return BotCommandParser.get_commands()

    def set_bot_handlers(self, dispatcher):
        as_handler(
            self.bot,
            callback=self.text_handler,
            func=lambda m: not m.text.startswith("/"),  # Any text, except
        )
        as_handler(self.bot, callback=self.film_handler, command=["film"])
        as_handler(self.bot, callback=self.serial_handler, command=["serial"])
        as_handler(self.bot, callback=self.auth_handler, command=["auth"])
        as_handler(self.bot, callback=self.notify_handler, command=["notify"])
        as_handler(self.bot, callback=self.start_handler, command=["start"])
        as_handler(
            self.bot,
            callback=self.send_messages_to_all_handler,
            command=["send_messages_to_all"],
        )
        as_callback_handler(self.bot, callback=self.call_back_handler)

    def updater_handler(self, bot, update):
        text = update.message.text.replace("/import", "")
        text.split(":")
        (file_name, data_type, *f) = text.split(":")

        self.protocol.importer.handle_data_from_file(file_name, data_type)

    def notify_handler(self, message: telebot.types.Message):
        """
        Обрабатывает команду на изменение оповещений

        """
        logger.info("Change notification status for user {}".format(message.chat.id))
        msg = BotCommandParser.get_command_message(
            "/notify", {"option": UserOptions.NOTIFICATION}, message.chat.id
        )
        assert msg is not None
        self.protocol.send_message(msg)

    def text_handler(self, message: telebot.types.Message):
        """
        Handle messages without command

        """
        logger.info("New message {0} from {1}".format(message.text, message.chat.id))
        self.bot.send_message(
            chat_id=message.chat.id,
            text="Эээээ, чето ты хотел этим сказать?",
            reply_to_message_id=message.message_id,
        )

    def start_handler(self, message: telebot.types.Message):
        """
        Handle add film command

        """
        logger.info("New message /start from {0}".format(message.chat.id))
        self.bot.send_message(
            chat_id=message.chat.id,
            text="Привет! Для начала авторизации набери /auth."
            "Для добавления фильма набери /film Название фильма год"
            "Для добавления сериала /serial Название сериала сезон N год"
            "Для включения уведомлений о новых фильмах и сериалах набери /notify",
            reply_to_message_id=message.message_id,
        )

    def auth_handler(self, message: telebot.types.Message):
        """

        Handle autorise command for new user

        """
        logger.info("New user {0}".format(message.text))
        assert message.text is not None
        client_d = re.findall(r"\d{2,}", message.text)
        client_id = 0 if len(client_d) == 0 else client_d.pop(0)
        try:
            client_data = self.bot.get_chat(client_id)
            data = {
                "client_id": client_id,
                "name": client_data.first_name,
                "last_name": client_data.last_name,
                "nick": client_data.username,
            }
        except Exception:
            data = {"client_id": client_id, "name": "", "last_name": "", "nick": ""}
        msg = BotCommandParser.get_command_message("/auth", data, message.chat.id)
        assert msg is not None
        self.protocol.send_message(msg)

    def serial_handler(self, message: telebot.types.Message):
        """

        Handle serial command

        """
        logger.info("New serial {0}".format(message.text))
        assert message.text is not None
        text = message.text.replace("/serial", "")
        if not len(re.findall(r"\S", text)):
            return
        msg = BotCommandParser.get_command_message(
            "/serial",
            {"text": text},
            message.chat.id,
        )
        assert msg is not None
        self.protocol.send_message(msg)

    def film_handler(self, message: telebot.types.Message):
        """
        Handle add film command

        """
        logger.info("New film {0}".format(message.text))
        assert message.text is not None
        text = message.text.replace("/film", "")
        if not len(re.findall(r"\S", text)):
            return
        msg = BotCommandParser.get_command_message(
            "/film", {"text": text}, message.chat.id
        )
        assert msg is not None
        self.protocol.send_message(msg)

    def send_messages_to_all_handler(self, message: telebot.types.Message):
        assert message.text is not None
        text = message.text.replace("/send_messages_to_all", "")
        if not len(re.findall(r"\S", text)):
            return
        msg = BotCommandParser.get_command_message(
            "/send_messages_to_all",
            {
                "message_text": text,
                "choices": [],
            },
            message.chat.id,
        )
        assert msg is not None
        self.protocol.send_message(msg)

    def call_back_handler(self, call: telebot.types.CallbackQuery):
        logger.debug("Пришел inline callback с данными {}".format(call.data))
        cache_data = self.cache.get(call.data)
        if cache_data is None:
            return
        message = BotCommandParser.get_callback_message(cache_data, call)
        if message is None:
            return
        self.protocol.send_message(message)


def as_handler(
    bot: telebot.TeleBot,
    callback: typing.Callable[[telebot.types.Message], None],
    text: str | None = None,
    command: list[str] | None = None,
    func: typing.Callable[[telebot.types.Message], bool] | None = None,
):
    def m(*a, **kv):
        print(f"In thread: ", threading.get_ident())
        callback(*a, **kv)

    bot.message_handler(
        func=func,
        commands=command,
        texy=text,
    )(m)


def as_callback_handler(
    bot: telebot.TeleBot,
    callback: typing.Callable[[telebot.types.CallbackQuery], None],
    func: typing.Callable[[telebot.types.CallbackQuery], bool] | None = None,
):
    bot.callback_query_handler(
        func=func,
    )(callback)


class BotCache:
    """
    Класс реализует логику работы с кэшом для хранения callback данных
    """

    def __init__(self, db_path):
        self.dump_name = db_path
        self.base = MyPickledb(self.dump_name)

    def get(self, key):
        return json.loads(str(self.base.get(key)), object_hook=as_enum)

    'urn:uuid:8c66f26a-8cdd-433c-baa2-dd8c0ad223f5'
    def set(self, value):
        key = uuid.uuid4().urn
        self.base.set(key, json.dumps(value, cls=EnumEncoder))
        return key


class EnumEncoder(json.JSONEncoder):
    def default(self, o):
        if type(o) in PUBLIC_ENUMS.values():
            return {"__enum__": str(o)}
        return json.JSONEncoder.default(self, o)


def as_enum(d):
    if "__enum__" in d:
        name, member = d["__enum__"].split(".")
        return getattr(PUBLIC_ENUMS[name], member)
    else:
        return d


class MyPickledb(pickledb.PickleDB):
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
        return [command["command_text"] for command in cls.message_commands()]

    @classmethod
    def get_command_message(cls, command: str, data: dict, chat_id: int):
        """
        Send message to command exsecuter
        :param command:
        :param data:
        :param chat_id:
        :return:
        """

        client_command = [
            x["command"] for x in cls.message_commands() if x["command_text"] == command
        ]
        client_command = client_command[0] if len(client_command) else None

        if client_command is None:
            logging.error("Wrong command for execution {0}".format(command))
            return

        return command_message(ComponentType.CLIENT, client_command, data, chat_id)

    @classmethod
    def get_callback_message(cls, cache_data, call: telebot.types.CallbackQuery):
        message = None
        if "force" in cache_data.keys():
            cache_data["key_board"] = False
            message = crawler_message(
                ComponentType.CLIENT,
                call.from_user.id,
                cache_data,
                ActionType.ADD_TORRENT_WATCHER,
            )
        elif "action" in cache_data.keys():
            if cache_data["action"] == "kinopoisk":
                message = parser_message(
                    ComponentType.CLIENT, cache_data, call.from_user.id
                )
            elif cache_data["action"] == "select_torrent":
                client_id = call.from_user.id
                command_data = {
                    "media_id": cache_data["media_id"],
                    "media_type": cache_data["media_type"],
                }
                upd_data = {
                    "download_url": cache_data["download_url"],
                    "theam_id": cache_data["theam_id"],
                    "torrent_tracker": cache_data["torrent_tracker"],
                }

                if cache_data["media_type"].value == MediaType.SERIALS.value:
                    season = {"season": cache_data["season"]}
                    command_data.update(season)

                command_data.update(
                    {
                        "upd_data": upd_data,
                        "next_messages": [
                            crawler_message(
                                ComponentType.CRAWLER,
                                client_id,
                                cache_data,
                                ActionType.DOWNLOAD_TORRENT,
                            )
                        ],
                    }
                )
                message = command_message(
                    ComponentType.CRAWLER,
                    ClientCommands.UPDATE_MEDIA,
                    command_data,
                    client_id,
                )
        return message

    @classmethod
    def message_commands(cls) -> list:
        return [
            {"command_text": "/film", "command": ClientCommands.ADD_FILM},
            {"command_text": "/serial", "command": ClientCommands.ADD_SERIAL},
            {"command_text": "/auth", "command": ClientCommands.AUTHENTICATION},
            {"command_text": "/notify", "command": ClientCommands.EDIT_SETTINGS},
            {
                "command_text": "/send_messages_to_all",
                "command": ClientCommands.SEND_MESSAGES_TO_ALL,
            },
        ]


class DataImporter:
    def __init__(self, cfg: Config, bot: Bot):
        self.bot = bot
        self.config: Config = cfg
        self.user_id = self.config.tg_cfg.admin_user

    def handle_data_from_file(self, file_name, data_type):
        with open(file_name, "br") as file:
            data = file.readlines()
        self.handle_data(data, data_type)

    def handle_data(self, data, data_type):
        for text in data:
            if data_type == "user":
                self.handle_user(text)
            elif data_type == "film":
                self.handle_film(text)
            elif data_type == "serial":
                self.handle_serial(text)

    def handle_user(self, user_id):
        try:
            client_data = self.bot.get_chat(user_id)
            data = {
                "client_id": self.user_id,
                "name": client_data.first_name,
                "last_name": client_data.last_name,
                "nick": client_data.username,
            }
        except requests.exceptions.HTTPError:
            data = {"client_id": self.user_id, "name": "", "last_name": "", "nick": ""}

        self.bot.protocol.send_message(
            command_message(
                ComponentType.CLIENT, ClientCommands.AUTHENTICATION, data, self.user_id
            )
        )

    def handle_film(self, query):
        message = command_message(
            ComponentType.CLIENT, ClientCommands.ADD_FILM, {"text": query}, self.user_id
        )
        self.bot.protocol.send_message(message)

    def handle_serial(self, query):
        message = command_message(
            ComponentType.CLIENT,
            ClientCommands.ADD_SERIAL,
            {"text": query},
            self.user_id,
        )
        self.bot.protocol.send_message(message)
