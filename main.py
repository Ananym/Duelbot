import discord
from discord import app_commands
from discord.ext import commands, tasks
from game import GameState
from database_handler import db
import logging
from player_emoji import is_single_emoji
import sys
import os
from rules import rules_txt
from lobby import (
    consume_newest_challenge_for_user,
    consume_existing_challenge,
    add_new_challenge,
    cleanup_expired_challenges,
)

# https://discord.com/oauth2/authorize?client_id=1160688239577931796&permissions=2048&integration_type=0&scope=bot+applications.commands

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

ongoing_matches = {}  # {channel_id: GameState}
configured_channels = {}  # {guild_id: channel_id}

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger("main")


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user.name}")
    load_configured_channels()
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Error syncing commands: {e}")
    cleanup_task.start()


@tasks.loop(minutes=30)
async def cleanup_task():
    cleanup_expired_challenges()


def load_configured_channels():
    global configured_channels
    configured_channels = db.get_configured_channels()
    logger.info(
        f"Loaded configured channels from database: {configured_channels}")


@bot.tree.command(name="usechannel",
                  description="Set the channel for the bot to listen to")
async def use_channel(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    guild_id = interaction.guild_id
    db.set_configured_channel(guild_id, channel_id)
    configured_channels[guild_id] = channel_id
    logger.info(
        f"Updated configured channel for guild {guild_id}: {channel_id}")
    logger.info(f"Current configured channels: {configured_channels}")
    await interaction.response.send_message(
        f"Duel Bot will now listen to commands in this channel.",
        ephemeral=True)


def is_configured_channel():

    async def predicate(interaction: discord.Interaction) -> bool:
        guild_id = interaction.guild_id
        channel_id = interaction.channel_id
        configured_channel_id = configured_channels.get(guild_id)

        is_configured = channel_id == configured_channel_id

        if not is_configured:
            if configured_channel_id:
                configured_channel = interaction.guild.get_channel(
                    configured_channel_id)
                if configured_channel:
                    await interaction.response.send_message(
                        f"This command can only be used in the configured channel: {configured_channel.mention}",
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        f"This command can only be used in the configured channel (ID: {configured_channel_id}), but that channel seems to no longer exist. Please use `/usechannel` to set a new channel.",
                        ephemeral=True,
                    )
            else:
                await interaction.response.send_message(
                    "No channel has been configured for duel commands in this server. Please use `/usechannel` to set one.",
                    ephemeral=True,
                )
        return is_configured

    return app_commands.check(predicate)


async def check_configured_channel(interaction: discord.Interaction) -> bool:
    guild_id = interaction.guild_id
    channel_id = interaction.channel_id
    configured_channel_id = configured_channels.get(guild_id)

    if channel_id != configured_channel_id:
        if configured_channel_id:
            configured_channel = interaction.guild.get_channel(
                configured_channel_id)
            if configured_channel:
                await interaction.response.send_message(
                    f"This command can only be used in the configured channel: {configured_channel.mention}",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    f"This command can only be used in the configured channel (ID: {configured_channel_id}), but that channel seems to no longer exist. Please use `/usechannel` to set a new channel.",
                    ephemeral=True,
                )
        else:
            await interaction.response.send_message(
                "No channel has been configured for commands in this server. Please use `/usechannel` to set one.",
                ephemeral=True,
            )
        return False
    return True


@bot.tree.command(name="rules", description="Show the rules of the duel")
@is_configured_channel()
async def rules(interaction: discord.Interaction):
    await interaction.response.send_message(content=rules_txt, ephemeral=False)


@bot.tree.command(name="accept",
                  description="Accept your most recent challenge")
@is_configured_channel()
async def accept(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    challenge = consume_newest_challenge_for_user(interaction.user)
    if challenge:
        await interaction.response.send_message("Duel confirmed!",
                                                ephemeral=True)
        game_state = GameState(
            challenge.challenger,
            interaction.user,
            interaction.channel,
            challenge.challenge_interaction,
            interaction,
        )
        ongoing_matches[channel_id] = game_state
        await game_state.run_until_end()
        del ongoing_matches[channel_id]
    else:
        await interaction.response.send_message(
            "No unexpired challenge found - challenges expire after 30 minutes.  Use /challenge to challenge someone else!",
            ephemeral=True,
        )


@bot.tree.command(
    name="challenge",
    description=
    "Challenge another user to a samurai duel, or accept an existing challenge",
)
@is_configured_channel()
async def challenge(interaction: discord.Interaction,
                    opponent: discord.Member):
    channel_id = interaction.channel_id
    if channel_id in ongoing_matches:
        await interaction.response.send_message(
            "A game is already in progress in this channel.", ephemeral=True)
        return
    if interaction.user == opponent:
        await interaction.response.send_message(
            "You can't challenge yourself!", ephemeral=True)
        return

    challenge = consume_existing_challenge(opponent, interaction.user)
    if challenge:
        await interaction.response.send_message("Challenge accepted!",
                                                ephemeral=True)
        game_state = GameState(
            challenge.challenger,
            interaction.user,
            interaction.channel,
            challenge.challenge_interaction,
            interaction,
        )
        ongoing_matches[channel_id] = game_state
        try:
            await game_state.run_until_end()
        except Exception as e:
            logger.error(f"Error running game: {e}")
            await interaction.channel.send(
                content="Error while running duel - aborted.")
        finally:
            del ongoing_matches[channel_id]
    else:
        add_new_challenge(interaction, opponent)
        await interaction.response.send_message(
            f"{interaction.user.mention} has challenged {opponent.mention} to a samurai duel! {opponent.mention}, use /accept to accept.",
            ephemeral=False,
        )


# @bot.tree.command(name="forfeit", description="Forfeit the current game")
# @is_configured_channel()
# async def forfeit(interaction: discord.Interaction):
#     channel_id = interaction.channel_id
#     if channel_id not in ongoing_matches:
#         await interaction.response.send_message(
#             "There is no ongoing game in this channel.", ephemeral=True
#         )
#         return

#     game = ongoing_matches[channel_id]
#     if interaction.user not in [game.player1, game.player2]:
#         await interaction.response.send_message(
#             "You are not part of the ongoing game.", ephemeral=True
#         )
#         return

#     winner = game.player2 if interaction.user == game.player1 else game.player1
#     forfeit_message = f"{interaction.user.mention} has forfeited the match."

#     # Update stats
#     db_handler.update_stats(winner.id, interaction.guild.id, True)
#     db_handler.update_stats(interaction.user.id, interaction.guild.id, False)

#     # End the game
#     await game.end_game(forfeit_message)

#     # Clean up
#     del ongoing_matches[channel_id]
#     if channel_id in player_timeouts:
#         for task in player_timeouts[channel_id].values():
#             task.cancel()
#         del player_timeouts[channel_id]

#     await interaction.response.send_message(
#         "You have forfeited the game.", ephemeral=True
#     )


@bot.tree.command(name="set-emoji",
                  description="Set the emoji to be your duel champion")
async def set_emoji(interaction: discord.Interaction, emoji: str):
    await check_configured_channel(interaction)
    if not emoji or not is_single_emoji(emoji):
        await interaction.response.send_message(
            "Please provide an emoji to set as your champion.", ephemeral=True)
        return
    db.set_player_emoji(interaction.user.id, emoji)
    await interaction.response.send_message(
        f"Your champion has been set to {emoji}.", ephemeral=True)


@bot.tree.command(name="stats", description="Check your duel statistics")
async def stats(interaction: discord.Interaction):
    await check_configured_channel(interaction)
    user_stats = db.get_stats(interaction.user.id, interaction.guild.id)
    total_games = user_stats["games_played"]
    win_rate = (user_stats["wins"] / total_games *
                100) if total_games > 0 else 0

    await interaction.response.send_message(
        f"Duel Statistics for {interaction.user.mention} in {interaction.guild.name}:\n"
        f"Duels fought: {total_games}\n"
        f"Victories: {user_stats['wins']}\n"
        f"Ratio: {win_rate:.2f}%", )


bot.run(os.environ.get("DUELBOT_TOKEN"))
