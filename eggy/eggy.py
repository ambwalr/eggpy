from ircutils import bot
import random
import re
import time
import os
import codecs

from . import settings

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

class QuoteTrigger:
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

class Command(object):
    def on_message(self, bot, event):
        prefix = bot.trigger+' '+self.trigger+' '
        msg = event.message
        if not msg.startswith(prefix):
            return False
        return self.on_command(bot, event, msg[len(prefix):])

class AddQuote(Command):
    def on_command(self, bot, event, new_quote):
        if new_quote in bot.quotes:
            bot.respond(event, "ooooold")
            return True
        bot.quotes.add(new_quote)
        topic = bot.topics[event.target]
        if topic:
            newtopic = re.sub(re.compile(str(len(bot.quotes)-1)), str(len(bot.quotes)), topic)
            if newtopic != topic:
                bot.change_topic(event.target, newtopic)
                return True
        bot.respond(event, "Quote added. "+str(len(bot.quotes))+" quotes in database")
        return True

class GetQuote:
    def __init__(self):
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

class GetY:
    def __init__(self):
        self.trigger = re.compile(r'^:Y (..*)$')

    def on_message(self, bot, event):
        msg = event.message
        result = self.trigger.match(msg)
        if result is None:
            return False
        msg = msg[3:]
        buttQuotes = []
        for q in bot.quotes:
            if msg.lower() in q.lower():
                buttQuotes.append(q)
        if len(buttQuotes) == 0:
            quote = random.choice(bot.quotes)
            bot.respond(event, quote)
        else:
            quote = random.choice(buttQuotes)
            bot.respond(event, quote)
        return True

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
        
class FindQuote(Command):
    def on_command(self, bot, event, args):
        maximum = 30
        results = []
        result = None
        i = 1
        for q in bot.quotes:
            if args.lower() in q.lower():
                results.append(i)
                result = q
            i = i + 1
            if len(results) >= maximum:
                break
        if not results:
            bot.respond(event, "Not found")
            return True
        if len(results) == 1:
            bot.respond(event, str(int(results[0]))+": "+result)
            return True
        bot.respond(event, ', '.join(map(str, results)))
        return True

class SetQuote(Command):
    def on_command(self, bot, event, args):
        bot.quotes.set_last(args)
        bot.respond(event, 'Done!')
        return True

class RelayMessages:
    def on_message(self, bot, event):

        if not event.source in bot.messages_to_relay.keys():
            return False

        if len(bot.messages_to_relay[event.source]) >= 2:
            indexNumber = 1
            bot.respond(event, str(event.source) + " you have new messaeggs, first messaegg: " + str(bot.messages_to_relay[event.source][0]))
            del bot.messages_to_relay[event.source][0]
            for msgToRelay in bot.messages_to_relay[event.source]:
                bot.respond(event, "messaegg #" + str(indexNumber+1) + ": " + str(msgToRelay))
                indexNumber += 1
        else:
            bot.respond(event, str(event.source) + " you have a new messaegg: " + str(bot.messages_to_relay[event.source][0]))

        del bot.messages_to_relay[event.source]

        return True

class Tell(Command):
    def on_command(self, bot, event, args):
        if "me about" in args:
            if len(bot.messages_to_relay.keys()) == 0:
                bot.respond(event, "NOBODY HAS ANY MESSAEGGS, EGG OFF")
                return True
            person_to_tell_about = args.split()[2]
            if person_to_tell_about in bot.messages_to_relay.keys():
                bot.respond(event, str(person_to_tell_about) + " has " + str(len(bot.messages_to_relay[person_to_tell_about])) + " messaeggs waiting")
                return True
            elif person_to_tell_about == "everybody":
                bot.respond(event, "messaeggs for the following: " + str(', '.join(map(str, bot.messages_to_relay.keys()))))
                return True
            else:
                bot.respond(event, "no messaeggs for " + str(person_to_tell_about))
                return True
        elif args.split()[1] == "nothing" and len(args.split()) <= 2:
            person_to_empty = args.split()[0]
            if person_to_empty in bot.messages_to_relay.keys():
                del bot.messages_to_relay[person_to_empty]
                bot.respond(event, "I JUST FORGOT THINGS ABOUT " + str(person_to_empty).upper())
                return True
            else:
                bot.respond(event, str(person_to_empty) + " who???")
                return True

        if len(args.split()) >= 2:
            person_to_tell = args.split(None, 1)[0]
            message_to_tell = args.split(None, 1)[1]
            bot.respond(event, "okay buddy, I'll tell " + str(person_to_tell) + " the following: " + str(message_to_tell))
            if person_to_tell in bot.messages_to_relay.keys():
                bot.messages_to_relay[person_to_tell].append("<" + str(event.source) + "> " + str(message_to_tell))
            else:
                bot.messages_to_relay[person_to_tell] = [("<" + str(event.source) + "> " + str(message_to_tell))]
            return True
        else:
            bot.respond(event, "WHAT, I'M BREGGING UP, SAY THAT EGGAIN")
            return True

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
                GetQuote,
                GetY,
                QuoteTrigger,
                RelayMessages,
                )

        self.commands = (
                ('add', AddQuote),
                ('find', FindQuote),
                ('rebirth', Rebirth),
                ('say', Say),
                ('set last', SetQuote),
                ('tell', Tell),
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

if __name__ == "__main__":
    bot = Eggy()
    bot.connect('irc.dsau.dk')
    import asyncore
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        bot.logger.error("Keyboard interrupt")
    except Exception as exn:
        bot.logger.error("Unhandled exception "+str(type(exn)))
        bot.logger.error(str(exn))
