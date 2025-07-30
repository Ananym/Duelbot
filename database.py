import sqlite3


class Database:

    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_stats (
                user_id INTEGER,
                server_id INTEGER,
                games_played INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, server_id)
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS configured_channels (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_emoji (
                player_id INTEGER PRIMARY KEY,
                emoji TEXT
            )
        """)
        self.conn.commit()

    def record_game_win(self, winning_member, losing_member):
        self.cursor.execute(
            """
            INSERT INTO game_stats (user_id, server_id, games_played, wins)
            VALUES (?, ?, 1, 1)
            ON CONFLICT (user_id, server_id) DO UPDATE SET
            games_played = games_played + 1,
            wins = wins + 1
        """,
            (
                winning_member.id,
                winning_member.guild.id,
            ),
        )

        self.cursor.execute(
            """
            INSERT INTO game_stats (user_id, server_id, games_played, wins)
            VALUES (?, ?, 1, 0)
            ON CONFLICT (user_id, server_id) DO UPDATE SET
            games_played = games_played + 1
        """,
            (
                losing_member.id,
                losing_member.guild.id,
            ),
        )
        self.conn.commit()

    def record_double_timeout(self, p1_member, p2_member):
        self.cursor.execute(
            """
            INSERT INTO game_stats (user_id, server_id, games_played, wins)
            VALUES (?, ?, 1, 0)
            ON CONFLICT (user_id, server_id) DO UPDATE SET
            games_played = games_played + 1
        """,
            (
                p1_member.id,
                p1_member.guild.id,
            ),
        )
        self.cursor.execute(
            """
            INSERT INTO game_stats (user_id, server_id, games_played, wins)
            VALUES (?, ?, 1, 0)
            ON CONFLICT (user_id, server_id) DO UPDATE SET
            games_played = games_played + 1
        """,
            (
                p2_member.id,
                p2_member.guild.id,
            ),
        )
        self.conn.commit()

    def get_player_emoji(self, player_id):
        self.cursor.execute(
            """
            SELECT emoji FROM player_emoji
            WHERE player_id = ?
        """,
            (player_id, ),
        )
        result = self.cursor.fetchone()
        if result:
            return result[0]
        return None

    def set_player_emoji(self, player_id, emoji):
        self.cursor.execute(
            """
            INSERT OR REPLACE INTO player_emoji (player_id, emoji)
            VALUES (?, ?)
        """,
            (player_id, emoji),
        )
        self.conn.commit()

    def get_stats(self, user_id, server_id):
        self.cursor.execute(
            """
            SELECT games_played, wins FROM game_stats 
            WHERE user_id = ? AND server_id = ?
        """,
            (user_id, server_id),
        )
        result = self.cursor.fetchone()
        if result:
            return {"games_played": result[0], "wins": result[1]}
        return {"games_played": 0, "wins": 0}

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
        self.cursor.execute(
            "SELECT guild_id, channel_id FROM configured_channels")
        return dict(self.cursor.fetchall())

    def close(self):
        self.conn.close()


db = Database("state.db")
