import logging
from .WorkerABC import Worker

logger = logging.getLogger(__name__)


class DownloadWorker(Worker):
    def get_target(self):
        return self.work

    def work(self):
        logger.debug('Start torrent worker.')

    @property
    def result(self):
        return []