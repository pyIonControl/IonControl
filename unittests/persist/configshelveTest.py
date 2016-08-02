# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from persist.configshelve import configshelve
import unittest

from persist.DatabaseConnectionSettings import DatabaseConnectionSettings


class ConfigshelveTest(unittest.TestCase):
    def testLoadSQLite(self):
        dbConnection = DatabaseConnectionSettings(user='python', password='yb171', database='unittests', host='localhost')
        with configshelve(dbConnection, filename='ExperimentUi.config.db') as d:
            pass

if __name__ == "__main__":
    unittest.main()