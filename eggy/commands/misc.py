import re

from .base import Command

class Rebirth(Command):
    def __init__(self):
        self.allowable = re.compile('^[0-9a-zA-Z]+$')

    def on_command(self, bot, event, args):
        if not self.allowable.match(args):
            bot.respond(event, "i'm afraid i can't let you do that $nick")
            return True
        bot.set_nickname(args)
        return True

class Say(Command):
    def on_command(self, bot, event, args):
        bot.respond(event, args)
        return True
