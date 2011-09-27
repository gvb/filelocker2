#!/usr/bin/python2.4
# -*- coding: utf-8 -*-
import StringIO
from subprocess import call
import random
import mimetypes
mimetypes.init()
mimetypes.types_map['.dwg']='image/x-dwg'
mimetypes.types_map['.ico']='image/x-icon'
import stat
import urllib
import subprocess
import cherrypy
from cherrypy.process import plugins, servers
from cherrypy.lib.static import serve_file
from cherrypy.process.plugins import DropPrivileges
from cherrypy.lib import cptools, http, file_generator_limited
from cherrypy import HTTPError
import cgi
import re
import tempfile
import os
import sys
import signal, errno
import logging
import datetime,time

from Cheetah.Template import Template
from Cheetah.Filters import WebSafe

from core.dao.models.Permission import Permission
from core.dao.models.User import User
from core.dao.models.Attribute import Attribute
from core.dao.models.FLError import FLError
from core.dao.models.Message import Message
from core.dao.models.ActionLog import ActionLog
from core.dao.models.File import File
from core.dao.models.Parameter import Parameter
from core.Filelocker import Filelocker
from core.Filelocker import __version__ as FL_VERSION
from core.dao import dao_creator
from core import encryption
from core import directory


    

       


    
            
class HTTP_CLI:
    validIPv4 = re.compile('^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')
    validIPv6 = re.compile('^\s*((([0-9A-Fa-f]{1,4}:){7}([0-9A-Fa-f]{1,4}|:))|(([0-9A-Fa-f]{1,4}:){6}(:[0-9A-Fa-f]{1,4}|((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){5}(((:[0-9A-Fa-f]{1,4}){1,2})|:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){4}(((:[0-9A-Fa-f]{1,4}){1,3})|((:[0-9A-Fa-f]{1,4})?:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){3}(((:[0-9A-Fa-f]{1,4}){1,4})|((:[0-9A-Fa-f]{1,4}){0,2}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){2}(((:[0-9A-Fa-f]{1,4}){1,5})|((:[0-9A-Fa-f]{1,4}){0,3}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){1}(((:[0-9A-Fa-f]{1,4}){1,6})|((:[0-9A-Fa-f]{1,4}){0,4}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(:(((:[0-9A-Fa-f]{1,4}){1,7})|((:[0-9A-Fa-f]{1,4}){0,5}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:)))(%.+)?\s*$')
    
    @cherrypy.expose
    def register_client(self, username, password, hostIPv4="", hostIPv6="", **kwargs):
        fl, authType, authenticated, sMessages, fMessages, cliKey = cherrypy.thread_data.flDict['app'], None, False, [], [], None
        if kwargs.has_key("authType"):
            authType = kwargs['authType']
        else:
            authType = fl.authType
        username = strip_tags(username)
        try:
            if authType == "cas":
                if fl.CAS.proxy_cas_authenticate(username, password):
                    authenticated = True
            else:
                if password is None or password == "":
                    fMessages.append("Password cannot be blank")                
                elif (authType == "local" and fl.localDirectory.authenticate(username, password)) or (authType!="local" and fl.directory.authenticate(username, password)):
                    currentUser = fl.get_user(username, True) #if they are authenticated and local, this MUST return a user object
                    if currentUser is not None:
                        if authType == "local":
                            currentUser.isLocal = True #Tags a user if they used a local login, in case we want to use this later
                        if currentUser.authorized == False:
                            fMessages.append("You do not have access to this system")
                        fl.record_login(currentUser, cherrypy.request.remote.ip)
                        fl.log_action(currentUser.userId, "Register Client", None, "You registered a new Filelocker client.")
                        authenticated = True
                    else: #This should only happen in the case of a user existing in the external directory, but having never logged in before
                        try:
                            newUser = fl.directory.lookup_user(username)
                            fl.install_user(newUser)
                            currentUser = fl.get_user(username, True)
                            if currentUser is not None and currentUser.authorized != False:
                                authenticated = True
                            else:
                                fMessages.append("You do not have permission to access this system")
                        except FLError, fle:
                            fMessages.append("Could not install your user account on the system: %s" % fle.failureMessages)
            if authenticated:
                cliKey = fl.get_CLIkey(username, hostIPv4, hostIPv6)
                if cliKey is None:
                    cliKey = fl.create_CLIkey(username, hostIPv4, hostIPv6)
                sMessages.append("Filelocker client successfully registered")
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        except Exception, e:
            fMessages.append("Problem registering new Filelocker client: %s" % str(e))
        return fl_response(sMessages, fMessages, format="cli", data=cliKey) 
    
        
    @cherrypy.expose
    def CLI_login(self, CLIkey, userId):
        fl, sMessages, fMessages = (cherrypy.thread_data.flDict['app'], [], [])
        hostIP = cherrypy.request.remote.ip
        if(self.validIPv4.match(hostIP)):
            hostIPv4 = hostIP
            hostIPv6 = ""
        elif(self.validIPv6.match(hostIP)):
            hostIPv4 = ""
            hostIPv6 = hostIP
        try:
            if(fl.verify_CLIlogin(userId, hostIPv4, hostIPv6, CLIkey)):
                currentUser = fl.get_user(userId, True)
                cherrypy.session["user"], cherrypy.session["filelocker"], cherrypy.session["sMessages"], cherrypy.session["fMessages"] = currentUser, fl, [], []
                fl.record_login(currentUser, hostIP, "CLI")
                sMessages.append("Welcome, %s, to the command line interface for Filelocker" % userId)
            else:
                fMessages.append("Login failed: invalid CLI key for this userID and IP address")
        except FLError, fle:
                fMessages.extend(fle.failureMessages)
                sMessages.extend(fle.successMessages)
        return fl_response(sMessages, fMessages, format="cli")
        
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def create_CLIkey(self, hostIPv4, hostIPv6, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        hostIPv4 = strip_tags(hostIPv4)
        if hostIPv6 != "":
            hostIPv6 = self.expand_IPv6(strip_tags(hostIPv6))
        if (hostIPv4 != "" and self.validIPv4.match(hostIPv4)) or (hostIPv6 != "" and self.validIPv6.match(hostIPv6)) or (hostIPv4 != "" and hostIPv6 != ""):
            try:
                fl.create_CLIkey(user.userId, hostIPv4, hostIPv6)
                sMessages.append("CLI key successfully created")
            except FLError, fle:
                fMessages.extend(fle.failureMessages)
                sMessages.extend(fle.successMessages)
        else:
            fMessages.append("Not a valid IPv4 or IPv6 address.")
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_CLIkey_list(self, format="json", **kwargs):
        user, fl, sMessages, fMessages, CLIKeysList = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [], [])
        try:
            CLIKeys = fl.get_CLIkey_list(user.userId)
            for CLIKey in CLIKeys:
                CLIKeysList.append({'hostIPv4': CLIKey.CLIKeyHostIPv4, 'hostIPv6': CLIKey.CLIKeyHostIPv6, 'value': CLIKey.CLIKeyValue})
        except FLError, fle:
            fMessages.extend(fle.failureMessages)
            sMessages.extend(fle.successMessages)
        return fl_response(sMessages, fMessages, format, data=CLIKeysList)
    
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def delete_CLIkey(self, hostIPv4, hostIPv6, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        hostIPv4 = strip_tags(hostIPv4)
        if hostIPv6 != "":
            hostIPv6 = self.expand_IPv6(strip_tags(hostIPv6))
        if (hostIPv4 != "" and self.validIPv4.match(hostIPv4)) or (hostIPv6 != "" and self.validIPv6.match(hostIPv6)) or (hostIPv4 == "" and hostIPv6 == ""):
            try:
                fl.delete_CLIkey(user.userId, hostIPv4, hostIPv6)
                sMessages.append("CLI key successfully deleted")
            except FLError, fle:
                fMessages.extend(fle.failureMessages)
                sMessages.extend(fle.successMessages)
        else:
            fMessages.append("Not a valid IPv4 or IPv6 address.")
        return fl_response(sMessages, fMessages, format)
        
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def download_CLIconf(self, CLIKey, **kwargs):
        fl = cherrypy.thread_data.flDict['app']
        try:
            response = cherrypy.response
            response.headers['Cache-Control'] = "no-cache"
            response.headers['Content-Disposition'] = '%s; filename="%s"' % ("attachment", "filelocker_cli.conf")
            response.headers['Content-Type'] = "application/x-download"
            response.headers['Pragma']="no-cache"
            response.body = str(Template(file=fl.get_template_file('filelocker_cli.conf.tmpl'), searchList=[locals(),globals()]))
            response.headers['Content-Length'] = len(response.body[0])
            response.stream = True
            return response.body
        except Exception,e:
            logging.error("Error: %s" % str(e))
            raise HTTPError(500, "Unable to serve CLI configuration file: %s" % str(e))
    
    def expand_IPv6(self, address):
        fullAddress = "" # All groups
        expandedAddress = "" # Each group padded with leading zeroes
        validGroupCount = 8
        validGroupSize = 4
        if "::" not in address: # All groups are already present
            fullAddress = address
        else: # Consecutive groups of zeroes have been collapsed with "::"
            sides = address.split("::")
            groupsPresent = 0
            for side in sides:
                if len(side) > 0:
                    groupsPresent += len(side.split(":"))
            if len(sides[0]) > 0:
                fullAddress += sides[0] + ":"
            for i in range(0,validGroupCount-groupsPresent):
                fullAddress += "0000:"
            if len(sides[1]) > 0:
                fullAddress += sides[1]
            if fullAddress[-1] == ":":
                fullAddress = fullAddress[:-1]
        groups = fullAddress.split(":")
        for group in groups:
            while(len(group) < validGroupSize):
                group = "0" + group
            expandedAddress += group + ":"
        if expandedAddress[-1] == ":":
            expandedAddress = expandedAddress[:-1]
        return expandedAddress

      


#def regenerate_session_id(): #Work in progress, currently not used
    #"""Replace the current session (with a new id)."""
    #if cherrypy.session.id is not None:
        #try:
            #cherrypy.session.delete()
        #except KeyError, ke:
            #print "Tried to delete %s, this is contents of cache: %s" % (cherrypy.session.id, cherrypy.session.cache)
    #old_session_was_locked = cherrypy.session.locked
    #if old_session_was_locked:
        #cherrypy.session.release_lock()
    #cherrypy.session.id = None
    #while cherrypy.session.id is None:
        #cherrypy.session.id = cherrypy.session.generate_id()
        ## Assert that the generated id is not already stored.
        #if cherrypy.session._exists():
            #cherrypy.session.id = None
    #cherrypy.response.cookie["filelocker"] = cherrypy.session.id

def error(status, message, traceback, version):
    fl = cherrypy.thread_data.flDict['app']
    currentYear = datetime.date.today().year
    footerText = str(Template(file=fl.get_template_file('footer_text.tmpl'), searchList=[locals(),globals()]))
    tpl = str(Template(file=fl.get_template_file('error.tmpl'), searchList=[locals(),globals()]))
    return tpl
    
def split_list_sanitized(cs_list):
    cleanList = []
    if cs_list is not None:
        for listItem in cs_list.split(','):
            if listItem is not None and listItem !="":
                cleanList.append(strip_tags(listItem))
    return cleanList 

def get_temp_file():
    fl = cherrypy.thread_data.flDict['app']
    fileList, filePrefix, fileSuffix = os.listdir(fl.vault), "[%s]fltmp" % str(fl.clusterMemberId), ".tmp"
    randomNumber = random.randint(1, 1000000)
    tempFileName = os.path.join(fl.vault, filePrefix + str(randomNumber) + fileSuffix)
    while tempFileName in fileList:
        random.seed(fileNotes)
        randomNumber = random.randint(1, 1000000)
        tempFileName = os.path.join(fl.vault, filePrefix + str(randomNumber) + fileSuffix)
    file_object = open(tempFileName, "wb")
    return file_object
    
class myFieldStorage(cherrypy._cpcgifs.FieldStorage):
    def __del__(self, *args, **kwargs):
        try:
            uploadKey = None
            if cherrypy.session.has_key("user"):
                uploadKey = cherrypy.session.get('user').userId
            elif cherrypy.session.has_key("uploadTicket"):
                uploadKey = cherrypy.session.has_key("uploadTicket").ownerId+":"+cherrypy.session.has_key("uploadTicket").ticketId
            if cherrypy.file_uploads.has_key(uploadKey):
                for transfer in cherrypy.file_uploads[uploadKey]:
                    if transfer.file_object.name == self.file_location:
                        cherrypy.file_uploads[uploadKey].remove(transfer)
                if len(cherrypy.file_uploads[uploadKey]) == 0:
                    del cherrypy.file_uploads[uploadKey]
            if os.path.isfile(self.file_location):
                fl = cherrypy.thread_data.flDict['app']
                tempFileName = self.file_location.split(os.path.sep)[-1]
                fl.queue_for_deletion(tempFileName)
        except KeyError:
            pass
        except KeyError, ke:
            pass
        except AttributeError, ae:
            pass
        except OSError, oe:
            pass
        except Exception, e:
            pass
        
    def make_file(self, binary=None):
        if self.filename is not None:
            uploadIndex = None
            if cherrypy.request.headers.has_key("uploadindex"):
                uploadIndex = cherrypy.request.headers['uploadindex']
            fo = ProgressFile(self.bufsize, self.filename, uploadIndex=uploadIndex)
            self.file_location = fo.file_object.name
            uploadKey = None
            if cherrypy.session.has_key("uploadTicket"):
                uploadKey = cherrypy.session.get("uploadTicket").ownerId+":"+cherrypy.session.get("uploadTicket").ticketId
            elif cherrypy.session.has_key("user"):
                uploadKey = cherrypy.session.get('user').userId
            
            if cherrypy.file_uploads.has_key(uploadKey):
                cherrypy.file_uploads[uploadKey].append(fo)
            else:
                cherrypy.file_uploads[uploadKey] = [fo,]
            return fo
        else:
            return StringIO.StringIO("")

class ProgressFile(object):
    def __init__(self, buf, fileName, file_object=None, uploadIndex=None, sessionId=None, *args, **kwargs):
        if file_object is None:
            #self.file_object = tempfile.NamedTemporaryFile(*args, **kwargs)
            self.file_object = get_temp_file()
        else:
            self.file_object = file_object
        self.sessionId = sessionId
        self.fileName = fileName
        self.transferred = 0
        self.buf = buf
        lcHDRS = {}
        for key, val in cherrypy.request.headers.iteritems():
            lcHDRS[key.lower()] = val
        self.pre_sized = float(lcHDRS['content-length'])
        self.speed = 1
        self.remaining = 0
        self.eta = 0
        self.uploadIndex = uploadIndex
        self._start = time.time()
        self.status = "Uploading"
    def write(self, data):
        now = time.time()
        self.transferred += len(data)
        if (now - self._start) == 0:
            self.speed = 0
        else:
            self.speed = self.transferred / (now - self._start)
        self.remaining = self.pre_sized - self.transferred
        if self.speed == 0: self.eta = 9999999
        else: self.eta = self.remaining / self.speed
        return self.file_object.write(data)

    def seek(self, pos):
        self.post_sized = self.transferred
        self.transferred = True
        return self.file_object.seek(pos)

    def read(self, size):
        return self.file_object.read(size)
        
    def stat_dict(self):
        valDict = {}
        valDict['fileName'] = self.fileName
        valDict['speed'] = '%9.2f' % (self.speed / 1024.0)
        valDict['sizeKB'] = '%9.2f' % (self.pre_sized / 1024.0)
        valDict['transferredKB'] = '%9.2f' % (self.transferred / 1024.0)
        valDict['eta'] = str(int(self.eta))
        if self.uploadIndex is not None:
            if self.uploadIndex.isdigit():
                valDict['uploadIndex'] = self.uploadIndex
            else:
                valDict['uploadIndex'] = "\"%s\"" % self.uploadIndex
        valDict['status'] = self.status
        return valDict

def fl_connect(threadIndex): 
    # Create a Filelocker instance and store it in the current thread 
    flDict = {'app': Filelocker(cherrypy.request.app.config)} #This is silly, but necessary
    cherrypy.thread_data.flDict = flDict
    cherrypy.FLThreads.append(cherrypy.thread_data.flDict)
    cherrypy.thread_data.db = cherrypy.thread_data.flDict['app'].db.get_db()

def check_updates():
    config = cherrypy._cpconfig._Parser()
    config.read(cherrypy.configfile)
    confDict = config.as_dict()
    dbSession = False
    if cherrypy.config['tools.sessions.storage_type'] == "db":
        dbSession = True
    dbType = confDict['database']["dbtype"]
    dbHost = confDict['database']["dbhost"]
    dbUser = confDict['database']["dbuser"]
    dbPassword = confDict['database']["dbpassword"]
    dbName = confDict['database']["dbname"]
    db = dao_creator.get_dao(dbType, dbHost, dbUser, dbPassword, dbName)
    db.updateDB(FL_VERSION, dbSession)
    
def reconfig(configfile=None):
    config = cherrypy._cpconfig._Parser()
    if configfile is None:
        configfile = os.path.join("conf","filelocker.conf")
    config.read(configfile)
    fl = Filelocker(config.as_dict())
    authType = None
    hiddenPrefixes = []
    dirType = None
    mailAuth = False
    params = fl.db.getAllParameters()
    print "=====Filelocker configuration====="
    for param in params:
        prefix = param.parameterName.split("_")[0]
        if prefix not in hiddenPrefixes:
            print str(param)
            resp = raw_input("Desired value for %s[%s]?: " % (param.parameterName, param.value))
            if resp is not None and resp !="":
                param.value = resp
                fl.db.setParameter(param)
            if param.parameterName == "auth_type":
                authType = param.value
            if param.parameterName == "directory_type":
                dirType = param.value
            if dirType is not None and authType is not None:
                if authType != "cas":
                    hiddenPrefixes.append("cas")
                if authType != "ldap" and dirType != "ldap":
                    hiddenPrefixes.append("ldap")
                    
def midnightloghandler(fn, level, backups):
    from logging import handlers
    h = handlers.TimedRotatingFileHandler(fn, "midnight", 1, backupCount=backups)
    h.setLevel(level)
    h.setFormatter(cherrypy._cplogging.logfmt)
    return h
   
def start(configfile=None, daemonize=False, pidfile=None):
    config = cherrypy._cpconfig._Parser()
    cherrypy.config.update({'log.screen': False})
    if configfile is None:
        configfile = os.path.join(os.getcwd(),"conf","filelocker.conf")
    config.read(configfile)
    cherrypy.configfile = configfile
    cherrypy.config.update(configfile)
    cherrypy.FLThreads = [] #Build a list to hold the threads in a globally accessible fashion. This is necessary for on the fly config updates to take effect.
    logLevel = 40
    if config.as_dict()['filelocker'].has_key("loglevel"):
        logLevel = config.as_dict()['filelocker']['loglevel']
    if cherrypy.config['tools.sessions.storage_type'] == "db":
        from core.dao import MySQLDAO
        cherrypy.lib.sessions.DbSession = MySQLDAO.DbSession
    app = cherrypy.tree.mount(Root(), '/', config=configfile)
    #The following section handles the log rotation
    log = app.log
    log.error_file = "" 
    log.error_log.addHandler(midnightloghandler(cherrypy.config['log.error_file'], logLevel, 30))
    log.access_file = ""
    log.access_log.addHandler(midnightloghandler(cherrypy.config['log.access_file'], logging.INFO, 7))
    
    #This is just aliasing the engine for shorthand, from a code example
    engine = cherrypy.engine
    #Bind the error page to our custom one so it doesn't print a stack trace. The output of the error function is printed
    cherrypy.config.update({'error_page.default': error})
    # Only daemonize if asked to.
    if daemonize:
        # Don't print anything to stdout/sterr.
        plugins.Daemonizer(engine).subscribe()
    if pidfile is None:
            pidfile = os.path.join(os.getcwd(),"filelocker.pid")
    plugins.PIDFile(engine, pidfile).subscribe()
    #Build the DB connection threadpool
    engine.subscribe('start_thread', fl_connect) 
    #This was from the example
    if hasattr(engine, "signal_handler"):
        engine.signal_handler.subscribe()
    if hasattr(engine, "console_control_handler"):
        engine.console_control_handler.subscribe()
    
    try:
        #This line override the cgi Fieldstorage with the one we defined in order to track upload progress
        cherrypy._cpcgifs.FieldStorage = myFieldStorage
        cherrypy.server.socket_timeout = 60
        engine.start()
    except Exception, e:
        print "Exception when starting up: %s" % str(e)
        # Assume the error has been logged already via bus.log.
        sys.exit(1)
    else:
        #engine.block()
        pass
    
    try:
        #Now that CherryPy has started, perform maintenance...first check that the database is up to date
        check_updates()
        
        #Set hour counter to 0.0. We have daily maintenance for expirations and maintenance every 12 minutes for queued deletions, etc.
        hour = 0.0
        while True:
            threadLessFL = Filelocker(config.as_dict())
            maxSize = int(1024*1024*threadLessFL.maxFileUploadSize)
            #Set max file size, in bytes
            cherrypy.config.update({'server.max_request_body_size': maxSize})
            if threadLessFL.isClusterMaster:
                if hour == 0.0: #on startup and each new day
                    threadLessFL.check_expirations()
                    threadLessFL.delete_orphaned_files()
                threadLessFL.process_deletion_queue() #process deletion queue every 12 minutes
                if hour < 24.0:
                    hour += 0.2
                if hour >= 24.0:
                    hour = 0.0
            #Clean up stalled and invalid transfers
            #validSessionIds = []
            #sessionCache = {}
            #try:
                #cherrypy.lib.sessions.init()
                #cherrypy.session.acquire_lock()
                #if cherrypy.config['tools.sessions.storage_type'] == "db":
                    #sessionCache = cherrypy.session.get_all_sessions()
                #else:
                    #sessionCache = cherrypy.session.cache
                #cherrypy.session.release_lock()
            #except AttributeError, ae:
                #logging.error("No sessions built") #Sessions haven't been built yet
            #for key in cherrypy.file_uploads.keys():
                #pass
                #for progressFile in cherrypy.file_uploads[key]:
                    #if progressFile.sessionId not in validSessionIds:
                        #cherrypy.file_uploads[key].remove(progressFile)
            #Cleanup orphaned temp files, possibly resulting from stalled transfers
            validTempFiles = []
            for key in cherrypy.file_uploads.keys():
                for progressFile in cherrypy.file_uploads[key]:
                    validTempFiles.append(progressFile.file_object.name.split(os.path.sep)[-1])
            threadLessFL.clean_temp_files(validTempFiles)
            threadLessFL = None #This is so that config changes will be absorbed during the next maintenance cycle
            time.sleep(720) #12 minutes
    except KeyboardInterrupt, ki:
        logging.error("Keyboard interrupt")
        engine.exit()
        sys.exit(1)
    except Exception, e:
        logging.error("Exception: %s" % str(e))
        logging.critical("Failed to start up Filelocker: %s" % str(e))
        engine.exit()
        sys.exit(1)

def stop(pidfile=None):
    if pidfile is None:
        pidfile = os.path.join(os.getcwd(),"filelocker.pid")
    if os.path.isfile(pidfile):
        FILE = open(pidfile, 'r')
        pid = int(FILE.read().strip())
        FILE.close()
        try:
            os.kill(pid, signal.SIGTERM)
        except os.error, args:
            if args[0] != errno.ESRCH: # NO SUCH PROCESS
                print "Error stopping: %s\n" % str(args[0])
            else:
                print "Stale PID file, removing...No such process\n"
        except Exception, e:
            print "Error stopping: %s\n" % str(e)
        else:
            os.kill(pid, 9)

if __name__ == '__main__':
    from optparse import OptionParser
    
    p = OptionParser()
    p.add_option('-c', '--config', dest='configfile',
                 help="specify config file")
    p.add_option('-d', action="store_true", dest='daemonize',
                 help="run the server as a daemon")
    p.add_option('-p', '--pidfile', dest='pidfile', default=None,
                 help="store the process id in the given file")
    p.add_option('-a','--action', dest='action', default="start", help="action to perform (start, stop, restart, reconfig)")
    options, args = p.parse_args()
    
    if options.action:
        if options.action == "stop":
            stop(options.pidfile)
        elif options.action == "restart":
            stop(options.pidfile)
            start(options.configfile, options.daemonize, options.pidfile)
        elif options.action == "reconfig":
            reconfig(options.configfile)
        elif options.action == "start":
            start(options.configfile, options.daemonize, options.pidfile)
        elif options.action == "rebuild_static":
            pass #Future use: combine/minify JS and CSS
    else:
        start(options.configfile, options.daemonize, options.pidfile)
