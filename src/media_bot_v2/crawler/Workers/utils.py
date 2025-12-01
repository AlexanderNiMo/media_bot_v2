from media_bot_v2.database import MediaData
from media_bot_v2.mediator import CrawlerData
from media_bot_v2.app_enums import MediaType


class MediaTask:
    """
    Описывает класс даных со всеми необходимыми
    данными для передачи в процессы воркеров

    """
    def __init__(self, action_type, client_id, media: MediaData, crawler_data: CrawlerData, **kwargs):
        self.action_type = action_type
        self.client_id = client_id
        self.media = media
        self.crawler_data = crawler_data
        self.__dict__.update(**kwargs)

    def __getattr__(self, item):
        if item in self.__dict__:
            return super(MediaTask, self).__getattribute__(item)
        else:
            return getattr(self.media, item)

    @property
    def text_query(self):
        return '{0} {1} {2}'.format(
            self.title,
            self.year,
            'сезон {}'.format(self.season) if not self.season == '' else ''
        )

    def __str__(self):
        return 'Media_task <client_id:{0} media_id:{1}>'.format(self.client_id, self.media_id)


def construct_upd_data(media: MediaTask, upd_data):
    res = {'upd_data': upd_data}
    add_media_keys(media, res)
    return res


def add_media_keys(media: MediaTask, data: dict):

    data.update({
        'media_id': media.media_id,
        'media_type': media.media_type,
    })

    if media.media_type.value == MediaType.SERIALS.value:
        season = {'season': media.season}
        data.update(season)
