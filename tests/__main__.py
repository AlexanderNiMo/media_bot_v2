import logging

from unittest import TextTestRunner, defaultTestLoader, main
from unittest.suite import TestSuite

from tests.testmediator import TestMediator
from tests.testdb import TestDB
from tests.testparser import TestParser
from tests.testcrawler import TestCrawler, TestCrawlerWeb
from tests.testclient import TestClientCache, TestCommandParser
from tests.testcommandhandler import TestCommandHandler


def setup_logging():
    root = logging.getLogger("root")
    root.setLevel(logging.DEBUG)
    root.addHandler(logging.StreamHandler())

    logger = logging.getLogger('sqlalchemy.engine')
    logger.setLevel(logging.DEBUG)


def suite():
    setup_logging()
    return defaultTestLoader.loadTestsFromTestCase(
        TestSuite(
            tests=(
                TestMediator(),
                TestDB(),
                TestParser(),
                TestCrawler(),
                TestCommandHandler(),
                # TestCrawlerWeb(),
                TestClientCache(),
                TestCommandParser()
            )
        )
    )


if __name__ == '__main__':
    main()    
