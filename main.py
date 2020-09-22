#!/usr/bin/env python

# -*- coding: utf-8 -*-

""" 
BoxGuessBot
    
    0.0.1
        Initial Release


http://twitch.tv/johnlonnie

"""

#--------------------------------
# SCRIPT IMPORT LIBRARIES
#--------------------------------

import auth
import cfg
import socket
import time
import re
import sys
import datetime
import re
import gspread
import pygsheets
import pandas as pd

#--------------------------------
#GLOBAR VARS
#--------------------------------

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
gc = pygsheets.authorize(client_secret='client_secret.json')

df = pd.DataFrame({'Guesses & Questions':[],}) # initialize and set the pandas data frame
sh = gc.open("What is in the Box") #name of the google sheet
wks = sh[1] # set the worksheet

#--------------------------------
#HELPERS
#--------------------------------

# Parse IRCv3 tags
ircv3_tag_escapes = {':': ';', 's': ' ', 'r': '\r', 'n': '\n'}
def _tags_to_dict(tag_list, separator=';'):
    tags = {}
    if separator:
        tag_list = tag_list.split(separator)
    for tag in tag_list:
        tag = tag.split('=', 1)
        if len(tag) == 1:
            tags[tag[0]] = True
        elif len(tag) == 2:
            if '\\' in tag[1]: # Iteration is bad, only do it if required.
                value  = ''
                escape = False
                for char in tag[1]: # TODO: Remove this iteration.
                    if escape:
                        value += ircv3_tag_escapes.get(char, char)
                        escape = False
                    elif char == '\\':
                        escape = True
                    else:
                        value += char
            else:
                value = tag[1] or True
            tags[tag[0]] = value
    print ("TAGS TO DICT OK")

    return tags

# Create the IRCv2/3 parser
def ircv3_message_parser(msg):
    n = msg.split(' ')

    # Process IRCv3 tags
    if n[0].startswith('@'):
        tags = _tags_to_dict(n.pop(0)[1:])
    else:
        tags = {}

    # Process arguments
    if n[0].startswith(':'):
        while len(n) < 2:
            n.append('')
        hostmask = n[0][1:].split('!', 1)
        if len(hostmask) < 2:
            hostmask.append(hostmask[0])
        i = hostmask[1].split('@', 1)
        if len(i) < 2:
            i.append(i[0])
        hostmask = (hostmask[0], i[0], i[1])
        cmd      = n[1]
    else:
        cmd      = n[0]
        hostmask = (cmd, cmd, cmd)
        n.insert(0, '')

    # Get the command and arguments
    args = []
    c = 1
    for i in n[2:]:
        c += 1
        if i.startswith(':'):
            args.append(' '.join(n[c:]))
            break
        else:
            args.append(i)

    print ("MESSAGE PARSER OK")
    # Return the parsed data
    return cmd, hostmask, tags, args

# Escape tags
def _escape_tag(tag):
    tag = str(tag).replace('\\', '\\\\')
    for i in ircv3_tag_escapes:
        tag = tag.replace(ircv3_tag_escapes[i], '\\' + i)
    print("TAGS ESCAPED")
    return tag

# Convert a dict into an IRCv3 tags string
def _dict_to_tags(tags):
    res = b'@'
    for tag in tags:
        if tags[tag]:
            etag = _escape_tag(tag).replace('=', '-')
            if isinstance(tags[tag], str):
                etag += '=' + _escape_tag(tags[tag])
            etag = (etag + ';').encode('utf-8')
            if len(res) + len(etag) > 4094:
                break
            res += etag
    if len(res) < 3:
        return b''
    print("DICT TO TAGS OK")
    return res[:-1] + b' '


#send to the socket
def send(s, text):
    s.send(text.encode('utf-8') + b'\r\n')

#send chat message
def chat(sock, msg):

    #Send a chat message to the server.
    #Keyword arguments:
    #sock -- the socket over which to send the message
    #msg  -- the message to be sent

    sock.send(("PRIVMSG {} :{}\r\n".format(auth.CHAN, msg)).encode("UTF-8"))

def addGuess(guesstext):
    global guessArray
    guessArray = np.append(guesstext)

def addQuestion(questiontext):
    global questionArray
    questionArray.append(questiontext)

#--------------------------------
# MAIN LOOP
#--------------------------------

def bot_loop():

    global s
    global guessList
    global df

    #connect to the IRC chat
    s.connect((auth.HOST, auth.PORT))
    s.send("PASS {}\r\n".format(auth.PASS).encode("utf-8"))
    s.send("NICK {}\r\n".format(auth.NICK).encode("utf-8"))
    s.send("JOIN {}\r\n".format(auth.CHAN).encode("utf-8"))
    s.send("CAP REQ :twitch.tv/tags".encode("utf-8") + b'\r\n')

    chat(s, cfg.ENTRYMESSAGE)

    while True:
        data = s.recv(1024)

        if data.decode("utf-8") == "PING :tmi.twitch.tv\r\n":
            s.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))

        else:
            print("DATA")
            print (data)
            
            data = data.decode() # turn socket message into byte type
            print("DATA DECODED")
            print (data)
            
            parsedMessage = ircv3_message_parser(data) # run message through decoder to get list with tags
            
            print("PARSED MESSAGE")
            print(parsedMessage)
            
            tagStrip = parsedMessage[2] # separate tag dict from list
            print("TAG STRIPPED")

            # get the username
            if 'display-name' in tagStrip:
                username = tagStrip.get('display-name').strip()
                        
            # get the message from the parser and remove unnecessary chars 
            messageStrip = parsedMessage[3]
            print("MESSAGE STRIPPED")
            print (messageStrip)
            try:
                messageIsolated = messageStrip[1]
                print("MESSAGE ISOLATION COMPLETE")
                print(messageIsolated)
            except IndexError:
                messageIsolated = ""
                print("MESSAGE ISOLATED EXCEPTION")
            if len(messageIsolated) > 0:
                trueMessage = messageIsolated[1:] # separate message from username who sent it
                cleanMessage = trueMessage.strip() # clean the message by stripping leading and trailing chars
                splitMessage = trueMessage.split(' ') # split the message into a list
          

            if splitMessage[0] == "!guess" and len(splitMessage) > 0:
                print("ADDING GUESS")
                guessText = cleanMessage[7:]
                guessData = [{'Guesses & Questions':guessText}]
                df = df.append(guessData,ignore_index=True,sort=False)
                print(df)
                wks.set_dataframe(df,(1,4))
            
            if splitMessage[0] == "!question" and len(splitMessage) > 0:
                print("ADDING QUESTION")
                questionText = "QUESTION: " + cleanMessage[10:]
                questionData = [{'Guesses & Questions':questionText}]
                df = df.append(questionData,ignore_index=True,sort=False)
                print(df)
                wks.set_dataframe(df,(1,4))                       

            if splitMessage[0] == "!goof" and len(splitMessage) > 0:
                print("ADDING QUESTION")
                goofText = "GOOF: " + cleanMessage[6:]
                goofData = [{'Guesses & Questions':goofText}]
                df = df.append(goofData,ignore_index=True,sort=False)
                print(df)
                wks.set_dataframe(df,(1,4)) 

    sleep(1)
if __name__ == "__main__":
    bot_loop()