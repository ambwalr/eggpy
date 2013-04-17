class Command(object):
    def on_message(self, bot, event):
        prefix = bot.trigger+' '+self.trigger+' '
        msg = event.message
        if not msg.startswith(prefix):
            return False
        return self.on_command(bot, event, msg[len(prefix):])

