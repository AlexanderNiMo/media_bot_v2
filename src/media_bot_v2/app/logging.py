from media_bot_v2.config import Config


import logging
from logging.handlers import RotatingFileHandler


def configure_logger(config: Config):

    logger = logging.getLogger()

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')

    consol_hndl = logging.StreamHandler()
    consol_hndl.setFormatter(formatter)

    logger.addHandler(consol_hndl)

    log_file_name = 'main.log'
    file_hndl = RotatingFileHandler(log_file_name, maxBytes=150000, backupCount=3)
    file_hndl.setFormatter(formatter)

    logger.addHandler(file_hndl)
    if config.log_level == 'info':
        logger.setLevel(logging.INFO)
    elif config.log_level == 'error':
        logger.setLevel(logging.ERROR)
    elif config.log_level == 'debug':
        logger.setLevel(logging.DEBUG)
        logger.addHandler(consol_hndl)

    log_file_name = 'telegramm.log'

    telegramm_logger = logging.getLogger('telegram')
    telegramm_logger.setLevel(logging.ERROR)

    file_hndl = RotatingFileHandler(log_file_name, maxBytes=150000, backupCount=1)
    file_hndl.setFormatter(formatter)

    logger.addHandler(file_hndl)
    logger = logging.getLogger('sqlalchemy.engine')
    logger.setLevel(logging.ERROR)
    info_ls = [
        'media_bot_v2.mediator.mediator_client',
        'urllib3.connectionpool',
        'media_bot_v2.parser',
        'media_bot_v2.crawler',
        'media_bot_v2.mediator'
        'media_bot_v2.command_handler.'
    ]
    for l in info_ls:
        logger = logging.getLogger(l)
        logger.setLevel(logging.INFO)
