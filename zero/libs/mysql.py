# coding=utf-8
# @Time    : 2021/7/30 10:50 上午
# @Author  : jerry
# @File    : mysql.py
from peewee import OperationalError, __exception_wrapper__
from playhouse.pool import PooledMySQLDatabase

DB_CONFIGS = dict(
    eshop={"host": "eshop.fat.mysql.jlgltech.com", "port": 3306, "user": "eshop", "password": "^8#rtg0j8$VoV29f"},
    eshop_orders={
        "host": "eshop.fat.mysql.jlgltech.com",
        "port": 3306,
        "user": "eshop_orders",
        "password": "g@hBAZ%aK1HJKL#7",
    },
    eduplatform0={
        "host": "eduplatform.fat.mysql.jlgltech.com",
        "port": 3306,
        "user": "eduplatform0",
        "password": "N0HvMFSO%yu&LTRf",
    },
    eduplatform1={
        "host": "eduplatform.fat.mysql.jlgltech.com",
        "port": 3306,
        "user": "eduplatform1",
        "password": "iCUsBQGw#5cdh2eg",
    },
)


class RetryOperationError:
    def execute_sql(self, sql, params=None, commit=True):
        try:
            cursor = super(RetryOperationError, self).execute_sql(sql, params, commit)
        except OperationalError:
            if not self.is_closed():
                self.close()
            with __exception_wrapper__:
                cursor = self.cursor()
                cursor.execute(sql, params or ())
                if commit and not self.in_transaction():
                    self.commit()
        return cursor


class AutoConnectPooledDatabase(RetryOperationError, PooledMySQLDatabase):
    pass


connection_pools = {k: None for k, v in DB_CONFIGS.items()}


def get_connect_config(db):
    """生成不同db链接配置"""
    if connection_pools[db] is None:
        connection_pools[db] = dict(DB_CONFIGS.get(db), database=db)
    return connection_pools[db]


def get_database(refresh=None, db=None):
    connection_pool = get_connect_config(db)
    conn = connection_pools[db]
    if refresh or isinstance(conn, dict):
        connection_pool = AutoConnectPooledDatabase(**connection_pools[db])
        connection_pools[db] = connection_pool
        print("*" * 10, connection_pools)
    if isinstance(conn, AutoConnectPooledDatabase) and conn.is_closed:
        connection_pool = connection_pools[db]
        print(isinstance(conn, AutoConnectPooledDatabase), conn.is_closed())
    try:
        cursor = connection_pool.execute_sql("SELECT 1")
        cursor.fetchall()
    except Exception as e:
        print(e)
        if refresh:
            return None
        connection_pool = get_database(True, db)
    return connection_pool


class MySQL:
    def __init__(self, db):
        self.db = get_database(db=db)
        print(self.db)

    def query(self, sql, args=None):
        cursor = self.db.execute_sql(sql, args)
        columns = [head[0] for head in cursor.description]
        data = cursor.fetchall()
        return [dict(zip(columns, row)) for row in data]

    def query_raw(self, sql, args=None):
        cursor = self.db.execute_sql(sql, args)
        return cursor.fetchall()

    def execute(self, sql, args=None):
        self.db.execute_sql(sql, args)
