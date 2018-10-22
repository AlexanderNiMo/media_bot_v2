from abc import ABCMeta, abstractmethod
from bs4 import BeautifulSoup
from http import cookiejar
from os import path
import re
import logging
import requests
import torrent_parser
import inspect
import sys

from app_enums import TorrentType

logger = logging.getLogger(__name__)

HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Connection': 'keep-alive',
    'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.6,en;q=0.4',
    'Accept-Encoding': 'gzip, deflate, lzma, sdch',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36',
}


class Torrent:

    def __init__(self, label, url, size, data, file_name,
                 pier, resolution, theam_url, file_amount,
                 kinopoisk_id, tracker):
        self.label = label
        self.url = url
        self.size = size
        self.theam_url = theam_url
        self.data = data
        self.file_name = file_name
        self.pier = pier
        self.resolution = resolution
        self.file_amount = file_amount
        self.kinopoisk_id = kinopoisk_id
        self.tracker = tracker

    def __repr__(self):
        return '<torrent label:{0}, pier:{3}, kinopoisk_id:{1}, files:{2}>'.format(
            self.label, self.kinopoisk_id, self.file_amount, self.pier)


class AbcTorrentTracker(metaclass=ABCMeta):

    @classmethod
    @property
    @abstractmethod
    def site_name(self):
        return ''

    @abstractmethod
    def login(self):
        pass

    @abstractmethod
    def search(self, text) -> [Torrent]:
        pass

    @abstractmethod
    def get_torrent_data(self, data):
        pass


class TorrentTracker(AbcTorrentTracker):

    def __init__(self, config):
        self.config = config
        self._connection = None
        self._cookie = None
        self._film_forums = None
        self._serial_forums = None
        self._is_loggining_in = None

    def login(self):
        return None

    def search(self, text):
        return []

    def get_connection(self):
        proxies = {
            'https': '{0}//{2}:{3}@{1}'.format(
                self.config.PROXY_URL.split('//')[0],
                self.config.PROXY_URL.split('//')[1],
                self.config.PROXY_USER,
                self.config.PROXY_PASS,
            ),
            'http': '{0}//{2}:{3}@{1}'.format(
                self.config.PROXY_URL.split('//')[0],
                self.config.PROXY_URL.split('//')[1],
                self.config.PROXY_USER,
                self.config.PROXY_PASS,
            )
        }
        session = requests.session()
        session.proxies.update(proxies)
        session.headers.update(HEADERS)
        if self.cookie is not None:
            session.cookies.update(self.cookie)
        return session

    def load_cookie(self):
        file_name = "{0}/{1}.cookies".format(self.config.TORRENT_TEMP_PATH, self.site_name)
        if not path.exists(file_name):
            return
        jar = cookiejar.LWPCookieJar(filename=file_name)
        jar.load(filename=file_name, ignore_discard=True)
        return jar

    def save_cookies(self, cookies):
        file_name = "{0}/{1}.cookies".format(self.config.TORRENT_TEMP_PATH, self.site_name)
        jar = cookiejar.LWPCookieJar(filename=file_name)
        for c in cookies:
            jar.set_cookie(c)
        jar.save()

    def close(self):
        self._connection.close()
        self._connection = None

    def normalize_size(self, size: str)-> float:
        coef = 1
        new_size = 0
        if 'MB' in size.upper():
            coef = 0.001

        result = re.search(r'\d+.\d{0,2}', size)
        if result is None:
            return 0
        new_size = result.group()

        return float(new_size) * coef

    def get_torrent_data(self, url):
        if not self._is_loggining_in:
            self.login()
        req = self.connection.get(url)
        if not req.status_code == 200:
            return None
        torr_id = re.search(r'\d+', url)
        if torr_id is None:
            torr_id = ''
        else:
            torr_id = torr_id.group()
        return {
            'data': req.content,
            'id': torr_id
            }

    def get_resolution(self, url, title):
        result = None
        resolutions = ['720', '1080']
        for res in resolutions:
            if res in title:
                result = res
                return result
        result = self.get_resolution_from_page(url)
        return result

    def get_resolution_from_page(self, url):
        pass

    def test_login_status(self):
        pass

    def get_film_forums(self):
        return ''

    def get_serial_forums(self):
        return ''

    @property
    def is_logining_in(self):
        if self._is_loggining_in is None or not self._is_loggining_in:
            self._is_loggining_in = self.test_login_status()
        return self._is_loggining_in

    @property
    def film_forums(self):
        if self._film_forums is None:
            self._film_forums = self.get_film_forums()
        return self._film_forums

    @property
    def serial_forums(self):
        if self._serial_forums is None:
            self._serial_forums = self.get_serial_forums()
        return self._serial_forums

    @property
    def connection(self):
        if self._connection is None:
            self._connection = self.get_connection()
        return self._connection

    @property
    def cookie(self):
        if self._cookie is None:
            self._cookie = self.load_cookie()
        return self._cookie

    @property
    def site_name(cls):
        return TorrentType.NONE_TYPE

    @property
    def site_domain(cls):
        return 'https://exsample.com'

    @property
    def site_download(self):
        return ''


class Rutracker(TorrentTracker):

    def login(self):
        user = self.config.TORRENTS[self.site_name]['user_name']
        password = self.config.TORRENTS[self.site_name]['password']
        if self.is_logining_in:
            return True
        login_url = 'https://rutracker.org/forum/login.php'

        login_param = dict(
            login_username=user,
            login_password=password,
            login='%E2%F5%EE%E4'
        )
        self.connection.auth = (user, password)
        req = self.connection.post(
            login_url,
            data=login_param,
            timeout=60,
            headers=HEADERS
        )

        cookies = req.cookies
        if len(req.cookies) == 0:
            for elem in req.history:
                if len(elem.cookies) > 0:
                    cookies = elem.cookies
        self.save_cookies(cookies)
        if not self.is_logining_in:
            logger.error('Не удалось залогиниться в трекере. {}'.format(self.site_name))
            return False

    def test_login_status(self):
        main_url = '{}/index.php'.format(self.site_domain)
        req = self.connection.get(main_url)
        return self.config.TORRENTS[self.site_name]['user_name'] in req.text

    def search(self, text):
        if not self.login():
            return []
        search_url = '{}/tracker.php'.format(self.site_domain)

        params = {
                'nm': text,
                'f': self.film_forums
            }

        req = self.connection.get(
            search_url,
            params=params
        )
        soup = BeautifulSoup(req.text, features='lxml')
        tr_linse = soup.find_all('tr', {'class', 'tCenter hl-tr'})
        torrents = []
        for tr_line in tr_linse:
            if not tr_line.parent.parent['class'] == ['forumline', 'tablesorter']:
                continue
            torrent = self.create_torrent(tr_line)
            if torrent is not None:
                torrents.append(torrent)
        return torrents

    def create_torrent(self, search_line)->Torrent or None:
        tor_dict = dict(
            label='', url='', size=0, data='', file_name='',
            pier=0, resolution=None, theam_url='', file_amount=0, kinopoisk_id='', tracker=''
        )
        for row in search_line.find_all('td'):
            try:
                if 't-title' in row['class']:
                    tor_dict['label'] = row.a.text
                    tor_dict['theam_url'] = '{1}/{0}'.format(row.a['href'], self.site_domain)
                elif 'tor-size' in row['class']:
                    size = self.normalize_size(row.a.text)
                    tor_dict['size'] = size
                    tor_dict['url'] = '{1}/{0}'.format(row.a['href'], self.site_domain)
                    file_name = re.search(r'\d+', row.a['href'])
                    if file_name is not None:
                        tor_dict['file_name'] = 't_{}.torrent'.format(file_name.group())
                elif row['class'] == ['row4', 'nowrap']:
                    tor_dict['pier'] = int(row.b.text)
            except AttributeError:
                return None
            except NameError:
                return None

        tor_dict['resolution'] = self.get_resolution(tor_dict['theam_url'], tor_dict['label'])
        if tor_dict['resolution'] is None:
            return None

        tor_dict['data'] = self.get_torrent_data(tor_dict['url'])

        torrent_ditails = get_torrent_details(tor_dict['data']['data'])
        if torrent_ditails is None:
            return None
        if 'files' in torrent_ditails['info'].keys():
            tor_dict['file_amount'] = len(torrent_ditails['info']['files'])
        elif 'name' in torrent_ditails['info'].keys():
            tor_dict['file_amount'] = 1
        else:
            return None
        tor_dict['kinopoisk_id'] = self.get_kinopoisk_id(tor_dict['theam_url'])

        tor_dict['tracker'] = self.site_type

        return Torrent(**tor_dict)

    def get_kinopoisk_id(self, url):
        resp = self.connection.get(url)
        soup = BeautifulSoup(resp.text, features='lxml')
        data = soup.find_all('a', {'class', 'postLink'})
        result = ''
        for elem in data:
            if 'kinopoisk.ru' in elem['href']:
                result = re.search(r'\d+', elem['href'])
                if result is not None:
                    result = result.group()
                else:
                    result = ''
        return result

    def get_resolution_from_page(self, url):
        resp = self.connection.get(url)
        if 'Видео:' not in resp.text:
            return None
        soup = BeautifulSoup(resp.text, features='lxml')
        data = soup.find_all('div', {'class', 'post_body'})
        a=1

    def _get_sub_forum(self, forum_list):
        res = []
        resp = self.connection.get('{0}{1}'.format(self.site_domain, u'/index.php'))
        soup = BeautifulSoup(resp.text, features='lxml')
        for forum in forum_list:
            forums = soup.find_all(
                'tr',
                {
                    'id': "f-{0}".format(forum)
                }
            )
            if len(forums) == 0:
                res.append(forum)
                continue
            forums = forums[0].find_all('span', {'class': 'sf_title'})
            # , /td/span[@class="nobreak"]')
            for forum_link in forums:
                try:
                    forum_number = forum_link.a['href'].split(u'=')[1]
                except IndexError:
                    continue
                res.append(forum_number)
        return res

    def get_film_forums(self):
        forum_list = [
            '2198',
            '214',
            '7',
            '22',
            '709',
            '4',
            '33'
        ]
        return u','.join(self._get_sub_forum(forum_list))

    def get_serial_forums(self):
        forum_list = [
            '189',
            '2366',
            '911',
            '2366',
            '921'
        ]
        return u','.join(self._get_sub_forum(forum_list))

    @property
    def site_type(self):
        return TorrentType.RUTRACKER

    @property
    def site_name(self):
        return 'rutracker'

    @property
    def site_domain(self):
        return 'https://rutracker.org/forum'


class Rutor(TorrentTracker):

    def login(self):
        pass

    def test_login_status(self):
        return True

    def search(self, text):
        search_url = '{0}/search/0/0/100/0/{1}'.format(self.site_domain, text)

        req = self.connection.get(
            search_url
        )
        soup = BeautifulSoup(req.text, features='lxml')
        regex = re.compile(r'gai|tum')
        tr_linse = soup.find_all('tr', {'class', regex})
        torrents = []
        for tr_line in tr_linse:
            torrent = self.create_torrent(tr_line)
            if torrent is not None:
                torrents.append(torrent)
        return torrents

    def create_torrent(self, search_line)->Torrent or None:
        tor_dict = dict(
            label='', url='', size=0, data='', file_name='', pier=0,
            resolution=None, theam_url='', file_amount=0, kinopoisk_id='', tracker=''
        )
        rows = search_line.find_all('td')
        if len(rows) == 4:
            title_num = 1
            size_num = 2
            pier_num = 3
        elif len(rows) == 5:
            title_num = 1
            size_num = 3
            pier_num = 4
        else:
            return None
        try:
            title_row = rows[title_num]

            hrefs = title_row.find_all('a')
            tor_dict['url'] = hrefs[0]['href']
            file_name = re.search(r'\d+', hrefs[0]['href'])
            if file_name is not None:
                tor_dict['file_name'] = 't_{}.torrent'.format(file_name.group())

            tor_dict['label'] = hrefs[2].text
            tor_dict['theam_url'] = '{1}/{0}'.format(hrefs[2]['href'], self.site_domain)

            size_row = rows[size_num]
            size = self.normalize_size(size_row.text)
            tor_dict['size'] = size

            pier_row = rows[pier_num]

            pier = pier_row.find_all('span', {'class', 'green'})
            for elem in pier:
                tor_dict['pier'] = int(elem.text)

        except AttributeError:
                return None
        except NameError:
                return None

        tor_dict['resolution'] = self.get_resolution(tor_dict['theam_url'], tor_dict['label'])
        if tor_dict['resolution'] is None:
            return None

        tor_dict['data'] = self.get_torrent_data(tor_dict['url'])

        torrent_ditails = get_torrent_details(tor_dict['data']['data'])
        if torrent_ditails is None:
            return None
        elif 'files' in torrent_ditails['info'].keys():
            tor_dict['file_amount'] = len(torrent_ditails['info']['files'])
        elif 'name' in torrent_ditails['info'].keys():
            tor_dict['file_amount'] = 1
        else:
            return None

        tor_dict['kinopoisk_id'] = self.get_kinopoisk_id(tor_dict['theam_url'])
        tor_dict['tracker'] = self.site_type

        return Torrent(**tor_dict)

    def get_kinopoisk_id(self, url):
        resp = self.connection.get(url)
        soup = BeautifulSoup(resp.text, features='lxml')
        data = soup.find_all('a')
        result = ''
        for elem in data:
            if 'kinopoisk.ru' in elem['href']:
                result = re.search(r'\d{3,}', elem['href'])
                if result is not None:
                    result = result.group()
                else:
                    result = ''

        return result

    @property
    def site_type(self):
        return TorrentType.RUTOR

    @property
    def site_name(self):
        return 'rutor'

    @property
    def site_domain(self):
        # http://rutor.org/search/0/0/100/0/
        return 'http://rutor.info'

    @property
    def site_download(self):
        return 'http://d.rutor.info'


def search(conf, text):
    """
    Производи поиск по трекерам по запросу
    :param conf:
    :param text:
    :return:
    """
    trackers = get_trackers(conf)
    result = []
    for tracker in trackers:
        result += tracker.search(text)

    return result


def download(conf, url):
    """
    Скачивает с трекера torrent файл

    :param conf:
    :param url:
    :return:
    """

    trackers = get_trackers(conf)
    for tracker in trackers:
        if tracker.site_domain in url or tracker.site_download   in url:
            return tracker.get_torrent_data(url)


def get_trackers(conf)->list:
    """
    Получает список классов трекеров для обработки
    :param conf:
    :return:
    """
    result = []
    mods = inspect.getmembers(
        sys.modules[__name__],
        lambda x: inspect.isclass(x) and issubclass(x, TorrentTracker)
    )
    for mod in mods:
        yield mod[1](conf)
    return result


def get_torrent_details(data):
    try:
        return torrent_parser.decode(data)
    except torrent_parser.InvalidTorrentDataException:
        return None
    except TypeError:
        return None


if __name__ == '__main__':

    logger.setLevel(logging.DEBUG)

    from app import config
    t = Rutracker(config)
    torrents = t.search('Гарри поттер')
    for torr in torrents:
        print(torr)