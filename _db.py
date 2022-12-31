import mysql.connector
import sys


from settings import CONFIG


class Database:
    def get_conn(self):
        try:
            return mysql.connector.connect(
                user=CONFIG.user,
                password=CONFIG.password,
                host=CONFIG.host,
                port=CONFIG.port,
                database=CONFIG.database,
            )
        except Exception as e:
            print(f"Error connecting to MariaDB Platform: {e}")
            sys.exit(1)

    def select_all_from(self, table: str, condition: str = "1=1", cols: str = "*"):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute(f"SELECT {cols} FROM {table} WHERE {condition}")
        res = cur.fetchall()
        cur.close()
        conn.close()

        return res

    def insert_into(self, table: str, data: tuple = None):
        conn = self.get_conn()
        cur = conn.cursor()

        columns = f"({', '.join(CONFIG.INSERT[table])})"
        values = f"({', '.join(['%s'] * len(CONFIG.INSERT[table]))})"
        query = f"INSERT INTO {table} {columns} VALUES {values}"
        cur.execute(query, data)
        id = cur.lastrowid

        conn.commit()
        cur.close()
        conn.close()
        return id

    def update_table(self, table: str, set_cond: str, where_cond: str, data: set):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute(f"UPDATE {table} SET {set_cond} WHERE {where_cond}", data)
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


database = Database()


if __name__ == "__main__":
    comicTitle = "kahana no shou"
    condition = f'post_title = "{comicTitle}"'
    be_comic = database.select_all_from(
        table=f"{CONFIG.TABLE_PREFIX}posts", condition=condition
    )
    print(be_comic)
