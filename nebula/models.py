#!/usr/bin/python
import datetime
import json
import os
import sqlite3
import threading
import time
import traceback
import urllib

import qorm

#user
#    id
#    login
#    password
#    config (json)
#facet
#    id
#    name
#    type

setup_sql = """
BEGIN TRANSACTION;
CREATE TABLE "location" (
    "id" integer NOT NULL PRIMARY KEY,
    "path" text NOT NULL
);
CREATE TABLE "media" (
    "id" integer NOT NULL PRIMARY KEY,
    "url" text NOT NULL UNIQUE,
    "name" text NOT NULL,
    "kind" text NOT NULL
);
CREATE TABLE "media_facet" (
    "id" integer NOT NULL PRIMARY KEY,
    "media_id" integer NOT NULL,
    "name" text NOT NULL DEFAULT "",
    "value" text NOT NULL DEFAULT "",
    FOREIGN KEY ("media_id") REFERENCES "media" ("id")
);
-- INSERT INTO LOCATION (id,path) VALUES (null,'/home/wis/uade_chip');
INSERT INTO LOCATION (id,path) VALUES (null,'/home/wis/uade_chip/ahx/Jazz');
COMMIT;
"""

class DB(object):
    def __init__(self, isolation=None):
        self.orm = qorm.QOrmSQLite('nebula.sqlite', isolation)
        self.orm.conn.text_factory = str
        if not self.orm.table('sqlite_master').where(name='location').select():
            self.init_tables()

    def init_tables(self):
        self.orm.script(setup_sql)

    def playlist(self, playlist, search):
        r = []
        j = 0
        for media in self.orm.table('media').where().select():
            media['size'] = 1234
            media['author'] = 'auth%s' % j
            media['type'] = media['url'].split('.')[-1]
            j += 1
            r.append(media)
        return r

    def media_insert(self, url, name):
        self.orm.query("INSERT INTO media (url,name,kind) VALUES (?, ?, '')", url, name)

class IndexLocation(object):
    def index_root(self,root):
        print "index",root
        rpath = str(root.get('path'))
        if os.path.isdir(rpath):
            db = DB(isolation=1)
            for root, dirs, files in os.walk(rpath):
                for name in files:
                    url = os.path.join(root, name)
                    try:
                        db.media_insert(url, name)
                    except sqlite3.IntegrityError,e:
                        pass
            db.orm.commit()
            print "indexdone"

    def run(self):
        db = DB()
        for l in db.orm.table('location').where().select():
            self.index_root(l)

class IndexContent(object):
    def __init__(self):
        self.db = DB()

    def index_file(self,root):
        pass

    def run(self):
        for l in self.db.orm.table('media').where().select():
            pass

class Backend(threading.Thread):
    def run(self):
        now = datetime.datetime.now()
        print "%s says Hello World at time: %s" % (self.getName(), now)
        while 1:
            try:
                IndexLocation().run()
                IndexContent().run()
                time.sleep(60)
            except Exception,e:
                traceback.print_exc()
                os._exit(0)
                time.sleep(60)

def main():
    t = Backend()
    t.start()
