import requests

from media_bot_v2.config import TorrentTrackersConfig

from media_bot_v2.crawler.Workers.jasket_api import Config, Client


class Jacker:

    def __init__(self, config: TorrentTrackersConfig):
        self.config = config
        self.api = Client(Config())

    def search(self, text: str):
        return []

    def get_torrent_data(self, url: str):
        return None

