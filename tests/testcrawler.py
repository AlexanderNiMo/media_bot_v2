from unittest import TestCase, TextTestRunner, defaultTestLoader
import os

from tests.utils import TestEnvCreator

from src.mediator import CrawlerData
from src.crawler.crawler_class import Media_Task
import src


class TestCrawler(TestCase):
    def setUp(self):

        self.test_context = TestEnvCreator()
        self.test_context.construct_test_db()
        self.client_id = 1

    @property
    def conf(self):
        return self.test_context.conf

    @property
    def db(self):
        return self.test_context.db

    @property
    def crawler(self):
        return self.test_context.crawler

    def test_find_crawler(self):
        pass

    def test_download_crawler(self):
        pass

    def test_deluge_crawler(self):
        pass

    def test_add_crawler_job_check(self):

        session = self.db.get_session()

        film_id = 1
        film = self.test_context.add_test_film(
            session=session,
            client_id=self.client_id,
            kinopoisk_id=film_id,
            label='Игра',
            year=2000,
            url='torr/test',
        )
        job_CHECK = Media_Task(
            src.app_enums.ActionType.CHECK,
            self.client_id,
            film,
            CrawlerData(self.client_id, film.kinopoisk_url, film.media_type)
        )

        self.crawler.jobs.append(job_CHECK)
        self.crawler.add_workers()

        self.assertTrue(len(self.crawler.active_workers) == 1, 'Не добавился процесс воркер.')

    def tearDown(self):
        self.test_context.clear_test_db()


def suite():
    return defaultTestLoader.loadTestsFromTestCase(TestCrawler)


if __name__ == '__main__':

    testRuner = TextTestRunner()
    testRuner.run(suite())
