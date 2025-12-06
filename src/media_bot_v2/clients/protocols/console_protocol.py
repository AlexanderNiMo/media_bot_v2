from media_bot_v2.config import Config
from media_bot_v2.database import DbManager
from media_bot_v2.parser.parser_class import get_parser_chain
from media_bot_v2.crawler.Workers import utils, TorrentSearchWorker, get_torrent_worker


class Console:

    def __init__(self, config: Config):
        self.conf = config
        self.__db_manager = None
        self.__parser = None
        self.__parser = get_parser_chain(self.conf)

    @property
    def db_manager(self)->DbManager:
        if self.__db_manager is None:
            self.__db_manager = DbManager(self.conf.db_cfg)
        return self.__db_manager

    def parse(self, data):
        return self.__parser.parse(data)
