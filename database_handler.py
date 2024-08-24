import sqlite3


class DatabaseHandler:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS game_stats (
                user_id INTEGER,
                server_id INTEGER,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, server_id)
            )
        """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS configured_channels (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER
            )
        """
        )
        self.conn.commit()

    def update_stats(self, user_id, server_id, is_win):
        self.cursor.execute(
            """
            INSERT INTO game_stats (user_id, server_id, wins, losses)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (user_id, server_id) DO UPDATE SET
            wins = wins + ?,
            losses = losses + ?
        """,
            (
                user_id,
                server_id,
                1 if is_win else 0,
                0 if is_win else 1,
                1 if is_win else 0,
                0 if is_win else 1,
            ),
        )
        self.conn.commit()

    def get_stats(self, user_id, server_id):
        self.cursor.execute(
            """
            SELECT wins, losses FROM game_stats
            WHERE user_id = ? AND server_id = ?
        """,
            (user_id, server_id),
        )
        result = self.cursor.fetchone()
        if result:
            return {"wins": result[0], "losses": result[1]}
        return {"wins": 0, "losses": 0}

    def set_configured_channel(self, guild_id, channel_id):
        self.cursor.execute(
            """
            INSERT OR REPLACE INTO configured_channels (guild_id, channel_id)
            VALUES (?, ?)
        """,
            (guild_id, channel_id),
        )
        self.conn.commit()

    def get_configured_channels(self):
        self.cursor.execute("SELECT guild_id, channel_id FROM configured_channels")
        return dict(self.cursor.fetchall())

    def close(self):
        self.conn.close()
