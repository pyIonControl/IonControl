import collections
import pickle
import sqlite3


class SQLiteLRUCache(collections.MutableMapping):
    def __init__(self, capacity, filename):
        self.cach_path = filename
        self.open_database()

    def open_database(self):
        self.cache_conn = sqlite3.connect(self.cach_path)
        c = self.cache_conn.cursor()
        c.execute("create table if not exists Store (key text, value bytes)")
        c.execute("create unique index if not exists store_index on Store(key)")
        self.cache_conn.commit()

    def __getitem__(self, key):
        c = self.cache_conn.cursor()
        c.execute("select * from Store where key=?", (key, ))
        data = c.fetchone()
        if data is None:
            raise KeyError("{} not found".format(key))
        self.cache_conn.commit()
        return pickle.loads(data[1])

    def __setitem__(self, key, value):
        c = self.cache_conn.cursor()
        c.execute("insert or replace into Store (key, value) values (?, ?)", (key, pickle.dumps(value)))
        self.cache_conn.commit()

    def __delitem__(self, key):
        c = self.cache_conn.cursor()
        c.execute("delete from Store where key=?", (key, ))
        self.cache_conn.commit()

    def __iter__(self):
        raise NotImplementedError()

    def __len__(self):
        c = self.cache_conn.cursor()
        c.execute("select count(*) from Store")
        data = c.fetchone()
        if data is None:
            raise KeyError
        self.cache_conn.commit()
        return data[0]