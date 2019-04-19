from unittest import TestCase, TextTestRunner, defaultTestLoader
import os, time

from tests.utils import TestEnvCreator

from src.mediator import CrawlerData, crawler_message
from src.app_enums import ActionType, ComponentType, MediaType, ClientCommands
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

    def exec_task(self, task):

        self.crawler.jobs.append(task)
        self.crawler.add_workers()

        while len(self.crawler.active_workers) > 0:
            time.sleep(10)
            self.crawler.update_worker_status()

        return self.crawler.messages

    def test_find_crawler(self):

        film_id = 12198
        self.test_context.add_test_film(
            session=self.db.get_session(),
            client_id=self.client_id,
            kinopoisk_id=film_id,
            label='Игра',
            year=1997,
            url='https://www.kinopoisk.ru/film/12198/',
        )

        message = crawler_message(
            ComponentType.CRAWLER,
            self.client_id,
            {
                'media_id': film_id
            },
            ActionType.CHECK
        )

        messages = []
        jobs = self.crawler.db_handler.get_job_list(message)
        for job in jobs:
            messages = self.exec_task(job)

        self.assertTrue(len(messages) > 0, 'Не получен результат поиска фильма')

        upd_message = messages[0]

        upd_data_key = 'upd_data'
        dwld_url_key = 'download_url'

        self.assertTrue(
            upd_message.data.command == ClientCommands.UPDATE_MEDIA and
            upd_data_key in upd_message.data.command_data and
            dwld_url_key in upd_message.data.command_data[upd_data_key],
            'Не верный результат поиска.'
        )

        download_url = upd_message.data.command_data[upd_data_key][dwld_url_key]

        self.assertFalse(download_url == '', 'Не обновился url для фильма.')

    def test_download_crawler(self):
        film_id = 12198
        self.test_context.add_test_film(
            session=self.db.get_session(),
            client_id=self.client_id,
            kinopoisk_id=film_id,
            label='Игра',
            year=1997,
            url='https://www.kinopoisk.ru/film/12198/',
        )

        self.test_context.db.update_media_params(
            film_id,
            {'download_url': 'http://d.rutor.info/download/193221'},
            MediaType.FILMS
        )

        message = crawler_message(
            ComponentType.CRAWLER,
            self.client_id,
            {
                'media_id': film_id
            },
            ActionType.DOWNLOAD_TORRENT
        )

        messages = []
        jobs = self.crawler.db_handler.get_job_list(message)
        for job in jobs:
            messages = self.exec_task(job)

        self.assertTrue(len(messages) > 0, 'Не получен результат поиска фильма')



    def test_deluge_crawler(self):
        pass

    def test_add_crawler_job_check(self):

        film_id = 12198
        film = self.test_context.add_test_film(
            session=self.db.get_session(),
            client_id=self.client_id,
            kinopoisk_id=film_id,
            label='Игра',
            year=1997,
            url='https://www.kinopoisk.ru/film/12198/',
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
