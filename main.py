import sys
from os import path
sys.path.append(path.join(path.dirname(__file__)))

print(path.join(path.dirname(__file__)))
print(sys.path)



if __name__ == '__main__':
    """
    Осуществляет тестовую сборку приложения
    """
    from src.app import create_app_test

    create_app_test()
