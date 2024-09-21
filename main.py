import sqlite3
import zipfile
import random
import string
from hashlib import sha1
import json
import time
import os
import sys


class Model:
    """
    (int) id => model id (mid)

    (str) name => card type

    (list) tmpls => card templates for this type

    """
    def __init__(self, id, name, tmpls):
        self.id = id
        self.name = name
        self.tmpls = tmpls

class Note:
    def __init__(self, mid, guid, word, translation):
        """
            id              integer primary key,
      -- epoch milliseconds of when the note was created
    guid            text not null,
      -- globally unique id, almost certainly used for syncing
    mid             integer not null,
      -- model id
    mod             integer not null,
      -- modification timestamp, epoch seconds
    usn             integer not null,
      -- update sequence number: for finding diffs when syncing.
      --   See the description in the cards table for more info
    tags            text not null,
      -- space-separated string of tags. 
      --   includes space at the beginning and end, for LIKE "% tag %" queries
    flds            text not null,
      -- the values of the fields in this note. separated by 0x1f (31) character.
    sfld            integer not null,
      -- sort field: used for quick sorting and duplicate check. The sort field is an integer so that when users are sorting on a field that contains only numbers, they are sorted in numeric instead of lexical order. Text is stored in this integer field.
    csum            integer not null,
      -- field checksum used for duplicate check.
      --   integer representation of first 8 digits of sha1 hash of the first field
    flags           integer not null,
      -- unused
    data            text not null
      -- unused
      """
        self.id    = int(time.time()*1000)
        self.guid  = guid
        self.mid   = mid
        self.mod   = int(time.time())
        self.usn   = -1
        self.tags  = ''
        self.flds  = '%s\x1f%s' % (word, translation)
        self.sfld  = word
        self.csum  = int(sha1(word.encode()).hexdigest()[:8], 16)
        self.flags = 0
        self.data  = 0
    def as_tuple(self):
        return (
            self.id, self.guid, self.mid, 
            self.mod, self.usn, self.tags, 
            self.flds, self.sfld, self.csum, 
            self.flags, self.data
        )

class Deck:
    def __init__(self, did, name):
        self.did = did
        self.name = name

class Card:
    def __init__(self, nid, did):
        """
        -- Cards are what you review. 
        -- There can be multiple cards for each note, as determined by the Template.
        CREATE TABLE cards (
            id              integer primary key,
              -- the epoch milliseconds of when the card was created
            nid             integer not null,--    
              -- notes.id
            did             integer not null,
              -- deck id (available in col table)
            ord             integer not null,
              -- ordinal : identifies which of the card templates or cloze deletions it corresponds to 
              --   for card templates, valid values are from 0 to num templates - 1
              --   for cloze deletions, valid values are from 0 to max cloze index - 1 (they're 0 indexed despite the first being called `c1`)
            mod             integer not null,
              -- modification time as epoch seconds
            usn             integer not null,
              -- update sequence number : used to figure out diffs when syncing. 
              --   value of -1 indicates changes that need to be pushed to server. 
              --   usn < server usn indicates changes that need to be pulled from server.
            type            integer not null,
              -- 0=new, 1=learning, 2=review, 3=relearning
            queue           integer not null,
              -- -3=user buried(In scheduler 2),
              -- -2=sched buried (In scheduler 2), 
              -- -2=buried(In scheduler 1),
              -- -1=suspended,
              -- 0=new, 1=learning, 2=review (as for type)
              -- 3=in learning, next rev in at least a day after the previous review
              -- 4=preview
            due             integer not null,
            -- Due is used differently for different card types: 
            --   new: the order in which cards are to be studied; starts from 1.
            --   learning/relearning: epoch timestamp in seconds
            --   review: days since the collection's creation time
            ivl             integer not null,
              -- interval (used in SRS algorithm). Negative = seconds, positive = days
              -- v2 scheduler used seconds for (re)learning cards and days for review cards
              -- v3 scheduler uses seconds only for intraday (re)learning cards and days for interday (re)learning cards and review cards
            factor          integer not null,
              -- The ease factor of the card in permille (parts per thousand). If the ease factor is 2500, the card’s interval will be multiplied by 2.5 the next time you press Good.
            reps            integer not null,
              -- number of reviews
            lapses          integer not null,
              -- the number of times the card went from a "was answered correctly" 
              --   to "was answered incorrectly" state
            left            integer not null,
              -- of the form a*1000+b, with:
              -- a the number of reps left today
              -- b the number of reps left till graduation
              -- for example: '2004' means 2 reps left today and 4 reps till graduation
            odue            integer not null,
              -- original due: In filtered decks, it's the original due date that the card had before moving to filtered.
                            -- If the card lapsed in scheduler1, then it's the value before the lapse. (This is used when switching to scheduler 2. At this time, cards in learning becomes due again, with their previous due date)
                            -- In any other case it's 0.
            odid            integer not null,
              -- original did: only used when the card is currently in filtered deck
            flags           integer not null,
              -- an integer. This integer mod 8 represents a "flag", which can be see in browser and while reviewing a note. Red 1, Orange 2, Green 3, Blue 4, no flag: 0. This integer divided by 8 represents currently nothing
            data            text not null
              -- currently unused
        );
        """
        self.id = int(time.time()*1000)
        self.nid = nid # notes.id
        self.did = did # deck id
        self.ord = 0
        self.mod = int(time.time())
        self.usn = -1
        self.type = 0
        self.queue = 0
        self.due = 10
        self.ivl = 0
        self.factor = 0
        self.reps = 0
        self.lapses = 0
        self.left = 0
        self.odue = 0
        self.odid = 0
        self.flags = 0
        self.data = '{}'
    def as_tuple(self):
        return (
            self.id, self.nid, self.did,
            self.ord, self.mod, self.usn,
            self.type, self.queue, self.due,
            self.ivl, self.factor, self.reps,
            self.lapses, self.left, self.odue, 
            self.odid, self.flags, self.data
        )

def gen_guid(guid_list) -> str:
    """
    
    Generates a GUID for Anki2

    """
    _guid = ''.join(random.choices(string.ascii_letters+string.digits+string.punctuation, k=10))
    for i in guid_list:
        if i[0] == _guid:
            gen_guid(guid_list) # If there is duplicate guid found
    return _guid

if len(sys.argv) < 3:
    print("Usage: python3 anki_database_write.py WORDLIST APKG_FILE [DELIMITER]")
    exit(-1)

wordlist  = os.path.abspath(sys.argv[1]) # Getting filename with some language words+their translation
APKG_FILE   = os.path.abspath(sys.argv[2]) # Temporary accepting collection.anki21
DELIMITER = ' - ' if len(sys.argv) < 4 else sys.argv[3]


# Create a temp working directory and cd into it
TEMP_WORKING_DIR = '.\\TempAnkiDatabaseWrite'
if os.path.isdir(TEMP_WORKING_DIR):
    os.chdir(TEMP_WORKING_DIR)
else:
    os.mkdir(TEMP_WORKING_DIR)
    os.chdir(TEMP_WORKING_DIR)

# Read vocabulary #

words = []
with open(wordlist, 'r', encoding='utf-16') as file:
    for line in file:
        string_ = line.strip().lower()
        words.append(string_.split(DELIMITER))

# END #

# Unpack Anki2 .apkg file #
with zipfile.ZipFile(APKG_FILE, 'r') as zip_ref:
    zip_ref.extractall('.\\')
# END #


# Update Anki2 Database #
db_conn = sqlite3.connect('.\\collection.anki21') # Anki2 db connection object
cur = db_conn.cursor()


# Get models and card templates #

models = cur.execute('SELECT models FROM col').fetchall()

models_arr = []

i = 0

print('Choose a card template:')
for model in models:
    model_ = json.loads(model[0])
    obj = list(model_.values())[0]
    model_id    = obj['id']
    model_name  = obj['name']
    model_tmpls = obj['tmpls']
    models_arr.append(
        Model(model_id, model_name, model_tmpls)
    )
    for tmp in model_tmpls:
        print('[ %d ] => %s (%s)' % (i, tmp['name'],model_name))
    i += 1

mid = -1
while mid < 0 or mid > len(models_arr)-1: # Forces user to select the right index
    mid = int(input('\n--> '))

mid = models_arr[mid].id

# END #

# Get decks #

decks = cur.execute('SELECT decks FROM col').fetchall()

decks_arr = []

print('Choose a deck:')
i = 0
for deck in decks:
    deck_ = json.loads(deck[0])
    obj = list(deck_.values())[0]
    deck_id = obj['id']
    deck_name = obj['name']
    decks_arr.append(Deck(deck_id, deck_name))
    print('[ %d ] => %s' % (i, deck_name))
    i += 1

did = -1
while did < 0 or did > len(decks_arr)-1: # Forces user to select the right index
    did = int(input('\n--> '))

did = decks_arr[did].did
# END #

guid_list = cur.execute('SELECT guid FROM notes').fetchall() # Getting existing guids to evade duplication

notes_data = []

"""
data = [
    (1726351306382, "k,8y_-6/%A", 1726350757302, 1726351367, -1, "метка" , "La calleУлица","La calle",4169362173,0),
    ...
]
"""

cards_data = []

for word in words: # word = [ original, translated ]
    try:
        print('Adding card (%s => %s)' % (word[0], word[1]))
    except IndexError:
        print('Something is wrong with the delimiter you set:', word)
        exit(-1)
    guid = gen_guid(guid_list) # Generate a 10-char string
    guid_list.append(( guid, ))
    note = Note(mid, guid, word[0], word[1])
    card = Card(note.id, did)
    cards_data.append(card.as_tuple())
    notes_data.append(note.as_tuple())
    time.sleep(.01)

cur.executemany("INSERT INTO notes VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", notes_data)
cur.executemany("INSERT INTO cards VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", cards_data)
db_conn.commit() # Save to Anki2 Database
db_conn.close()
# END #

zipfile_name = os.path.abspath('..\\cards%d.apkg' % int(time.time()*1000))
with zipfile.ZipFile(zipfile_name, 'w') as zipf:
    for foldername, subfolders, filenames in os.walk('.\\'):
        for filename in filenames:
            file_path = os.path.join(foldername, filename)
            zipf.write(file_path, os.path.relpath(file_path, '.\\'))

def force_rmdir(directory):
    for root, dirs, files in os.walk(directory, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(directory)

os.chdir('..\\')
force_rmdir(TEMP_WORKING_DIR)

print('Saved to %s' % zipfile_name)

# https://github.com/ankidroid/Anki-Android/wiki/Database-Structure#decks-jsonobjects