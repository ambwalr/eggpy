from ircutils import bot
import random
import re

class Paths:
    """Class responsible for locating configuration files, logs, quotes and
    what not on disk."""
    def __init__(self, bot):
        self.quotes = 'quotes.txt'
        self.chatlog = 'chatlog.txt'

class Logger:
    """Class responsible for logging messages and internal events to the bot
    operator."""

    def __init__(self, bot, paths):
        self.bot = bot
        self.fmt = "<{0}> {1}"
        self.paths = paths
        self.chatfd = open(paths.chatlog, 'a')
        # We don't use add_message_handler, because we always want to capture messages
        bot.events["message"].add_handler(self.on_message)
        bot.events["welcome"].add_handler(self.on_welcome)

    def _chatlogline(self, line):
        """Write a chat line to standard out and the current chat log file."""
        print(line)
        self.chatfd.write(line+'\n')

    def on_welcome(self, bot, event):
        self._chatlogline("Connected to server as "+bot.nickname)

    def on_message(self, bot, event):
        line = self.fmt.format(event.source, event.message)
        self._chatlogline(line)

    def on_bot_message(self, target, line):
        line = self.fmt.format(self.bot.nickname, line)
        self._chatlogline(line)

    def error(self, msg):
        self._chatlogline("Error: "+msg)

class Quotes:
    """Class responsible for the quotes database and printing out a random
    quote."""
    def _read_quotes(self):
        self.quotes = []
        self.quotesfd.seek(0)
        for quote in self.quotesfd:
            self.quotes += [quote.rstrip('\n\r')]

    def __init__(self, bot, paths):
        self.paths = paths
        self.quotesfd = open(paths.quotes, 'a+')
        self._read_quotes()

    def add(self, quote):
        if quote == '' or '\n' in quote:
            raise ValueError()
        self.quotes += [quote]
        self.quotesfd.write(quote+'\n')

    def __len__(self):
        return len(self.quotes)

    def __getitem__(self, key):
        return self.quotes[key]

class QuoteTrigger:
    def __init__(self, bot):
        bot.add_message_handler(self, self.on_message)

    def on_message(self, bot, event):
        msg = event.message

        if not bot.trigger in msg:
            return False

        if len(bot.quotes) == 0:
            bot.respond(event, "No quotes")
        else:
            quote = random.choice(bot.quotes)
            bot.respond(event, quote)

        return True

class Command:
    def __init__(self, bot, command):
        bot.add_message_handler(self, self.on_message)
        self._command = command

    def on_message(self, bot, event):
        prefix = bot.trigger+' '+self._command+' '
        msg = event.message
        if not msg.startswith(prefix):
            return False
        return self.on_command(bot, event, msg[len(prefix):])

class AddQuote(Command):
    """Class responsible for the add quote command."""
    def __init__(self, bot):
        super().__init__(bot, "add")
        bot.add_message_handler(self, self.on_message)

    def on_command(self, bot, event, new_quote):
        bot.quotes.add(new_quote)
        bot.respond(event, "Quote added. "+str(len(bot.quotes))+" quotes in database")
        return True

class GetQuote(Command):
    def __init__(self, bot):
        bot.add_message_handler(self, self.on_message)
        self.trigger = re.compile('^#(-?[1-9]\d*)?$')

    def on_message(self, bot, event):
        msg = event.message
        result = self.trigger.match(msg)
        if result is None:
            return False
        query = result.group(1)
        if query is None:
            bot.respond(event, str(len(bot.quotes)))
            return True
        number = int(query)
        if number < 0:
            number += len(bot.quotes)+1
        if number > len(bot.quotes) or number <= 0:
            return False
        bot.respond(event, bot.quotes[number-1])
        return True

class Eggy(bot.SimpleBot):
    def __init__(self):
        super(bot.SimpleBot, self).__init__("ravpython")
        self.trigger = 'eggpy'
        self.message_handlers = ()

        # Load modules. The order is important, since the modules will call
        # add_message_handler in their __init__, and the order determines the
        # order in which messages are handled.
        self.paths = Paths(self)
        self.logger = Logger(self, self.paths)
        self.quotes = Quotes(self, self.paths)
        self.add_quote = AddQuote(self)
        self.get_quote = GetQuote(self)
        self.quote_trigger = QuoteTrigger(self)
        self.events["welcome"].add_handler(self.on_welcome)
        self.events["message"].add_handler(self.on_message)

    def add_message_handler(self, handler, fn):
        """Adds a business logic message handler that returns True when the
        message should be captured and False when the message should be passed
        on."""
        self.message_handlers += ((handler,fn),)

    def on_message(self, bot, event):
        for (handler, fn) in self.message_handlers:
            try:
                if fn(bot, event):
                    return
            except Exception as err:
                self.logger.error("Handler "+str(handler)+" threw exception "+str(type(err)))
                self.logger.error(str(err))

    def respond(self, event, response):
        self.say(event.target, response)

    def say(self, target, line):
        self.send_message(target, line)
        self.logger.on_bot_message(target, line)

    def on_welcome(self, bot, event):
        self.join_channel('#ravpython')

if __name__ == "__main__":
    bot = Eggy()
    bot.connect('irc.dsau.dk')
    import asyncore
    asyncore.loop()
