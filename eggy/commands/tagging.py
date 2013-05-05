from .base import Command
import sqlite3

tagdb = "/home/amb/public_html/vote/quote.db"
connection = sqlite3.connect( tagdb )
c = connection.cursor()

def conopen():
    connection = sqlite3.connect( tagdb )
    cursor = connection.cursor()
    return connection,cursor

def topTags( limit=5 ):
    conn,c=conopen()
    query='SELECT tagname,count() FROM tags GROUP BY tagname ORDER BY count() desc LIMIT ?'
    c.execute(query,[limit])
    toptags=c.fetchall()
    conn.close()
    return toptags

def findquotesbytag( tag ):
    conn,c=conopen()
    c.execute(
    'SELECT id FROM quotes WHERE id IN'+
    '(SELECT quoteid FROM tags WHERE tagname=? )',[tag])
    res=[r[0] for r in c.fetchall()]
    conn.close()
    return res

def ircFormatTag(tagname):
    return '[{}]'.format(tagname)

def ircTopTags():
    popular=topTags()
    def tc(entry):
        tag,count=entry
        #return '{} [{}]'.format(count,tag)
        return '{} {}'.format(count, ircFormatTag(tag) )
    top = map( tc, popular )
    return "top tags: "+', '.join(top)

def quotenumsformat( quotelist ):
    ids=['#'+str(res) for res in quotelist]
    return ', '.join(ids)

def ircFindTagCount( tagname ):
    results=findquotesbytag(tagname)
    return "{} quotes tagged {}".format(len(results), ircFormatTag(tagname))

def ircFindTaggedQuotes( tagname ):
    resultslimit = 8
    out=out+quotenumsformat(results[0:resultslimit])
    return out

#not even using this
def chunks(l,n):
    return [l[i:i+n] for i in range(0, len(l), n)]

#print( ircTopTags() )
#print( ircFindTagCount("mspa") )

class Tag(Command):
    def on_command(self, bot, event, args):
        results = "huh?"
        if "list" in args:
          results = ircTopTags()
        if "count" in args:
          args = args.split(' ',1)[1]
          results = ircFindTagCount( args )
        bot.respond(event, results)
        return True
