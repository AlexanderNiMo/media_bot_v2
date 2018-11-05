from unittest import TextTestRunner, defaultTestLoader
from tests.testmediator import TestMediator
from tests.testdb import TestDB
from tests.testparser import TestParser


def suite():
    return defaultTestLoader.loadTestsFromTestCase((TestMediator, TestDB, TestParser))


if __name__ == '__main__':
    testRuner = TextTestRunner()
    testRuner.run(suite())
