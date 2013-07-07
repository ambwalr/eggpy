from .base import Command
import sqlite3

tagdb = "/home/amb/public_html/vote/quote.db"

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

def addTag( tagname, quoteid, user ):
    conn,c=conopen()
    query = 'insert into tags ( tagname, quoteid, user ) values (?,?,?)'
    c.execute(query,[tagname,quoteid,user])
    conn.close()
    return

def findquotesbytag( tag ):
    conn,c=conopen()
    c.execute(
    'SELECT id FROM quotes WHERE id IN'+
    '(SELECT quoteid FROM tags WHERE tagname=? )',[tag])
    res=[r[0] for r in c.fetchall()]
    conn.close()
    return res

def findtagsbyquote( num ):
    conn,c=conopen()
    c.execute('SELECT tagname FROM tags WHERE quoteid =?',[num])
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

def quotenumformat( quotenum ):
    return '#'+str(quotenum)
def quotenumsformat( quotelist ):
    ids=[quotenumformat(res) for res in quotelist]
    return ', '.join(ids)

def ircFindTagCount( tagname ):
    results=findquotesbytag(tagname)
    return "{} quotes tagged {}".format(len(results), ircFormatTag(tagname))

def ircFindTagsByQuote( num ):
    results=findtagsbyquote(num)
    tags=' '.join(map( ircFormatTag, results ))
    if tags=='': tags ='none'
    return "quote {} tags: {}".format( quotenumformat(num), tags )

def ircFindTaggedQuotes( tagname ):
    results=findquotesbytag(tagname)
    out ="{} results for {}: ".format(len(results), ircFormatTag(tagname))
    chunksize = 8
    if len(results) > chunksize*2:
      out+=quotenumsformat(results[0:chunksize])
      out+=" (...) "
      last = len(results)-1
      out+=quotenumsformat(results[last-chunksize:last])
    else:
      out+=quotenumsformat(results)
    return out

#not even using this
def chunks(l,n):
    return [l[i:i+n] for i in range(0, len(l), n)]

#print( ircTopTags() )
#print( ircFindTagCount("mspa") )

class Tag(Command):
    def on_command(self, bot, event, args):
        results = "huh?"
        tokens = args.split(' ')
        firstarg=tokens[0]
        restargs=' '.join(tokens[1:])
        if firstarg == "find":
          results = ircFindTaggedQuotes( restargs )
        if firstarg == "list":
          results = ircTopTags()
        if firstarg == "for":
          results = ircFindTagsByQuote( restargs )
        if firstarg == "count":
          results = ircFindTagCount( restargs )
        if firstarg == "add":
          results = "nope"
        bot.respond(event, results)
        return True


