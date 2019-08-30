from src.database import DbManager
from src.app.app_config import default_conf
from src.parser.parser_class import get_parser_chain
from src.crawler.Workers import utils, TorrentSearchWorker, get_torrent_worker


class Console:

    def __init__(self):
        self.conf = default_conf
        self.__db_manager = None
        self.__parser = None
        self.__parser = get_parser_chain(self.conf)

    @property
    def db_manager(self)->DbManager:
        if self.__db_manager is None:
            self.__db_manager = DbManager(self.conf)
        return self.__db_manager

    def parse(self, data):
        return self.__parser.parse(data)
