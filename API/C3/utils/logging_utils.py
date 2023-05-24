import logging
import logging.config
import os

LOG_LEVEL = 'DEBUG' if os.environ.get('DEBUG_C3') == 'dev' else 'INFO'

DICT_CONFIG = {
    'version': 1,
    'formatters': {
        'default': {
            'format':
            '%(levelname)-5s - %(module)-10s: %(funcName)s ' +
            '%(lineno)-4d - %(message)s',
        }
    },
    'handlers': {
        'stdout': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'stream': 'ext://sys.stdout',
            'level': LOG_LEVEL
        }
    },
    'root': {
        'level': LOG_LEVEL,
        'handlers': ['stdout']
    },
}


def init_logger():
    logging.config.dictConfig(DICT_CONFIG)


def get_logger(module_name):
    return logging.getLogger('root').getChild(module_name)
