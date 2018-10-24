import sys
from os import path
sys.path.append(path.path.join(path.dirname(__file__), '/src'))

from scr.app import create_app_test


if __name__ == '__main__':
    """
    Осуществляет тестовую сборку приложения
    """


    create_app_test()
