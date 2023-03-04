from mysql.connector.pooling import MySQLConnectionPool
import sys
from pathlib import Path

from settings import CONFIG


class Database:
    def __init__(self):
        try:
            self.pool = MySQLConnectionPool(
                pool_name="mypool",
                pool_size=min(32, CONFIG.MAX_THREAD + 2),
                pool_reset_session=True,
                user=CONFIG.user,
                password=CONFIG.password,
                host=CONFIG.host,
                port=CONFIG.port,
                database=CONFIG.database,
            )
        except Exception as e:
            print(f"Error connecting to MariaDB Platform: {e}")
            sys.exit(1)

    def get_conn(self):
        return self.pool.get_connection()

    def select_all_from(self, table: str, condition: str = "1=1", cols: str = "*"):
        try:
            condition = condition.replace("&#39", "'")
            conn = self.get_conn()
            cur = conn.cursor()
            cur.execute(f"SELECT {cols} FROM {table} WHERE {condition}")
            res = cur.fetchall()
            cur.close()
            conn.close()

            return res
        except Exception as e:
            self.error_log(
                msg=f"Select from {table} failed\n{condition}\n{e}",
                filename="_db.select_all_from.log",
            )
            return ""

    def format_data_by_row(self, row: list) -> list:
        tmp = []
        for cell in row:
            if isinstance(cell, str):
                cell = cell.replace("&#39", "'")

            tmp.append(cell)

        return tmp

    def format_data(self, datas, is_bulk: bool = False) -> list:
        if not is_bulk:
            return self.format_data_by_row(datas)

        return [self.format_data_by_row(row) for row in datas]

    def insert_into(self, table: str, data: tuple = None, is_bulk: bool = False):
        try:
            data = self.format_data(data, is_bulk)
            conn = self.get_conn()
            cur = conn.cursor()

            columns = f"({', '.join(CONFIG.INSERT[table])})"
            values = f"({', '.join(['%s'] * len(CONFIG.INSERT[table]))})"
            query = f"INSERT INTO {table} {columns} VALUES {values}"
            if is_bulk:
                cur.executemany(query, data)
            else:
                cur.execute(query, data)

            conn.commit()
            cur.close()
            conn.close()

            id = cur.lastrowid
        except Exception as e:
            self.error_log(
                msg=f"Insert into {table} {'with is_bulk' if is_bulk else ''} failed\n{e}",
                filename="_db.insert_into.log",
            )
            id = 0

        return id

    def update_table(self, table: str, set_cond: str, where_cond: str, data: set):
        data = self.format_data(data)
        conn = self.get_conn()
        cur = conn.cursor()
        try:
            cur.execute(f"UPDATE {table} SET {set_cond} WHERE {where_cond}", data)
        except Exception as e:
            self.error_log(
                msg=f"Update {table} failed\n{set_cond}\n{where_cond}\n{data}",
                filename="_db.update_table.log",
            )
        conn.commit()
        cur.close()
        conn.close()

    def delete_from(self, table: str = "", condition: str = "1=1"):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute(f"DELETE FROM {table} WHERE {condition}")
        conn.commit()
        cur.close()
        conn.close()

    def select_or_insert(self, table: str, condition: str, data: set):
        res = self.select_all_from(table=table, condition=condition)
        if not res[0]:
            self.insert_into(table, data)
            res = self.select_all_from(table, condition=condition)
        return res

    def error_log(self, msg, filename: str = "failed.txt"):
        Path("log").mkdir(parents=True, exist_ok=True)
        with open(f"log/{filename}", "a") as f:
            print(f"{msg}\n{'-' * 80}", file=f)


database = Database()


if __name__ == "__main__":
    comicTitle = "Tit F'or Tat"
    condition = f'post_title = "{comicTitle}"'
    be_comic = database.select_all_from(
        table=f"{CONFIG.TABLE_PREFIX}posts", condition=condition
    )
    print(be_comic)
