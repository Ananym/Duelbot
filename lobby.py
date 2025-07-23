from datetime import datetime, timedelta
import uuid
from dataclasses import dataclass
import discord
from typing import Dict, TypeAlias

challenge_validity = timedelta(minutes=30)


@dataclass
class Challenge:
    challenger: discord.Member
    opponent: discord.Member
    dt: datetime
    challenge_id: uuid.UUID
    challenge_interaction: discord.Interaction

    def __init__(
        self,
        challenger: discord.Member,
        opponent: discord.Member,
        challenge_interaction: discord.Interaction,
    ):
        self.challenger = challenger
        self.challenge_interaction = challenge_interaction
        self.opponent = opponent
        self.dt = datetime.now()
        self.challenge_id = uuid.uuid4()

    def is_expired(self):
        return self.dt + challenge_validity < datetime.now()

    def __lt__(self, other):
        if not isinstance(other, Challenge):
            return NotImplemented
        # return newest
        return self.dt > other.dt


# data structures
ChallengerDict: TypeAlias = Dict[
    str, Challenge]  # Dict of challenger IDs to Challenge objects
MemberDict: TypeAlias = Dict[
    str, ChallengerDict]  # Dict of member IDs to ChallengerDict
ServerDict: TypeAlias = Dict[str,
                             MemberDict]  # Dict of channel IDs to MemberDict

lobby: ServerDict = dict()


def find_existing_challenge(challenger: discord.Member,
                            opponent: discord.Member):
    server_id = challenger.guild.id
    try:
        challenge = lobby[server_id][opponent.id][challenger.id]
        if challenge.is_expired():
            raise KeyError
        return True
    except KeyError:
        return False


def consume_existing_challenge(challenger: discord.Member,
                               opponent: discord.Member):
    server_id = challenger.guild.id
    try:
        challenge = lobby[server_id][opponent.id][challenger.id]
        if challenge.is_expired():
            raise KeyError
        del lobby[server_id][opponent.id][challenger.id]
        return True
    except KeyError:
        return None


def add_new_challenge(challenge_interaction: discord.Interaction,
                      opponent: discord.Member):
    server_id = challenge_interaction.guild.id
    challenger = challenge_interaction.user
    if server_id not in lobby:
        lobby[server_id] = {}
    if opponent.id not in lobby[server_id]:
        lobby[server_id][opponent.id] = {}
    lobby[server_id][opponent.id][challenger.id] = Challenge(
        challenger, opponent, challenge_interaction)


def consume_newest_challenge_for_user(user: discord.Member):
    server_id = user.guild.id
    if server_id not in lobby:
        return None
    # find the [server][opponent] dict and fetch all the challenge objects inside
    # determine the newest one by sorting them
    # remove it from the dict and return it
    challenger_dict = lobby[server_id][user.id]
    if not challenger_dict or len(challenger_dict) == 0:
        return None
    challenges = [
        c for c in list(challenger_dict.values()) if not c.is_expired()
    ]
    challenges.sort()
    challenge = challenges[0]
    challenger_id = challenge.challenger.id
    del lobby[server_id][user.id][challenger_id]
    return challenge


def cleanup_expired_challenges():
    expired_challenges = []
    
    for server_id, member_dict in lobby.items():
        for opponent_id, challenger_dict in member_dict.items():
            for challenger_id, challenge in challenger_dict.items():
                if challenge.is_expired():
                    expired_challenges.append((server_id, opponent_id, challenger_id))
    
    for server_id, opponent_id, challenger_id in expired_challenges:
        if (server_id in lobby and 
            opponent_id in lobby[server_id] and 
            challenger_id in lobby[server_id][opponent_id]):
            del lobby[server_id][opponent_id][challenger_id]
