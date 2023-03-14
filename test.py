from hackchat.bot import BotChannel, Arg
from base64 import b64encode, b64decode

channel = BotChannel(prefix='!', name='testbot')


@channel.command(
    name='encode',
    description='encode a string in base64',
    args=[Arg(name='string', description='the string to encode', required=True)]
)
async def base64encode(string: str):
    await channel.send('Encoded: {}'.format(b64encode(string.encode()).decode()))


@channel.command(
    name='decode',
    description='decode a base64 encoded string',
    args=[Arg(name='string', description='the string to decode', required=True)]
)
async def base64decode(string: str):
    await channel.send('Decoded: {}'.format(b64decode(string.encode()).decode()))


channel.join(nick='BlueBot')