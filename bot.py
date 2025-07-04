import os
import sys
import discord
import requests
import asyncio
import datetime
import json
import structlog
import async_timeout
import re
from dotenv import load_dotenv
from PIL import Image
import redis.asyncio as redis

spirit_emoji_map = {
'Behemoth': 'SpiritEmberEyedBehemothEEB',
'Breath': 'SpiritBreathOfDarknessBoDDYS',
'Bringer': 'SpiritBringerDreamNightmareBoDaN',
'Downpour': 'SpiritDownpourDrenchesWorld',
'Earthquakes': 'SpiritDancesUpEarthquakesDUE',
'Earth': 'SpiritVitalStrengthEarth',
'Exploratory Bringer': 'SpiritBringerDreamNightmareBoDaN',
'Eyes': 'SpiritEyesWatchTrees',
'Fangs': 'SpiritSharpFangsLeaves',
'Finder': 'SpiritFinderPathsUnseen',
'Fractured': 'SpiritFracturedDaysSplitSky',
'Gaze': 'SpiritRelentlessGazeOfSun',
'Green': 'SpiritSpreadRampantGreen',
'Heat': 'SpiritRisingHeatStoneSand',
'Keeper': 'SpiritKeeperForbiddenWilds',
'Lightning': 'SpiritLightningSwiftStrike',
'Lure': 'SpiritLureDeepWilderness',
'Minds': 'SpiritManyMindsMoveOneMMMAO',
'Mist': 'SpiritShroudSilentMist',
'Mud': 'SpiritOtterFathomlessMud',
'Ocean': 'SpiritOceanHungryGrasp',
'River': 'SpiritRiverSurgesSunlight',
'Roots': 'SpiritToweringRoots',
'Serpent': 'SpiritSerpentSlumberingSnek',
'Shadows': 'SpiritShadowsFlickerFlame',
'Shifting': 'SpiritShiftingMemoryAges',
'Starlight': 'SpiritStarlightSeeksForm',
'Stone': 'SpiritStoneUnyieldingDefiance',
'Teeth': 'SpiritChompDevouringTeeth',
'Thunderspeaker': 'SpiritThunderspeaker',
'Trickster': 'SpiritGrinningTrickster',
'Vengeance': 'SpiritVengeanceBurningPlague',
'Vigil': 'SpiritHearthVigil',
'Voice': 'SpiritWanderingVoice',
'Volcano': 'SpiritVolcanoLoomingHigh',
'Waters': 'SpiritWoundedWaters',
'Whirlwind': 'SpiritKittySunBrightWhirlwind',
'Wildfire': 'SpiritHeartWildfire',
}

emoji_to_discord_map = {}
energy_to_discord_map = {}

load_dotenv()

if '--fake-discord' in sys.argv:
    class Client:
        class Guild:
            def __init__(self):
                self.emojis = {}

        class Channel:
            def __init__(self, id):
                self.id = id

            async def send(self, msg, file=None):
                if file:
                    print(f"send {self.id}: {msg} file: {file.filename}")
                else:
                    print(f"send {self.id}: {msg}")

        def event(self, f):
            return f

        def run(self, guild):
            print(f"fake client for {guild}")
            asyncio.run(on_ready())

        async def wait_until_ready(self):
            pass

        def get_guild(self, _):
            return self.Guild()

        def get_channel(self, id):
            return self.Channel(id)

    client = Client()
else:
    intents = discord.Intents.default()
    intents.message_content = True

    client = discord.Client(intents=intents)

LOG = structlog.get_logger()
debug = os.environ.get('DEBUG', None) == 'yes'

DISCORD_KEY = os.getenv('DISCORD_KEY')
DJANGO_HOST = os.getenv('DJANGO_HOST', 'localhost')
DJANGO_PORT = int(os.getenv('DJANGO_PORT', 8000))
GAME_URL = os.getenv('GAME_URL', 'si.bitcrafter.net')
GUILD_ID = int(os.getenv('DISCORD_GUILD_ID', 846580409050857493))
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

def combine_images(filenames):
    images = []

    for infile in filenames:
        images.append(Image.open(infile).resize((300, 420)))

    out = Image.new('RGB', (len(images)*300, 420))

    for i, img in enumerate(images):
        out.paste(img, (i*300, 0))

    out.save('out.jpg')

@client.event
async def on_ready():
    LOG.msg(f'We have logged in as {client}')
    #await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, status="a movie"))
    await asyncio.create_task(logger())

def match_game_url(s):
    """
    Match a game url returning the guid on a match.

    >>> match_game_url('https://si.bitcrafter.net/game/573a76ed-b9ed-45b1-8e14-04bfacb90a21')
    '573a76ed-b9ed-45b1-8e14-04bfacb90a21'
    >>> match_game_url('stuff')
    """
    match = re.search(GAME_URL + r'''/game/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})''', s)
    if match is not None:
        return match[1]
    return None

async def updatethings(after,topic):
    guid = match_game_url(topic)
    if guid is not None:
        LOG.msg(f'found guid: {guid}, linking to channel: {after.id}')
        r = requests.post(f'http://{DJANGO_HOST}:{DJANGO_PORT}/api/game/{guid}/link/{after.id}')
        LOG.msg(r)
        if r.status_code == 200:
            await after.send(f'Now relaying game log for {guid} to this channel. Good luck!')
        return r.status_code

@client.event
async def on_guild_channel_update(before, after):
    LOG.msg(f'channel update #{after.name}')
    if (isinstance(before, discord.TextChannel) and isinstance(after, discord.TextChannel)) or \
    (isinstance(before, discord.Thread) and isinstance(after, discord.Thread)):
        LOG.msg(f'id: {after.id}')
        LOG.msg(f'before topic: {before.topic}')
        LOG.msg(f'after  topic: {after.topic}')
        if before.topic != after.topic:
            status = await updatethings(after, after.topic)
            if status and status != 200:
                await after.send(f"Couldn't link the channel to the game ({status}). The bot owner needs to check the logs for the site API and/or bot")

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    parts = message.content.split()
    if len(parts) >= 2 and parts[0] == '$follow':
        argument = parts[1]
        status = await updatethings(message.channel, argument)
        if not status:
            await message.channel.send(f"That doesn't look like a game URL. Did you provide the full URL https://{GAME_URL}/game/abcd1234... ?")
            return
        elif status != 200:
            await message.channel.send(f"Couldn't link the channel to the game ({status}). The bot owner needs to check the logs for the site API and/or bot")
            return
        try:
            await message.pin()
        except discord.Forbidden:
            await message.channel.send("I don't have permission to pin messages, so you'll have to pin the link yourself, but I'll still relay game logs.")
        except discord.HTTPException:
            await message.channel.send("Failed to pin the message due to an HTTP error, so you'll have to pin the link yourself, but I'll still relay game logs.")
    if message.content.startswith('$help'):
        # The message starts with the specified word
        LOG.msg(f'$help called')
        text = "[Github link](<https://github.com/nathanj/spirit-island-pbp>)\
            \n\n- Use `$follow (yourgameurl)` to start\
            \n- Use `$pin` (reply to message) to pin the message"
        await message.channel.send(text)
    if message.content.startswith('$pin'):
        LOG.msg(f'$pin called')
        if not message.reference:
            await message.channel.send("You need to reply to a message to use $pin")
        else:
            message_to_pin = await message.channel.fetch_message(message.reference.message_id)
            try:
                await message_to_pin.pin()
                await message.channel.send("Message pinned!")
            except discord.Forbidden:
                await message.channel.send("I don't have permission to pin messages.")
            except discord.HTTPException:
                await message.channel.send("Failed to pin the message due to an HTTP error.")

def load_emojis():
    guild = client.get_guild(GUILD_ID)
    for e in guild.emojis:
        #LOG.msg(f'found emoji = {e.name} {str(e)}')
        if e.name in spirit_emoji_map.values():
            emoji_to_discord_map[e.name] = str(e)
        if e.name == 'Energy1':
            energy_to_discord_map[e.name] = str(e)
        if e.name == 'Energy2':
            energy_to_discord_map[e.name] = str(e)
        if e.name == 'Energy3':
            energy_to_discord_map[e.name] = str(e)
    for spirit in spirit_emoji_map:
        if spirit_emoji_map[spirit] not in emoji_to_discord_map:
            LOG.warn(f'missing emoji for {spirit}')

def adjust_msg(msg):
    try:
        for spirit in spirit_emoji_map:
            try:
                # searches for keys from spirit_emoji_map and replaces with correct Discord emoji
                # \\S+ matches the emoji representing the spirit; (.) does not successfully match ❤️
                msg = re.sub(f'^(\\S+) {spirit} ', '\\1 ' + emoji_to_discord_map[spirit_emoji_map[spirit]] + ' ', msg)
            except KeyError:
                pass
        match = re.search(r'''(\d+) energy''', msg)
        if match is not None:
            new_msg = ''
            value = int(match[1])
            while value >= 3:
                new_msg += energy_to_discord_map['Energy3']
                value -= 3
            while value >= 2:
                new_msg += energy_to_discord_map['Energy2']
                value -= 2
            while value >= 1:
                new_msg += energy_to_discord_map['Energy1']
                value -= 1
            if len(new_msg) > 0:
                msg = re.sub(r'''(\d+) energy''', new_msg, msg)
    except KeyError:
        pass
    return msg

async def relay_game(channel_id, log):
    channel = client.get_channel(channel_id)
    combined_text = []
    for entry in log:
        msg = adjust_msg(entry['text'])
        if 'images' in entry:
            if len(combined_text) > 0:
                await channel.send('\n'.join(combined_text))
                combined_text = []
            images = entry['images']
            filenames = images.split(',')
            if len(filenames) > 1:
                combine_images(filenames)
                await channel.send(msg, file=discord.File('out.jpg'))
            else:
                await channel.send(msg, file=discord.File(filenames[0]))
        else:
            combined_text.append(msg)

    if len(combined_text) > 0:
        await channel.send('\n'.join(combined_text))
        combined_text = []

# Buffer up the log so we can send a group of related log messages together.
game_log_buffer = {}

async def logger():
    await client.wait_until_ready()
    load_emojis()

    redis_obj = await redis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}", decode_responses=True)
    pubsub = redis_obj.pubsub()
    await pubsub.psubscribe("log-relay:*")

    while True:
        try:
            async with async_timeout.timeout(30):
                message = await pubsub.get_message(ignore_subscribe_messages=True)
                if message is not None:
                    LOG.msg("got message", message=message)
                    channel_id = int(message['channel'].split(':')[1])
                    if channel_id in game_log_buffer:
                        game_log_buffer[channel_id]['timestamp'] = datetime.datetime.utcnow()
                    else:
                        game_log_buffer[channel_id] = {'timestamp': datetime.datetime.utcnow(), 'logs': []}
                    game_log_buffer[channel_id]['logs'].append(json.loads(message['data']))

                keys = list(game_log_buffer.keys())
                for channel_id in keys:
                    if game_log_buffer[channel_id]['timestamp'] + datetime.timedelta(seconds=20) < datetime.datetime.utcnow():
                        LOG.msg('sending', channel_id=channel_id)
                        logs = game_log_buffer[channel_id]['logs']
                        del game_log_buffer[channel_id]
                        await relay_game(channel_id, logs)
                await asyncio.sleep(1)
        except asyncio.TimeoutError:
            LOG.msg('timeout')
            pass
        except Exception as ex:
            LOG.exception(ex)
            pass

if __name__ == '__main__':
    #combine_images(["./pbf/static/pbf/settle_into_huntinggrounds.jpg","./pbf/static/pbf/flocking_redtalons.jpg","./pbf/static/pbf/vigor_of_the_breaking_dawn.jpg","./pbf/static/pbf/vengeance_of_the_dead.jpg"])
    client.run(DISCORD_KEY)
