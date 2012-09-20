import ConfigParser
from lib import Models
import lib.DBTools
import os
from getpass import getpass
from xml.dom.minidom import parse, parseString
__author__="wbdavis"
__date__ ="$Nov 17, 2011 10:13:17 PM$"
# -*- coding: utf-8 -*-
def check_packages():
    try:
        from ConfigParser import ConfigParser
        import cherrypy
        import cgi
        import logging
        import mimetypes
        import os
        import re
        import random
        import signal, errno
        import sys
        import subprocess
        import shutil
        from subprocess import call
        import StringIO
        import stat
        import urllib
        import subprocess
        from Cheetah.Template import Template
        import tempfile
        import datetime,time
        import json
        import getpass
        from lib import Models
        from twisted.plugin import getPlugins, IPlugin
        try: #This bit here is to handle backwards compatibility with python-json modules. The .write and .dumps methods work analagously as far as I can tell
            json.write("test")
        except AttributeError:
            json.dumps("test")
        try:
            from hashlib import md5
        except ImportError:
            from md5 import md5
        return True
    except Exception, e:
        import sys
        print "You are missing a requisite package: %s." % str(e)
        sys.exit(0)
        
def setup_config():
    # Filelocker Configuration
    print "===== Filelocker Configuration Wizard ====="
    configFile = raw_input("Where would you like to save the config file? [%s%sconf%sfilelocker.conf]: " % (os.getcwd(), os.path.sep, os.path.sep))
    if configFile is None or configFile == "":
        configFile = "%s%sconf%sfilelocker.conf" % (os.getcwd(), os.path.sep, os.path.sep)
    preConfig = None
    if os.path.exists(configFile):
        try:
            preConfig = ConfigParser.RawConfigParser()
            preConfig.read(configFile)
            print "Found existing configuration file, loading previous values as defaults."
        except Exception, e:
            print "Found existing configuration file, but there were problems importing the data. Creating config from scratch."
    configXML = os.path.join(os.getcwd(), "etc", "cherrypy_config_template.xml")
    #TODO: Read cherrypy config XML and iterate through user questions to build config file

def backup_legacy_db(dburi, outfile, host=None, username=None, password=None, db=None):
    from lib.DBTools import LegacyDBConverter
    if host is None:
        host = raw_input("What is the host of the old DB server?: ")
        db = raw_input("Database: ")
        username = raw_input("Username: ")
        password = getpass("Password: ")
    converter = LegacyDBConverter(host, username, password, db)
    converter.port_database(outfile)

def restore_from_backup(dburi, infile):
    from lib.DBTools import import_db
    build_database(dburi)
    import_db(infile, dburi)
    print "Database has been rebuilt  from backed up data"

def backup_database(dburi):
    pass
            
def build_database(dburi):
    Models.drop_database_tables(dburi)
    Models.create_database_tables(dburi)

def reset_admin(dburi):
    password = getpass("Enter Admin password: ")
    confirmPassword = getpass("Confirm password: ")
    if password != confirmPassword:
        while (password!=confirmPassword):
            print "Passwords did not match!"
            password = getpass("Re-Enter Admin password: ")
            confirmPassword = getpass("Confirm password: ")
    lib.Models.create_admin_user(dburi, password)
    print "Admin user account reset"

if __name__ == '__main__':
    from optparse import OptionParser

    p = OptionParser()
    p.add_option('-c', '--config', dest='configfile', 
                 help="specify config file (defaults to etc/filelocker.conf)")
    p.add_option('-b', '--backup-db', dest="backup", action="store_true",
                 help="backup the database")
    p.add_option('-u', '--backup-legacy-db', dest='legacybackup', action="store_true",
                 help="backup a pre 2.6 database (use with -f or --file to specify backup file)")
    p.add_option('-r', '--restore-db', dest='restorebackup', action="store_true",
                 help="restore database from backup (use with -f or --file to specify backup file)")
    p.add_option('-a', '--admin', dest='resetadmin', action="store_true",
                 help="reset admin account")
    p.add_option('-f', '--file', dest='datafile', default=os.path.join(os.getcwd(), "FL_Data_Export.xml"),
                 help="store the process id in the given file")
    p.add_option('-i', '--initialize', dest='initialize', action="store_true",
                 help="Install - initialize database and set admin account")
    options, args = p.parse_args()

    dburi = None
    config = ConfigParser.SafeConfigParser()
    if options.configfile is not None:
        config.read(options.configfile)
    else:
        configfile = os.path.join(os.getcwd(),"etc","filelocker.conf")
        if not os.path.exists(configfile):
            configfile = os.path.join("/","etc","filelocker.conf")
        if not os.path.exists(configfile):
            raise Exception("Could not find config file, please specify one using the -c option")
        config.read(configfile)
    dburi = config.get("/","tools.SATransaction.dburi").replace("\"", "").replace("'","")

    if options.legacybackup:
        username = config.get("database","dbuser").replace("\"", "").replace("'","")
        password = config.get("database","dbpassword").replace("\"", "").replace("'","")
        host = config.get("database","dbhost").replace("\"", "").replace("'","")
        db = config.get("database","dbname").replace("\"", "").replace("'","")
        backup_legacy_db(dburi, options.datafile, host, username, password, db)
    elif options.backup:
        backup_db(dburi, options.datafile)
    if options.restorebackup:
        restore_from_backup(dburi, options.datafile)
    if options.resetadmin:
        reset_admin(dburi)
    if options.initialize:
#        setup_config()
        build_database(dburi)
        reset_admin(dburi)
