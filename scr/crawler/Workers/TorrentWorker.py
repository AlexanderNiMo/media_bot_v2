import logging
from typing import List

from .WorkerABC import Worker
from .TorrentTrackers import search, download, Torrent

logger = logging.getLogger(__name__)


class TorrentSearchWorker(Worker):

    def get_target(self):
        return self.work

    def work(self):

        data = search(self.job.text_query)
        self.returned_data = self.get_best_match(data)

    def get_best_match(self, data: List[Torrent]):
        sorted(data, key=lambda x: x.pier)
        filter(lambda x: not x.kinopoisk_id == '', data)
        filter(lambda x: not x.files_amount < 4, data)
        return data[0]

    @property
    def result(self):
        messages = []
        return messages


if __name__ == '__main__':

    t = TorrentSearchWorker({'text_query': 'Гарри поттер'})