from ircutils import bot
import random
import re
import time
import os
import codecs

from . import settings
from . import commands

def open(filename, mode):
    return codecs.open(filename, mode, 'utf-8')

class Paths:
    """Class responsible for locating configuration files, logs, quotes and
    what not on disk."""
    def __init__(self, bot):
        self.quotes = 'quotes.txt'
        self.chatlog_base = 'log'

    def chatlog(self, kind, name, now):
        month = time.strftime("%Y%m", now)
        date = time.strftime("%Y%m%d", now)
        d = self.chatlog_base+'/'+kind+'/'+name+'/'+month
        try:
            os.makedirs(d, 0o777)
        except OSError as err:
            pass
        return d + '/' + kind + '.' + name + '.' + date + '.txt'

class LogTarget:
    def __init__(self, paths, kind, name):
        self.paths = paths
        self.kind = kind
        self.name = name
        self.fd = None
        self.filename = None

    def ensure_open(self, now):
        f = self.paths.chatlog(self.kind, self.name, now)
        if not self.fd:
            self.filename = f
            self._open()
            return
        if f != self.filename:
            self.fd.close()
            self.filename = f
            self._open()

    def _open(self):
        self.fd = open(self.filename, 'a')

    def write_line(self, line, now):
        self.ensure_open(now)
        self.fd.write(line+'\n')
        self.fd.flush()

class Logger:
    """Class responsible for logging messages and internal events to the bot
    operator."""

    def __init__(self, bot, paths):
        self.bot = bot
        self.fmt = "<{0}> {1}"
        self.paths = paths
        self.maintarget = LogTarget(paths, 'main', 'main')
        self.chtargets = {}
        bot.events["message"].add_handler(self.on_message)
        bot.events["welcome"].add_handler(self.on_welcome)

    def _chatlogline(self, line, target=None):
        """Write a chat line to standard out and the current chat log file."""
        now = time.gmtime()
        prefix = time.strftime("%Y-%m-%d %H:%M:%S UTC ", now)
        if target:
            prefix += target+' '
        line = prefix+line
        print(line.encode('utf-8'))
        self.maintarget.write_line(line, now)
        if target:
            self.get_channel(target).write_line(line, now)

    def get_channel(self, target):
        target = target[1:]

        if not target in self.chtargets:
            self.chtargets[target] = LogTarget(self.paths, 'channel', target)

        return self.chtargets[target]

    def on_welcome(self, bot, event):
        self._chatlogline("Connected to server as "+bot.nickname)

    def on_message(self, bot, event):
        line = self.fmt.format(event.source, event.message)
        self._chatlogline(line, event.target)

    def on_bot_message(self, target, line):
        line = self.fmt.format(self.bot.nickname, line)
        self._chatlogline(line, target)

    def error(self, msg):
        self._chatlogline("Error: "+msg)

    def on_initial_topic(self, target, topic):
        self._chatlogline("Topic in "+target+" is: "+topic, target)

    def on_change_topic(self, changer, target, topic):
        self._chatlogline(changer+" changed topic in "+target+" to: "+topic, target)

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
        self._open_quotes()

    def _open_quotes(self):
        self.quotesfd = open(self.paths.quotes, 'a+')
        self._read_quotes()

    def add(self, quote):
        if quote == '' or '\n' in quote:
            raise ValueError()
        self.quotes += [quote]
        self.quotesfd.write(quote+'\n')
        self.quotesfd.flush()

    def set_last(self, quote):
        self.set_quote(len(self.quotes)-1, quote)

    def set_quote(self, idx, quote):
        if not self.quotes[idx]:
            raise ValueError()
        self.quotes[idx] = quote
        self._rewrite_quotes()

    def _rewrite_quotes(self):
        self.quotesfd.close()
        self.quotesfd = open(self.paths.quotes, 'w')
        for quote in self.quotes:
            self.quotesfd.write(quote+'\n')
        self.quotesfd.close()
        self._open_quotes()

    def __len__(self):
        return len(self.quotes)

    def __getitem__(self, key):
        return self.quotes[key]

    def __iter__(self):
        return iter(self.quotes)

class Eggy(bot.SimpleBot):
    def __init__(self):
        super(bot.SimpleBot, self).__init__(settings.IDENT)
        self.trigger = settings.TRIGGER
        self.message_handlers = ()
        self.topics = {}
        self.messages_to_relay = {}

        # Load modules.
        self.paths = Paths(self)
        self.logger = Logger(self, self.paths)
        self.quotes = Quotes(self, self.paths)

        self.noncommands = (
                commands.GetQuote,
                commands.GetY,
                commands.QuoteTrigger,
                commands.RelayMessages,
                )

        self.commands = (
                ('add', commands.AddQuote),
                ('find', commands.FindQuote),
                ('rebirth', commands.Rebirth),
                ('say', commands.Say),
                ('set last', commands.SetQuote),
                ('tell', commands.Tell),
                ('tag', commands.Tag),
                )

        self.events["welcome"].add_handler(self.on_welcome)
        self.events["message"].add_handler(self.on_message)
        self.events["reply"].add_handler(self.on_reply)
        self.events["any"].add_handler(self.on_any)
        self.events["join"].add_handler(self.on_join)

    def on_message(self, bot, event):
        for (command, handler) in self.commands:
            try:
                fn = handler()
                fn.trigger = command
                if fn.on_message(bot, event):
                    return
            except Exception as err:
                self.logger.error("Command ["+str(command)+"] threw exception "+str(type(err)))
                self.logger.error(str(err))
        for handler in self.noncommands:
            try:
                fn = handler()
                if fn.on_message(bot, event):
                    return
            except Exception as err:
                self.logger.error("Non-command ["+str(handler)+"] threw exception "+str(type(err)))
                self.logger.error(str(err))

    def respond(self, event, response):

        # $variable replacements START, first up is $nick, ALSO THIS PROBABLY IS BAD
        response=re.sub(r"\$([A-Za-z]+)(1)?", commands.wikiwordlist.replword, response)

        response = response.replace("$nick", event.source)
        response = response.replace("$Nick", event.source)
        response = response.replace("$NICK", event.source.upper())

        # then we got this bro called $onick

        response = response.replace("$onick", random.choice(self.channels[event.target].user_list))
        response = response.replace("$oNick", random.choice(self.channels[event.target].user_list))
        response = response.replace("$ONICK", random.choice(self.channels[event.target].user_list).upper())

        # next up is $verb, doing handsomely with his bros

        response = response.replace("$verb", "poo")
        response = response.replace("$Verb", "Poo")
        response = response.replace("$VERB", "POO")

        # and then we got ourselves a $adjective

        response = response.replace("$adjective", "terrible")
        response = response.replace("$Adjective", "Terrible")
        response = response.replace("$ADJECTIVE", "TERRIBLE")

        # and can't forget our bro super$noun

        response = response.replace("$noun", "egg")
        response = response.replace("$Noun", "Egg")
        response = response.replace("$NOUN", "EGG")

        # $variable replacements END

        self.say(event.target, response)

    def say(self, target, line):
        self.send_message(target, line)
        self.logger.on_bot_message(target, line)

    def on_welcome(self, bot, event):
        self.join_channel(settings.CHANNEL)

    def change_topic(self, target, topic):
        self.execute('TOPIC', target, trailing=topic)

    def topic_changed(self, target, topic):
        self.topics[target] = topic

    def on_any(self, bot, event):
        if event.command == 'TOPIC':
            self.logger.on_change_topic(event.source, event.target, event.params[0])
            self.topic_changed(event.target, event.params[0])

    def on_reply(self, bot, event):
        if event.command == 'RPL_TOPIC':
            self.logger.on_initial_topic(event.params[0], event.params[1])
            self.topic_changed(event.params[0], event.params[1])

    def on_join(self, bot, event):
        self.execute("MODE", event.target)
