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
                    next_in_line INTEGER DEFAULT 1,
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

            cur.execute("""
                CREATE TABLE IF NOT EXISTS learning_lists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS learning_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    list_id INTEGER NOT NULL,
                    word_eng TEXT NOT NULL,
                    word_slo TEXT NOT NULL,
                    FOREIGN KEY (list_id) REFERENCES learning_lists(id) ON DELETE CASCADE
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_learning_progress (
                    user_id INTEGER NOT NULL,
                    word_id INTEGER NOT NULL,
                    score REAL DEFAULT 1.0,
                    PRIMARY KEY (user_id, word_id),
                    FOREIGN KEY (word_id) REFERENCES learning_words(id) ON DELETE CASCADE
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_learning_state (
                    user_id INTEGER PRIMARY KEY,
                    current_list_id INTEGER,
                    FOREIGN KEY (current_list_id) REFERENCES learning_lists(id) ON DELETE SET NULL
                );
            """)

    def add_user(self, user_id, name):
        with self.__cursor() as cur:
            cur.execute("INSERT INTO users (user_id, name) VALUES (?, ?);", (user_id, name))

    def get_users(self):
        with self.__cursor() as cur:
            cur.execute("SELECT user_id, name FROM users ORDER BY name;")
            return cur.fetchall()
        
    def remove_user(self, user_id):
        with self.__cursor() as cur:
            cur.execute("DELETE FROM users WHERE user_id = ?;", (user_id,))

    def create_list(self, name):
        with self.__cursor() as cur:
            cur.execute("INSERT INTO lists (name) VALUES (?);", (name,))

    def get_lists(self):
        with self.__cursor() as cur:
            cur.execute("SELECT id, name, next_in_line, created_at FROM lists ORDER BY created_at DESC;")
            return cur.fetchall()

    def get_list(self, name):
        with self.__cursor() as cur:
            cur.execute("SELECT id, name, next_in_line, created_at FROM lists WHERE name = ?;", (name,))
            return cur.fetchone()
        
    def set_next_in_line(self, list_name, place):
        with self.__cursor() as cur:
            if place == -1:
                place = self.get_list(list_name)[2] + 1
            cur.execute("UPDATE lists SET next_in_line = ? WHERE name = ?;", (place, list_name))
        
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

    def swap_list_entries(self, list_name, user1_id, user2_id):
        list_id = self.get_list_id(list_name)
        if list_id is None:
            raise ValueError(f"List '{list_name}' does not exist.")
        
        with self.__cursor() as cur:
            # Get places
            cur.execute("SELECT place FROM list_entries WHERE list_id = ? AND user_id = ?;", (list_id, user1_id))
            res1 = cur.fetchone()
            if not res1:
                raise ValueError(f"User with ID {user1_id} is not in list '{list_name}'.")
            place1 = res1[0]
            
            cur.execute("SELECT place FROM list_entries WHERE list_id = ? AND user_id = ?;", (list_id, user2_id))
            res2 = cur.fetchone()
            if not res2:
                raise ValueError(f"User with ID {user2_id} is not in list '{list_name}'.")
            place2 = res2[0]

            # Swap
            cur.execute("UPDATE list_entries SET place = ? WHERE list_id = ? AND user_id = ?;", (place2, list_id, user1_id))
            cur.execute("UPDATE list_entries SET place = ? WHERE list_id = ? AND user_id = ?;", (place1, list_id, user2_id))

    # Learning System Methods

    def create_learning_list(self, name):
        with self.__cursor() as cur:
            cur.execute("INSERT INTO learning_lists (name) VALUES (?);", (name,))

    def get_learning_lists(self):
        with self.__cursor() as cur:
            cur.execute("SELECT name FROM learning_lists ORDER BY created_at DESC;")
            return [row[0] for row in cur.fetchall()]

    def get_learning_list_id(self, name):
        with self.__cursor() as cur:
            cur.execute("SELECT id FROM learning_lists WHERE name = ?;", (name,))
            res = cur.fetchone()
            return res[0] if res else None

    def add_learning_word(self, list_name, eng, slo):
        list_id = self.get_learning_list_id(list_name)
        if not list_id:
            raise ValueError(f"Learning list '{list_name}' does not exist.")
        with self.__cursor() as cur:
            cur.execute("INSERT INTO learning_words (list_id, word_eng, word_slo) VALUES (?, ?, ?);", (list_id, eng, slo))

    def add_learning_words_bulk(self, list_name, words):
        # words is strictly a list of tuples (eng, slo)
        list_id = self.get_learning_list_id(list_name)
        if not list_id:
            raise ValueError(f"Learning list '{list_name}' does not exist.")
        
        with self.__cursor() as cur:
            cur.executemany("INSERT INTO learning_words (list_id, word_eng, word_slo) VALUES (?, ?, ?);", 
                            [(list_id, w[0], w[1]) for w in words])

    def clear_learning_list(self, list_name):
        list_id = self.get_learning_list_id(list_name)
        if not list_id:
            raise ValueError(f"Learning list '{list_name}' does not exist.")
        
        with self.__cursor() as cur:
            cur.execute("DELETE FROM learning_words WHERE list_id = ?;", (list_id,))

    def set_user_learning_list(self, user_id, list_name):
        list_id = self.get_learning_list_id(list_name)
        if not list_id:
             raise ValueError(f"Learning list '{list_name}' does not exist.")
        
        with self.__cursor() as cur:
            cur.execute("INSERT INTO user_learning_state (user_id, current_list_id) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET current_list_id = ?;", (user_id, list_id, list_id))

    def get_user_learning_list(self, user_id):
        with self.__cursor() as cur:
            cur.execute("""
                SELECT ll.name 
                FROM user_learning_state uls
                JOIN learning_lists ll ON uls.current_list_id = ll.id
                WHERE uls.user_id = ?;
            """, (user_id,))
            res = cur.fetchone()
            return res[0] if res else None

    def get_learning_words_with_scores(self, user_id, list_name):
        with self.__cursor() as cur:
            cur.execute("""
                SELECT lw.id, lw.word_eng, lw.word_slo, IFNULL(ulp.score, 1.0)
                FROM learning_words lw
                JOIN learning_lists ll ON lw.list_id = ll.id
                LEFT JOIN user_learning_progress ulp ON lw.id = ulp.word_id AND ulp.user_id = ?
                WHERE ll.name = ?;
            """, (user_id, list_name))
            return cur.fetchall()

    def update_word_score(self, user_id, word_id, new_score):
        with self.__cursor() as cur:
            cur.execute("INSERT INTO user_learning_progress (user_id, word_id, score) VALUES (?, ?, ?) ON CONFLICT(user_id, word_id) DO UPDATE SET score = ?;", (user_id, word_id, new_score, new_score))

    def get_learning_words(self, list_name):
        with self.__cursor() as cur:
            cur.execute("""
                SELECT lw.word_eng, lw.word_slo
                FROM learning_words lw
                JOIN learning_lists ll ON lw.list_id = ll.id
                WHERE ll.name = ?;
            """, (list_name,))
            return cur.fetchall()

    def get_learning_leaderboard(self, list_name):
        with self.__cursor() as cur:
            cur.execute("""
                SELECT ulp.user_id, u.name, SUM(1.0 / ulp.score) as total_score
                FROM user_learning_progress ulp
                JOIN learning_words lw ON ulp.word_id = lw.id
                JOIN learning_lists ll ON lw.list_id = ll.id
                LEFT JOIN users u ON ulp.user_id = u.user_id
                WHERE ll.name = ?
                GROUP BY ulp.user_id
                ORDER BY total_score DESC;
            """, (list_name,))
            return cur.fetchall()

    def update_learning_word(self, list_name, current_word, new_eng=None, new_slo=None):
        list_id = self.get_learning_list_id(list_name)
        if not list_id:
            raise ValueError(f"Learning list '{list_name}' does not exist.")
        
        with self.__cursor() as cur:
            # Try to find by eng or slo
            cur.execute("SELECT id, word_eng, word_slo FROM learning_words WHERE list_id = ? AND (word_eng = ? OR word_slo = ?);", (list_id, current_word, current_word))
            rows = cur.fetchall()
            
            if not rows:
                raise ValueError(f"Word '{current_word}' not found in list '{list_name}'.")
            if len(rows) > 1:
                # Ambiguous match (e.g., same word in both languages or duplicates)
                raise ValueError(f"Multiple entries match '{current_word}' in list '{list_name}'. Please be more specific.")
            
            word_id, old_eng, old_slo = rows[0]
            
            final_eng = new_eng if new_eng is not None else old_eng
            final_slo = new_slo if new_slo is not None else old_slo
            
            cur.execute("UPDATE learning_words SET word_eng = ?, word_slo = ? WHERE id = ?;", (final_eng, final_slo, word_id))
            return final_eng, final_slo
