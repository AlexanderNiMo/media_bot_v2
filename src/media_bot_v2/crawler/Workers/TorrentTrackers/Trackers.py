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
from time import sleep

from media_bot_v2.app_enums import TorrentType
from media_bot_v2.config import TorrentTrackersConfig
from .jasket_tracker import Jacker

logger = logging.getLogger(__name__)

HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Proxy-Connection': 'keep-alive',
    'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.6,en;q=0.4',
    'Accept-Encoding': 'gzip, deflate, lzma, sdch',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36',

}


class Torrent:

    def __init__(self, label, url, size, data, file_name,
                 pier, resolution, theam_url, file_amount,
                 kinopoisk_id, tracker, sound, sub, with_advertising=False):
        self.label = label
        self.url = url
        self.size = size
        self.theam_url = theam_url
        self.data = data
        self.file_name = file_name
        self.pier = pier
        self.resolution = resolution
        self.file_amount = file_amount
        self.kinopoisk_id = int(kinopoisk_id) if not kinopoisk_id == '' else 0
        self.tracker = tracker
        self.sound = sound
        self.sub = sub
        self.with_advertising = with_advertising

    def __repr__(self):
        return '<torrent label:{0}, pier:{3}, kinopoisk_id:{1}, files:{2}>'.format(
            self.label, self.kinopoisk_id, self.file_amount, self.pier)


class AbcTorrentTracker(metaclass=ABCMeta):

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

    def __init__(self, config: TorrentTrackersConfig):
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
            'https': self.config.proxy_cfg.build_proxy_str(),
            'http': self.config.proxy_cfg.build_proxy_str()
        }
        session = requests.session()
        session.proxies.update(proxies)
        session.headers.update(HEADERS)
        if self.cookie is not None:
            session.cookies.update(self.cookie)
        return session

    def load_cookie(self):
        file_name = "{0}/{1}.cookies".format(self.config.tmp_path, self.site_name)
        if not path.exists(file_name):
            return
        jar = cookiejar.LWPCookieJar(filename=file_name)
        jar.load(filename=file_name, ignore_discard=True)
        return jar

    def save_cookies(self, cookies):
        file_name = "{0}/{1}.cookies".format(self.config.tmp_path, self.site_name)
        jar = cookiejar.LWPCookieJar(filename=file_name)
        for c in cookies:
            jar.set_cookie(c)
        jar.save()

    def close(self):
        self._connection.close()
        self._connection = None

    @staticmethod
    def normalize_size(size: str) -> float:
        coef = 1
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
        req.raise_for_status()
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

    def get_resolution(self, page_soup, title):
        resolutions = ['720', '1080']
        for res in resolutions:
            if res in title:
                result = res
                return result
        result = self.get_resolution_from_page(page_soup)
        return result

    def get_resolution_from_page(self, page_soup):
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
        sleep(0.5)
        if self._connection is None:
            self._connection = self.get_connection()
        return self._connection

    @property
    def cookie(self):
        if self._cookie is None:
            self._cookie = self.load_cookie()
        return self._cookie

    @property
    def site_name(self):
        return TorrentType.NONE_TYPE

    @property
    def site_domain(self):
        return 'https://exsample.com'

    @property
    def site_download(self):
        return ''


class Rutracker(TorrentTracker):

    def login(self):
        user = self.config.credentials[self.site_name].user_name
        password = self.config.credentials[self.site_name].password
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
        return self.config.credentials[self.site_name].user_name in req.text

    def search(self, text):
        if not self.login():
            return []
        search_url = '{}/tracker.php'.format(self.site_domain)

        forums = self.film_forums
        if re.search(r'сезон', text) is not None:
            forums = self.serial_forums

        params = {
            'nm': text,
            'f': forums
        }

        req = self.connection.get(
            search_url,
            params=params
        )
        soup = BeautifulSoup(req.content.decode(req.encoding), features='lxml')
        reg = re.compile('tCenter hl-tr')
        tr_linse = soup.find_all('tr', {'class': reg})
        torrents = []
        for tr_line in tr_linse:
            if not tr_line.parent.parent['class'] == ['forumline', 'tablesorter']:
                continue
            torrent = self.create_torrent(tr_line)
            if torrent is not None:
                torrents.append(torrent)
        return torrents

    def create_torrent(self, search_line) -> Torrent or None:
        tor_dict = dict(
            label='', url='', size=0, data='', file_name='',
            pier=0, resolution=None, theam_url='', file_amount=0, kinopoisk_id='', tracker='',
            sound=[], sub=[]
        )
        for row in search_line.find_all('td'):
            try:
                if 't-title-col' in row['class']:
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
        resp = self.connection.get(tor_dict['theam_url'])
        theam_soup = BeautifulSoup(resp.text, features='lxml')

        tor_dict['resolution'] = self.get_resolution(theam_soup, tor_dict['label'])
        if tor_dict['resolution'] is None:
            return None

        tor_dict['kinopoisk_id'] = self.get_kinopoisk_id(theam_soup)

        tor_dict['tracker'] = self.site_type

        return Torrent(**tor_dict)

    def get_kinopoisk_id(self, soup):
        data = soup.find_all('a', {'class', 'postLink'})
        result = ''
        for elem in data:
            if 'www.imdb.com' in elem['href']:
                result = re.search(r'\d+', elem['href'])
                if result is not None:
                    result = result.group()
                else:
                    result = ''
                break
        return result

    def get_resolution_from_page(self, page_soup):
        pass

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
            '2100',
            '921',
            '9'
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

        search_url = '{0}/search/0/0/100/0/{1}'.format(self.site_domain, self.prepare_query(text))

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

    def create_torrent(self, search_line) -> Torrent or None:
        tor_dict = dict(
            label='', url='', size=0, data='', file_name='',
            pier=0, resolution=None, theam_url='', file_amount=0, kinopoisk_id='', tracker='',
            sound=[], sub=[], with_advertising=False
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

        resp = self.connection.get(tor_dict['theam_url'])
        theam_soup = BeautifulSoup(resp.text, features='lxml')

        tor_dict['resolution'] = self.get_resolution(theam_soup, tor_dict['label'])
        if tor_dict['resolution'] is None:
            return None

        tor_dict['kinopoisk_id'] = self.get_kinopoisk_id(theam_soup)
        tor_dict['tracker'] = self.site_type

        details = theam_soup.select('#details')
        if len(details) > 0:
            details = details[0].text

            sounds_re = re.findall(r'^(Language|Язык)\s*:\s*(\w*).*$', details, re.MULTILINE)
            for s_re in sounds_re:
                tor_dict['sound'].append(s_re[1].upper())

            sub = re.findall(r'^Субтитры\s*: (\w*).*$', details, re.MULTILINE)
            for s_re in sub:
                tor_dict['sub'].append(s_re.upper())
            tor_dict['with_advertising'] = 'реклама'.upper() in details.upper()

        return Torrent(**tor_dict)

    def get_kinopoisk_id(self, soup):
        data = soup.find_all('a')
        result = ''
        for elem in data:
            if 'www.imdb.com' in elem['href']:
                result = re.search(r'\d{3,}', elem['href'])
                if result is not None:
                    result = result.group()
                else:
                    result = ''
                break

        return result

    def prepare_query(self, text: str):
        data = re.search(r'(СЕЗОН)\s+(\d{1,2})', text, re.IGNORECASE)

        if data is None:
            return text

        season = data.group(2) if len(data.group(2)) == 2 else f'0{data.group(2)}'
        return text.replace(data.group(), f'S{season}')

    @property
    def site_type(self):
        return TorrentType.RUTOR

    @property
    def site_name(self):
        return 'rutor'

    @property
    def site_domain(self):
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
    logger.debug(f'Начало поиска по запросу {text}')

    trackers = get_trackers(conf)
    result = []
    for tracker in trackers:
        try:
            result += tracker.search(text)
        except Exception as ex:
            logger.error(f'При поиске по трекеру {tracker.site_name} произошла ошибка: {ex}')
    return result


def download(conf, _url):
    """
    Скачивает с трекера torrent файл

    :param conf:
    :param url:
    :return:
    """
    url = fix_shema(_url)
    trackers = get_trackers(conf)
    for tracker in trackers:
        if tracker.site_domain in url or tracker.site_download in url:
            data = get_torrent_details(tracker.get_torrent_data(url))
            return data


def fix_shema(url):
    if url.startswith('//'):
        return f'https:{url}'
    if not 'https://' in url:
        return 'https://{url}'
    return url


def get_trackers(conf: TorrentTrackersConfig) -> list:
    """
    Получает список классов трекеров для обработки
    :param conf:
    :return:
    """
    return [
        # Jacker(conf)
        Rutor(conf),
        Rutracker(conf),
    ]


def get_torrent_details(data_dict):

    try:
        torrent_ditails = torrent_parser.decode(data_dict['data'])
    except torrent_parser.InvalidTorrentDataException:
        torrent_ditails = None
    except TypeError:
        torrent_ditails = None

    file_amount = 0

    if torrent_ditails is None:
        file_amount = 0
        torrent_ditails = {}

    elif 'files' in torrent_ditails['info'].keys():
        file_amount = len([i for i in torrent_ditails['info']['files'] if get_ext(i.get('path')[-1]) in media_ext()])
    elif 'name' in torrent_ditails['info'].keys():
        file_amount = 1
    torrent_ditails.update({'file_amount': file_amount})
    torrent_ditails.update(data_dict)

    return torrent_ditails


def get_ext(path):
    path_part = path.split('.')
    return path_part[-1]


def media_ext():
    return [
        '3g2',
        '3gp',
        '3gp2',
        '3gpp',
        'avi',
        'dat',
        'drv',
        'f4v',
        'flv',
        'gtp',
        'h264',
        'm4v',
        'mkv',
        'mod',
        'moov',
        'mov',
        'mp4',
        'mpeg',
        'mpg',
        'mts',
        'rmvb',
        'spl',
        'stl',
        'ts',
        'vcd',
        'vid',
        'vid',
        'vid',
        'vob',
        'webm',
        'wmv',
        'yuv',
    ]
