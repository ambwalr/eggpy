import collections
import random
import re

def iscapital(string):
  return string==string.capitalize()
def istitle(string):
  return string==string.title()

def matchcaps(example,string):
  if example.islower(): #yo mama
    return string.lower()
  if example.isupper(): #YO MAMA
    return string.upper()
  if iscapital(example): #Yo mama
    return string.capitalize()
  if istitle(example): #Yo Mama
    return string.title()
  return string

def beginswith(string,substr):
    return string.find(substr,0,len(substr))!=-1

def getwikiwordlist():
    wikidir="/home/rav/www/wiki.lolwh.at/data/pages/"
    filename="wordlist.txt"
    fullpath=wikidir+filename
    wordlist=open(fullpath,'r' )
    ff=collections.defaultdict(list)
    currentkey=""
    for line in wordlist:
        if beginswith(line,'=='):
            currentkey=line.split()[1]
        if beginswith(line,'*'):
            fixedline=line.replace( "* ","" ).rstrip()
            ff[currentkey].append(fixedline)
    return ff

cachedlist = getwikiwordlist()

def randword(dictionary,word):
    ff = dictionary
    suffix=""
    if word[-1] == "s":
        suffix="s"
        word=word[0:-1]
    lookup = word.lower()
    if lookup in ff:
        choice= random.choice( ff[lookup] )
        result=re.sub(",.+","",choice)
        #return result+suffix
        return matchcaps( word, result+suffix )
    else:
        return "-REDACTED-"

def replword(matchobj):
    dictionary = cachedlist
    mg=matchobj.groups()
    m=mg[0].replace("$","")
    return randword( dictionary, m )

