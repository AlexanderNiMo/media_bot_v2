from unittest import TestCase, TestSuite, TextTestRunner, defaultTestLoader
from multiprocessing import Queue
import os
from subprocess import Popen

from src.mediator import CrawlerData
from src.database import DbManager, MediaData
from src.crawler import Crawler
from src.crawler.crawler_class import Job
import src


class TestCrawler(TestCase):
    def setUp(self):
        client_quine = Queue()
        mediator_quine = Queue()

        self.conf = src.app.app_config.default_conf
        self.conf.set_config_file(os.path.abspath('./test_config.ini'))
        self.conf.TEST = True

        self.component = src.app_enums.ComponentType.MAIN_APP
        self.db = DbManager(self.conf)
        self.client_id = 1
        self.crawler = Crawler(client_quine, mediator_quine, self.conf, 10)

    def add_test_film(self, session, **kwargs):
        return self.db.add_film(session=session, **kwargs)

    def add_test_serial(self, session, **kwargs):
        return self.db.add_serial(session=session, **kwargs)

    def test_add_crawler_job(self):

        session = self.db.get_session()

        film_id = 1
        film = self.add_test_film(
            session=session,
            client_id=self.client_id,
            kinopoisk_id=film_id,
            label='Игра',
            year=2000,
            url='torr/test',
        )
        job_CHECK = Job(
            src.app_enums.ActionType.CHECK,
            self.client_id,
            film,
            CrawlerData(self.client_id, film.kinopoisk_url, film.media_type)
        )

        self.crawler.jobs.append(job_CHECK)
        self.crawler.add_workers()

        self.assertTrue(len(self.crawler.active_workers) == 1, 'Не добавился процесс воркер.')

    def tearDown(self):
        db_path = '.test.db'
        if os.path.exists(db_path):
            os.remove(db_path)


def suite():
    return defaultTestLoader.loadTestsFromTestCase(TestCrawler)


if __name__ == '__main__':

    testRuner = TextTestRunner()
    testRuner.run(suite())
