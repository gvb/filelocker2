import cherrypy
__author__="wbdavis"
__date__ ="$Sep 25, 2011 9:09:40 PM$"

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
    cherrypy.tools.requires_login = cherrypy.Tool('before_request_body', requires_login, priority=70)
    cherrypy.tools.before_upload = cherrypy.Tool('before_request_body', before_upload, priority=71)
    cherrypy.file_uploads = dict()
    cherrypy.file_downloads = dict()
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
