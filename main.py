import sys
sys.path.append('./scr')

from scr.app import create_app_test


if __name__ == '__main__':
    """
    Осуществляет тестовую сборку приложения
    """


    create_app_test()
