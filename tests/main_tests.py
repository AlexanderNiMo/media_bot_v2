from unittest import TextTestRunner, defaultTestLoader
from tests.testmediator import TestMediator
from tests.testdb import TestDB
from tests.testparser import TestParser
from tests.testcrawler import TestCrawler


def suite():
    return defaultTestLoader.loadTestsFromTestCase((TestMediator, TestDB, TestParser, TestCrawler))


if __name__ == '__main__':
    testRuner = TextTestRunner()
    testRuner.run(suite())
