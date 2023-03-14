from .constants import *
from . import client
from . import md

import typing as t # TODO:
import asyncio



class Arg:

    def __init__(self, name: str, description: str | None = None, required: bool = False) -> None:
        self.name = name
        self.description = description
        self.required = required



class Command:

    def __init__(self, name: str, description: str, args: list[Arg], callback: CommandCallback) -> None:
        self.name = name
        self.description = description
        self.args = args
        self.callback = callback


    def __str__(self) -> str:
        return self.name


    def __repr__(self) -> str:
        return f'<Command {self.name}>'


    async def start(self, args: list[str]) -> None:
        await self.callback(*args)



class BotChannel(client.Channel):

    def __init__(self, prefix: str, name: str, loop: asyncio.AbstractEventLoop | None = None) -> None:
        super().__init__(name, loop)
        self.prefix = prefix

        self.events['message'] = [self.event_message]
        self.commands: list[Command] = [
            Command(
                'help',
                'show all the available commands',
                [Arg(name='command', description='the command to show it usage')],
                self._command_help
            )
        ]


    async def _command_help(self, cmd: str | None = None):
        if cmd:
            command = self.get_command(cmd)
            args = ' '.join(
                f'<{arg.name}>' if arg.required else f'({arg.name})'
                for arg in command.args
            )

            args_details = md.create_table(
                ['name', 'description', 'required'],
                [
                    (arg.name, arg.description, arg.required)
                    for arg in command.args
                ]
            )

            await self.send(f'---\n# Command **{command}**\n{self.prefix}{command} {args}\n\n---\n## Arguments\n{args_details}')
            return

        await self.send(f'**{self.prefix}help <command>** to get informations about a specific command.')
        await self.send('\n'.join(
            f'- **{command.name}**: {command.description}'
            for command in self.commands
        ))


    def command(self, name: str, description: str, args: list[Arg] = []) -> t.Callable[[CommandCallback], CommandCallback]:
        def decorator(func):
            cmd = Command(name, description, args, func)
            self.commands.append(cmd)
            return cmd
        return decorator


    def parse_arguments(self, args: str) -> list[str]:
        arguments = []
        in_quotes = False
        current_argument = ''

        for c in args:
            if c == '"':
                in_quotes = not in_quotes

            elif c == ' ' and not in_quotes:
                if current_argument:
                    arguments.append(current_argument)
                    current_argument = ''
            else:
                current_argument += c

        if current_argument:
            arguments.append(current_argument)
        return arguments


    def get_command(self, name: str) -> Command:
        return next(
            command for command in self.commands
            if command.name == name
        )


    async def event_message(self, message: client.Message):
        if message.content.startswith(self.prefix):
            parts = message.content.split()
            command = parts[0].split(self.prefix, maxsplit=1)[1]
            command = self.get_command(command)

            if len(parts) > 1:
                args = self.parse_arguments(' '.join(parts[1:]))
            else:
                args = []

            await command.start(args)