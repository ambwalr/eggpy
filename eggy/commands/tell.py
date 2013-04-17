from .base import Command

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
