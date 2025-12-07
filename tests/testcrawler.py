from unittest import TestCase, TextTestRunner, defaultTestLoader
import time

from tests.utils import TestEnvCreator

from media_bot_v2.mediator import CrawlerData, crawler_message
from media_bot_v2.app_enums import ActionType, ComponentType, MediaType, ClientCommands
from media_bot_v2.crawler.Workers.utils import MediaTask


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
        job_CHECK = MediaTask(
            ActionType.CHECK,
            self.client_id,
            film,
            CrawlerData(self.client_id, film.kinopoisk_url, film.media_type)
        )

        self.crawler.jobs.append(job_CHECK)
        self.crawler.add_workers()

        self.assertTrue(len(self.crawler.active_workers) == 1, 'Не добавился процесс воркер.')

    def tearDown(self):
        self.test_context.clear_test_db()


class TestCrawlerWeb(TestCase):

    def setUp(self):

        self.test_context = TestEnvCreator()
        self.test_context.construct_test_db()
        self.client_id = 1

    @property
    def crawler(self):
        return self.test_context.crawler

    @property
    def db(self):
        return self.test_context.db

    def exec_task(self, task):

        self.crawler.jobs.append(task)
        self.crawler.add_workers()
        start = time.time()
        while len(self.crawler.active_workers) > 0:
            time.sleep(10)
            self.crawler.update_worker_status()
            if time.time() - start > 150:
                break

        return self.crawler.messages

    def test_find_film_crawler(self):

        film_id = 1053352
        self.test_context.add_test_film(
            session=self.db.get_session(),
            client_id=self.client_id,
            kinopoisk_id=film_id,
            label='Мальчик, который обуздал ветер',
            year=2019,
            url='https://www.kinopoisk.ru/film/1053352/',
        )

        message = crawler_message(
            ComponentType.CRAWLER,
            self.client_id,
            {
                'media_id': film_id,
                'media_type': MediaType.FILMS,
            },
            ActionType.CHECK
        )

        messages = []
        jobs = self.crawler.db_handler.get_job_list(message)
        for job in jobs:
            messages += self.exec_task(job)

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

    def test_find_serial_crawler(self):
        serial_id = "tt4574334"
        self.test_context.add_test_serial(
            session=self.db.get_session(),
            client_id = self.client_id,
            kinopoisk_id=serial_id,
            label='Очень странные дела',
            year=2016,
            season=1,
            series=8,
            url='https://www.kinopoisk.ru/film/915196/'
        )

        message = crawler_message(
            ComponentType.CRAWLER,
            self.client_id,
            {
                'media_id': serial_id,
                'season': 1,
                'media_type': MediaType.SERIALS
            },
            ActionType.CHECK
        )

        messages = []
        jobs = self.crawler.db_handler.get_job_list(message)
        for job in jobs:
            messages += self.exec_task(job)

        self.assertTrue(len(messages) > 0, 'Не получен результат поиска сериала')

        bot_message = messages[0]

        key = 'choices'

        ch_keys = [
            'message_text',
            'button_text',
            'call_back_data',
        ]

        self.assertTrue(
            bot_message.data.user_id == self.client_id and
            key in bot_message.data and
            bot_message.data[key]['action'] == 'select_torrent' and
            len(bot_message.data[key]['data']) > 0 and
            all(ch_key in bot_message.data[key]['data'][0] for ch_key in ch_keys),
            'Не верный результат поиска.'
        )

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
            media_id=film_id,
            upd_data={'download_url': 'https://d.rutor.info/download/193221'},
            media_type=MediaType.FILMS
        )

        message = crawler_message(
            ComponentType.CRAWLER,
            self.client_id,
            {
                'media_id': film_id,
                'media_type': MediaType.FILMS
            },
            ActionType.DOWNLOAD_TORRENT
        )

        messages = []
        jobs = self.crawler.db_handler.get_job_list(message)
        for job in jobs:
            messages = self.exec_task(job)

        self.assertTrue(len(messages) > 0, 'Не получен результат поиска фильма')

    def tearDown(self):
        self.test_context.clear_test_db()


def suite():
    return defaultTestLoader.loadTestsFromTestCase((
        TestCrawler,
        TestCrawlerWeb
    )
    )


if __name__ == '__main__':

    testRuner = TextTestRunner()
    testRuner.run(suite())
