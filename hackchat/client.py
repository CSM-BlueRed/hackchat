from .constants import *

import aiohttp
import asyncio
import typing as t


__version__ = '1.0'
__author__ = 'BlueRed'
__license__ = 'MIT'
__all__ = ['User', 'Message', 'Channel', 'RateLimit']



class RateLimit(Exception):
    pass



class User:
    """
    An hack.chat channel member.

    Attributes  name  type   description
                nick  (str)  the nickname of the member
                id    (int)  the userid that is used by the hack.chat internal API
    """
    
    def __init__(self, nick: str, id: int) -> None:
        self.nick = nick
        self.id = id


    def __str__(self) -> str:
        return self.nick


    def __repr__(self) -> str:
        return f'<User {self.nick!r} id={self.id}>'



class Message:
    """
    A message that is sent in a channel.

    Attributes  name     type                description
                channel  (hackchat.Channel)  the channel where the message is
                author   (hackchat.User)     the author of the message
                content  (str)               the message himself
    """

    def __init__(self, channel: 'Channel', author: User, content: str) -> None:
        self.channel = channel
        self.author = author
        self.content = content


    def __str__(self) -> str:
        return self.content


    def __repr__(self) -> str:
        return f'<Message author={self.author.nick!r} channel={self.channel.name!r} {self.content!r}>'



class Channel:
    """
    A hack.chat channel.

    Attributes  name     type                                 description
                name     (str)                                the name of the channel
                loop     (asyncio.AbstractEventLoop)          the async loop
                session  (aiohttp.ClientSession)              the HTTP session where the websocket is created
                client   (aiohttp.ClientWebSocketResponse)    the websocket connection
                members  (list[hackchat.User])                the online members of the channel
                events   (dict[str, hackchat.EventCallback])  the events that will be dispatched
    """

    def __init__(self, name: str, loop: asyncio.AbstractEventLoop | None = None) -> None:
        self.name = name
        self.loop = loop or asyncio.get_event_loop()

        self.session = aiohttp.ClientSession(
            loop=self.loop,
            headers={
                'User-Agent': f'HackChat/{__version__}'
            }
        )

        self.client: aiohttp.ClientWebSocketResponse | None = None
        self.user: User | None = None
        self.members: list[User] = []
        self.events: dict[str, EventCallback] = {}


    def __str__(self) -> str:
        return self.name


    def __repr__(self) -> str:
        return f'<Channel {self.name!r} members={len(self.members)}>'


    def get_user(self, id: int) -> User:
        """
        Fetch a member by its id.

        Parameters  name  type  description
                    id    int   the id of the user

        Returns
            type         hackchat.User
            description  the fetched user
        """

        return next(
            user for user in self.members
            if user.id == id
        )


    def join(self, nick: str) -> None:
        """
        Join the channel with the given nickname.

        Parameters  name  type  description
                    nick  str   the nickname to join the channel with

        Returns
            nothing
        """

        self.loop.run_until_complete(self._join(nick))
        self.loop.run_forever()


    def event(self, coro: EventCallback):
        """
        Set a new event.

        Parameters  name  type                    description
                    coro  hackchat.EventCallback  the event callback

        Returns
            type         hackchat.EventCallback
            description  the given callback
        """

        self.events.setdefault(coro.__name__, [])
        self.events[coro.__name__].append(coro)
        return coro


    async def _join(self, nick: str) -> None:
        self.client = await self.session.ws_connect('wss://hack.chat/chat-ws')
        await self.client.send_json({
            'cmd': 'join',
            'channel': self.name,
            'nick': nick
        })

        asyncio.create_task(self.listen())


    _join.__doc__ = join.__doc__


    async def send(self, message: str) -> None:
        """
        Send a message in the channel.

        Parameters  name     type  description
                    message  str   the message to send

        Returns
            nothing
        """

        await self.client.send_json({
            'cmd': 'chat',
            'text': message
        })


    async def dispatch(self, event: str, data: t.Any = NO_DATA) -> None:
        """
        Trigger a given event if the callback was set.

        Parameters  name   type        description
                    event  str         the event to trigger
                    data   typing.Any  the argument to pass in the event callback

        Returns
            nothing
        """

        callbacks = self.events.get(event)

        if callbacks:
            for callback in callbacks:
                if data != NO_DATA:
                    coro = callback(data)
                else:
                    coro = callback()

                asyncio.create_task(coro)


    async def leave(self) -> None:
        """
        Leave the channel and close the websocket connection.

        Returns
            nothing
        """

        await self.client.close()
        self.members = []
        self.user = None
        self.client = None


    async def listen(self) -> None:
        """
        Listen the websocket messages.

        Returns
            nothing
        """

        while True:
            data: dict[str] = await self.client.receive_json()
            cmd: str = data['cmd']

            if cmd == 'onlineSet':
                for member in data['users']:
                    user = User(member['nick'], member['userid'])
                    self.members.append(user)

                    if member['isme']:
                        self.user = user

                await self.dispatch('ready')

            elif cmd == 'chat':
                author = self.get_user(data['userid'])
                message = Message(self, author, data['text'])
                await self.dispatch('message', message)

            elif cmd == 'onlineAdd':
                user = User(data['nick'], data['userid'])
                self.members.append(user)
                await self.dispatch('member_joined', user)

            elif cmd == 'onlineRemove':
                user = self.get_user(data['userid'])
                self.members.remove(user)
                await self.dispatch('member_leave', user)

            elif cmd == 'warn':
                if data['text'] == 'You are joining channels too fast. Wait a moment and try again.':
                    raise RateLimit(data['text'])
                await self.dispatch('warn', data['text'])

            elif cmd == 'info':
                await self.dispatch('info', data['text'])