import lib.Models
import os
import sys
import signal
import errno
import cherrypy
import logging
from Cheetah.Template import Template
from lib.SQLAlchemyTool import configure_session_for_app, session
from lib.Models import *
#from dao import dao_creator
__author__="wbdavis"
__date__ ="$Sep 25, 2011 9:09:40 PM$"
__version__ = "2.6"
def before_upload(**kwargs):
    fl, user, sMessages, fMessages, uploadTicket = None, None, None, None, None
    if cherrypy.session.has_key("uploadTicket") and cherrypy.session.get("uploadTicket") is not None:
        uploadTicket = cherrypy.session.get("uploadTicket")
        #fl = Filelocker(cherrypy.request.app.config)
        fl = cherrypy.thread_data.flDict['app']
        user = fl.get_user(uploadTicket.ownerId)
    else:
        requires_login()
        user, fl, sMessages, fMessages = cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], cherrypy.session.get("sMessages"), cherrypy.session.get("fMessages")
    vaultSpaceFreeMB, vaultCapacityMB = fl.get_vault_usage()
    cherrypy.response.timeout = 86400
    lcHDRS = {}
    for key, val in cherrypy.request.headers.iteritems():
        lcHDRS[key.lower()] = val
    # at this point we could limit the upload on content-length...
    try:
        fileSizeBytes = int(lcHDRS['content-length'])
    except KeyError, ke:
        fMessages.append("Request must have a valid content length")
        raise HTTPError(411, "Request must have a valid content length")
    fileSizeMB = ((fileSizeBytes/1024)/1024)
    quotaSpaceRemainingBytes = (user.userQuota*1024*1024) - int(fl.get_user_quota_usage(user, user.userId))
    if (fileSizeMB*2) >= vaultSpaceFreeMB:
        logging.critical("[system] [beforeUpload] [File vault is running out of space and cannot fit this file. Remaining Space is %s MB, fileSizeBytes is %s]" % (vaultSpaceFreeMB, fileSizeBytes))
        fMessages.append("The server doesn't have enough space left on its drive to fit this file. The administrator has been notified.")
        raise HTTPError(413, "The server doesn't have enough space left on its drive to fit this file. The administrator has been notified.")
    if fileSizeMB > fl.maxFileUploadSize:
        logging.debug("[system] [beforeUpload] [File exceeded maximum allowed upload size, rejected]")
        fMessages.append("File is too large for server to process.")
        raise HTTPError(413, "File is too large for server to process.")
    if fileSizeBytes > quotaSpaceRemainingBytes:
        fMessages.append("File size is larger than your quota will accomodate")
        raise HTTPError(413, "File size is larger than your quota will accomodate")
    cherrypy.request.process_request_body = False
    
def requires_login(**kwargs):
    format = None
    fl = cherrypy.thread_data.flDict['app']
    if cherrypy.request.params.has_key("format"):
        format = cherrypy.request.params['format']
    if cherrypy.session.has_key("user") and cherrypy.session.get('user') is not None:
        if cherrypy.session.get('user').userTosAcceptDatetime == None:
            raise cherrypy.HTTPRedirect(fl.rootURL+"/sign_tos")
        else:
            pass
    else:
        if fl.authType == "cas":
            if cherrypy.request.params.has_key("ticket"):
                valid_ticket, userId = fl.CAS.validate_ticket(fl.rootURL, cherrypy.request.params['ticket'])
                if valid_ticket:
                    currentUser = fl.get_user(userId, True)
                    if currentUser is None:
                        currentUser = fl.directory.lookup_user(userId) #Try to get user info from directory
                        if currentUser is not None:
                            fl.install_user(currentUser)
                        else:
                            logging.error("[system] [installUser] [User not found in directory lookup - installing with defaults]")
                            currentUser = User("Guest", "Guest", "Unknown", None, None, None, userId)
                            currentUser.userDisplayName = "Guest"
                            fl.install_user(currentUser)
                        currentUser = fl.get_user(userId, True)
                    if currentUser.authorized == False:
                        raise cherrypy.HTTPError(403, "Your user account does not have access to this system.")
                    cherrypy.session["user"], cherrypy.session['original_user'], cherrypy.session['sMessages'], cherrypy.session['fMessages'] = currentUser, currentUser, [], []
                    fl.record_login(cherrypy.session.get("user"), cherrypy.request.remote.ip)
                    if currentUser.userTosAcceptDatetime is None:
                        raise cherrypy.HTTPRedirect(fl.rootURL+"/sign_tos")
                    raise cherrypy.HTTPRedirect(fl.rootURL)
                else:
                    raise cherrypy.HTTPError(403, "Invalid CAS Ticket. If you copied and pasted the URL for this server, you might need to remove the 'ticket' parameter from the URL.")
            else:
                if format=="json":
                    raise cherrypy.HTTPRedirect(fl.rootURL+"/expired_json")
                elif format=="text":
                    raise cherrypy.HTTPRedirect(fl.rootURL+"/expired_text")
                else:
                    raise cherrypy.HTTPRedirect(fl.CAS.login_url(fl.rootURL))
        else:
            if format=="json":
                raise cherrypy.HTTPRedirect(fl.rootURL+"/expired_json")
            elif format=="text":
                raise cherrypy.HTTPRedirect(fl.rootURL+"/expired_text")
            else:
                raise cherrypy.HTTPRedirect(fl.rootURL+"/login")
def fl_connect(threadIndex):
    # Create a Filelocker instance and store it in the current thread
    flDict = {'app': Filelocker(cherrypy.request.app.config)} #This is silly, but necessary
    cherrypy.thread_data.flDict = flDict
    cherrypy.FLThreads.append(cherrypy.thread_data.flDict)
    cherrypy.thread_data.db = cherrypy.thread_data.flDict['app'].db.get_db()
    
def error(status, message, traceback, version):
    fl = cherrypy.thread_data.flDict['app']
    currentYear = datetime.date.today().year
    footerText = str(Template(file=fl.get_template_file('footer_text.tmpl'), searchList=[locals(),globals()]))
    tpl = str(Template(file=fl.get_template_file('error.tmpl'), searchList=[locals(),globals()]))
    return tpl

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
    db.updateDB(__version__, dbSession)

#def reconfig(configfile=None):
#    config = cherrypy._cpconfig._Parser()
#    if configfile is None:
#        configfile = os.path.join("conf","filelocker.conf")
#    config.read(configfile)
#    fl = Filelocker(config.as_dict())
#    authType = None
#    hiddenPrefixes = []
#    dirType = None
#    mailAuth = False
#    params = fl.db.getAllParameters()
#    print "=====Filelocker configuration====="
#    for param in params:
#        prefix = param.parameterName.split("_")[0]
#        if prefix not in hiddenPrefixes:
#            print str(param)
#            resp = raw_input("Desired value for %s[%s]?: " % (param.parameterName, param.value))
#            if resp is not None and resp !="":
#                param.value = resp
#                fl.db.setParameter(param)
#            if param.parameterName == "auth_type":
#                authType = param.value
#            if param.parameterName == "directory_type":
#                dirType = param.value
#            if dirType is not None and authType is not None:
#                if authType != "cas":
#                    hiddenPrefixes.append("cas")
#                if authType != "ldap" and dirType != "ldap":
#                    hiddenPrefixes.append("ldap")

def midnightloghandler(fn, level, backups):
    from logging import handlers
    h = handlers.TimedRotatingFileHandler(fn, "midnight", 1, backupCount=backups)
    h.setLevel(level)
    h.setFormatter(cherrypy._cplogging.logfmt)
    return h

cherrypy.tools.requires_login = cherrypy.Tool('before_request_body', requires_login, priority=70)
cherrypy.tools.before_upload = cherrypy.Tool('before_request_body', before_upload, priority=71)
def start(configfile=None, daemonize=False, pidfile=None):
    cherrypy.file_uploads = dict()
    cherrypy.file_downloads = dict()
    config = cherrypy._cpconfig._Parser()
    cherrypy.config.update({'log.screen': False})
    if configfile is None:
        configfile = os.path.join(os.getcwd(),"etc","filelocker.conf")
    config.read(configfile)
    cherrypy.configfile = configfile
    cherrypy.config.update(configfile)
    logLevel = 40
    if config.as_dict()['filelocker'].has_key("loglevel"):
        logLevel = config.as_dict()['filelocker']['loglevel']
#    if cherrypy.config['tools.sessions.storage_type'] == "db":
#        from dao import MySQLDAO
#        cherrypy.lib.sessions.DbSession = MySQLDAO.DbSession
    from controller.RootController import RootController
    app = cherrypy.tree.mount(RootController(), '/', config=configfile)
    
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
    cherrypy.process.plugins.PIDFile(engine, pidfile).subscribe()
    #This was from the example
    if hasattr(engine, "signal_handler"):
        engine.signal_handler.subscribe()
    if hasattr(engine, "console_control_handler"):
        engine.console_control_handler.subscribe()
    
    try:
        #This line override the cgi Fieldstorage with the one we defined in order to track upload progress
        from model.FileFieldStorage import FileFieldStorage
        cherrypy._cpcgifs.FieldStorage = FileFieldStorage
        cherrypy.server.socket_timeout = 60
        engine.start()
        configure_session_for_app(app)
    except Exception, e:
        print "Exception when starting up: %s" % str(e)
        # Assume the error has been logged already via bus.log.
        sys.exit(1)
    else:
        #engine.block()
        pass

#    try:
    from controller.FileController import FileController

    #Now that CherryPy has started, perform maintenance...first check that the database is up to date
    #check_updates()

    #Set hour counter to 0.0. We have daily maintenance for expirations and maintenance every 12 minutes for queued deletions, etc.
    hour = 0.0
    fileController = FileController()
    while True:
        #Set max file size, in bytes
        query = session.query(ConfigParameter).filter(ConfigParameter.config_parameter_name == "max_file_size")
        maxSizeParam = query.one()
        maxSize = long(maxSizeParam.config_parameter_value)
        cherrypy.config.update({'server.max_request_body_size': maxSize})
        logging.error("Just updated the max size to %s" % maxSize)
        if config.as_dict()['filelocker'].has_key("clustermaster") and config.as_dict()["filelocker"]["clustermaster"]: # This will allow you set up other front ends that don't run maintenance on the DB or FS
            if hour == 0.0: #on startup and each new day
                fileController.check_expirations()
                logging.error("Expirations checked")
                fileController.delete_orphaned_files()
            fileController.process_deletion_queue() #process deletion queue every 12 minutes
            if hour < 24.0:
                hour += 0.2
            if hour >= 24.0:
                hour = 0.0
        #Cleanup orphaned temp files, possibly resulting from stalled transfers
        validTempFiles = []
        for key in cherrypy.file_uploads.keys():
            for progressFile in cherrypy.file_uploads[key]:
                validTempFiles.append(progressFile.file_object.name.split(os.path.sep)[-1])
        fileController.clean_temp_files(validTempFiles)
        time.sleep(720) #12 minutes
#    except KeyboardInterrupt, ki:
#        logging.error("Keyboard interrupt")
#        engine.exit()
#        sys.exit(1)
#    except Exception, e:
#        logging.error("Exception: %s" % str(e))
#        logging.critical("Failed to start up Filelocker: %s" % str(e))
#        engine.exit()
#        sys.exit(1)

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
            
def build_database(configfile=None):
    config = cherrypy._cpconfig._Parser()
    cherrypy.config.update({'log.screen': False})
    if configfile is None:
        configfile = os.path.join(os.getcwd(),"etc","filelocker.conf")
    config.read(configfile)
    if config.as_dict()['/'].has_key("tools.SATransaction.dburi"):
        dburi = config.as_dict()['/']["tools.SATransaction.dburi"]
        lib.Models.create_database_tables(dburi)
    print "Created Database"
    
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
        elif options.action == "build_db":
            build_database(options.configfile)
        elif options.action == "reconfig":
            reconfig(options.configfile)
        elif options.action == "start":
            start(options.configfile, options.daemonize, options.pidfile)
        elif options.action == "rebuild_static":
            pass #Future use: combine/minify JS and CSS
    else:
        start(options.configfile, options.daemonize, options.pidfile)
