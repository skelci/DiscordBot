import sqlite3
import contextlib
from contextlib import closing



class DatabaseManager:
    @contextlib.contextmanager
    def __cursor(self):
        with sqlite3.connect(self.__db_path) as conn, closing(conn.cursor()) as cur:
            yield cur
            conn.commit()

    def __init__(self, db_path='bot_database.db'):
        self.__db_path = db_path
        with self.__cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL
                );
            """)
                
            cur.execute("""
                CREATE TABLE IF NOT EXISTS lists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("""        
                CREATE TABLE IF NOT EXISTS list_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    list_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    place INTEGER NOT NULL,
                    FOREIGN KEY (list_id) REFERENCES lists(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """)

    def add_user(self, user_id, name):
        with self.__cursor() as cur:
            cur.execute("INSERT INTO users (user_id, name) VALUES (?, ?);", (user_id, name))

    def get_users(self):
        with self.__cursor() as cur:
            cur.execute("SELECT user_id, name FROM users;")
            return cur.fetchall()

    def create_list(self, name):
        with self.__cursor() as cur:
            cur.execute("INSERT INTO lists (name) VALUES (?);", (name,))

    def get_lists(self):
        with self.__cursor() as cur:
            cur.execute("SELECT id, name, created_at FROM lists ORDER BY created_at DESC;")
            return cur.fetchall()
        
    def get_list_id(self, name):
        with self.__cursor() as cur:
            cur.execute("SELECT id FROM lists WHERE name = ?;", (name,))
            result = cur.fetchone()
            return result[0] if result else None

    def add_list_entry(self, list_name, user_id, place):
        list_id = self.get_list_id(list_name)
        if list_id is None:
            raise ValueError(f"List '{list_name}' does not exist.")
        with self.__cursor() as cur:
            cur.execute("INSERT INTO list_entries (list_id, user_id, place) VALUES (?, ?, ?);", (list_id, user_id, place))

    def remove_list_entry(self, list_name, user_id):
        list_id = self.get_list_id(list_name)
        if list_id is None:
            raise ValueError(f"List '{list_name}' does not exist.")
        with self.__cursor() as cur:
            cur.execute("DELETE FROM list_entries WHERE list_id = ? AND user_id = ?;", (list_id, user_id))

    def get_list_entries(self, list_name):
        with self.__cursor() as cur:
            cur.execute("""
                SELECT u.user_id, u.name, le.place
                FROM users u
                JOIN list_entries le ON u.user_id = le.user_id
                JOIN lists l ON le.list_id = l.id
                WHERE l.name = ?;
            """, (list_name,))
            return cur.fetchall()