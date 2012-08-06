# -*- coding: utf-8 -*-
__author__="wbdavis"
__date__ ="$Sep 25, 2011 9:09:40 PM$"
__version__ = "2.6"
import sys
import ConfigParser
import os
import time
import signal
import errno
import logging
import datetime
import cherrypy
from cherrypy.process import plugins
from Cheetah.Template import Template
from lib.SQLAlchemyTool import configure_session_for_app, session
import sqlalchemy
from lib import FileService
from lib.CAS import CAS
from lib.Constants import Actions
from lib.Models import *
from lib.Formatters import *

cherrypy.server.max_request_body_size = 0
def before_upload(**kwargs):
    cherrypy.request.process_request_body = False
cherrypy.tools.before_upload = cherrypy.Tool('before_request_body', before_upload, priority=71)

def requires_login(permissionId=None, **kwargs):
    from lib import AccountService
    format, rootURL = None, cherrypy.request.app.config['filelocker']['root_url']
    if cherrypy.request.params.has_key("format"):
        format = cherrypy.request.params['format']
    if cherrypy.session.has_key("user") and cherrypy.session.get('user') is not None:
        user = cherrypy.session.get('user')
        if user.date_tos_accept == None:
            raise cherrypy.HTTPRedirect(rootURL+"/sign_tos")
        elif permissionId is not None:
            if AccountService.user_has_permission(user, permissionId)==False:
                raise HTTPError(403)
        else:
            pass
    else:
        authType = session.query(ConfigParameter).filter(ConfigParameter.name=="auth_type").one().value
        if authType == "cas":
            casUrl = session.query(ConfigParameter).filter(ConfigParameter.name=="cas_url").one().value
            casConnector = CAS(casUrl)
            if cherrypy.request.params.has_key("ticket"):
                valid_ticket, userId = casConnector.validate_ticket(rootURL, cherrypy.request.params['ticket'])
                if valid_ticket:
                    currentUser = AccountService.get_user(userId, True)
                    if currentUser is None:
                        currentUser = User(id=userId, display_name="Guest user", first_name="Unknown", last_name="Unknown")
                        cherrypy.log.error("[%s] [requires_login] [User authenticated, but not found in directory - installing with defaults]"%str(userId))
                        AccountService.install_user(currentUser)
                        currentUser = AccountService.get_user(currentUser.id, True) #To populate attributes
                    if currentUser.authorized == False:
                        raise cherrypy.HTTPError(403, "Your user account does not have access to this system.")
                    session.add(AuditLog(currentUser.id, "Login", "User %s logged in successfully from IP %s" % (currentUser.id, cherrypy.request.remote.ip)))

                    session.commit()
                    if currentUser.date_tos_accept is None:
                        if format == None:
                            raise cherrypy.HTTPRedirect(rootURL+"/sign_tos")
                        else:
                            raise cherrypy.HTTPError(401)
                    raise cherrypy.HTTPRedirect(rootURL)
                else:
                    raise cherrypy.HTTPError(403, "Invalid CAS Ticket. If you copied and pasted the URL for this server, you might need to remove the 'ticket' parameter from the URL.")
            else:
                if format == None:
                    raise cherrypy.HTTPRedirect(casConnector.login_url(rootURL))
                else:
                    raise cherrypy.HTTPError(401)
        else:
            if format == None:
                raise cherrypy.HTTPRedirect(rootURL+"/login")
            else:
                raise cherrypy.HTTPError(401)
cherrypy.tools.requires_login = cherrypy.Tool('before_request_body', requires_login, priority=70)

def error(status, message, traceback, version):
    currentYear = datetime.date.today().year
    config = cherrypy.request.app.config['filelocker']
    orgConfig = get_config_dict_from_objects(session.query(ConfigParameter).filter(ConfigParameter.name.like('org_%')).all())
    footerText = str(Template(file=get_template_file('footer_text.tmpl'), searchList=[locals(),globals()]))
    tpl = str(Template(file=get_template_file('error.tmpl'), searchList=[locals(),globals()]))
    return tpl

def cluster_elections(config):
    try:
        currentNodeId = int(config['filelocker']['cluster_member_id'])
        currentNode = session.query(ClusterNode).filter(ClusterNode.member_id == currentNodeId).scalar()
        if currentNode is None: #This node isn't in the DB yet, check in
            import socket
            currentNode = ClusterNode(member_id=currentNodeId, hostname=socket.gethostname(), is_master=False, last_seen_timestamp=datetime.datetime.now())
            session.add(currentNode)
            session.commit()
        else: #In the DB, update last seen to avoid purging
            currentNode.last_seen_timestamp = datetime.datetime.now()
            session.commit()
        currentMaster = session.query(ClusterNode).filter(ClusterNode.is_master==True).scalar()
        #If this is default master node and another node has assumed master, reset and force election
        if currentNodeId==0 and currentNode.is_master == False and currentMaster is not None:
            for node in session.query(ClusterNode).all():
                node.is_master = False
            session.commit()
        #This isn't the default master, there is one, but it's expired
        elif currentMaster is not None and currentMaster.last_seen_timestamp < datetime.datetime.now()-datetime.timedelta(minutes=5): #master is expired
            session.delete(currentMaster)
            session.commit()
        #No master, hold election
        elif currentMaster is None: #No master nodes found, become master if eligible
            purge_expired_nodes()
            highestPriority = currentNode.member_id
            for node in session.query(ClusterNode).all():
                if node.member_id < highestPriority:
                    highestPriority = node.member_id
                    break
            if highestPriority == currentNode.member_id: #Current node has lowest node id, thus highest priority, assume master
                currentNode.is_master = True
                session.commit()
        return True
    except sqlalchemy.orm.exc.ConcurrentModificationError, cme:
        cherrypy.log.error("[system] [cluster_elections] [Concurrency error during elections. This can occur if locks on the DB inhibit normal cluster elections. If this error occurs infrequently, it can usually be disregarded. Full Error: %s]" % str(cme))
        session.rollback()
        return False
    except Exception, e:
        cherrypy.log.error("[system] [cluster_elections] [Concurrency error during elections. This can occur if locks on the DB inhibit normal cluster elections. If this error occurs infrequently, it can usually be disregarded. Full Error: %s]" % str(cme))
        session.rollback()
        return False
        
def purge_expired_nodes():
    #Clean node table, check for master, if none run election
    expirationTime = datetime.datetime.now()-datetime.timedelta(minutes=5)
    expiredNodes = session.query(ClusterNode).filter(ClusterNode.last_seen_timestamp < expirationTime).all()
    for node in expiredNodes:
        session.delete(node)
    session.commit()

def clean_temp_files(config):
    #Cleanup orphaned temp files, possibly resulting from stalled transfers
    validTempFiles = []
    for key in cherrypy.file_uploads.keys():
        for progressFile in cherrypy.file_uploads[key]:
            validTempFiles.append(progressFile.file_object.name.split(os.path.sep)[-1])
    FileService.clean_temp_files(config, validTempFiles)
    
def routine_maintenance(config):
    from lib import AccountService
    expiredFiles = session.query(File).filter(File.date_expires < datetime.datetime.now())
    for flFile in expiredFiles:
        try:
            for share in flFile.user_shares:
                session.delete(share)
            for share in flFile.group_shares:
                session.delete(share)
            for share in flFile.public_shares:
                session.delete(share)
            for share in flFile.attribute_shares:
                session.delete(share)
            FileService.queue_for_deletion(flFile.id)
            session.add(AuditLog("admin", Actions.DELETE_FILE, "File %s (ID:%s) has expired and has been purged by the system." % (flFile.name, flFile.id), flFile.owner_id))
            session.delete(flFile)
            session.commit()
        except Exception, e:
            session.rollback()
            cherrypy.log.error("[system] [routine_maintenance] [Error while deleting expired file: %s]" % str(e))
    expiredMessages = session.query(Message).filter(Message.date_expires < datetime.datetime.now())
    for message in expiredMessages:
        try:
            session.delete(message)
            FileService.queue_for_deletion("m%s" % str(message.id))
            session.add(AuditLog("admin", Actions.DELETE_MESSAGE, "Message %s (ID:%s) has expired and has been deleted by the system." % (message.messageSubject, message.messageId), message.owner_id))
            session.commit()
        except Exception, e:
            session.rollback()
            cherrypy.log.error("[system] [routine_maintenance] [Error while deleting expired message: %s]" % str(e))
    expiredUploadRequests = session.query(UploadRequest).filter(UploadRequest.date_expires < datetime.datetime.now())
    for uploadRequest in expiredUploadRequests:
        try:
            session.delete(uploadRequest)
            session.add(AuditLog("system", Actions.DELETE_UPLOAD_REQUEST, "Upload request %s has expired." % uploadRequest.id, uploadRequest.owner_id))
            session.commit()
        except Exception, e:
            cherrypy.log.error("[system] [routine_maintenance] [Error while deleting expired upload request: %s]" % (str(e)))
    maxUserDays = int(session.query(ConfigParameter).filter(ConfigParameter.name=="user_inactivity_expiration").one().value)
    expiredUsers = session.query(User).filter(and_(User.date_last_login < (datetime.date.today() - datetime.timedelta(days=maxUserDays)), User.id!= "admin"))
    
    for user in expiredUsers:
        if AccountService.user_has_permission(user, "admin") == False and AccountService.user_has_permission(user, "expiration_exempt") == False:
            cherrypy.log.error("Purging user %s" % user.id)
            session.delete(user)
            session.add(AuditLog("admin", Actions.DELETE_USER, "User %s was deleted due to inactivity. All files and shares associated with this user have been purged as well" % str(user.id)))
            session.commit()

    for ps in session.query(PublicShare).all():
        if len(ps.files) == 0:
            session.delete(ps)
            session.add(AuditLog("admin", Actions.DELETE_PUBLIC_SHARE, "Public share %s owned by %s had no files and was deleted by maintenance" % (ps.id, ps.owner_id if ps.role_owner_id is None else ps.role_owner_id)))
    session.commit()

    vaultFileList = os.listdir(config['filelocker']['vault'] )
    for fileName in vaultFileList:
        try:
            if fileName.endswith(".tmp")==False and fileName.startswith(".") == False and fileName !="custom": #this is a file id, not a temp file
                if fileName.startswith("m"):
                    messageId = fileName.split("m")[1]
                    try:
                        session.query(Message).filter(Message.id==messageId).one()
                    except sqlalchemy.orm.exc.NoResultFound, nrf:
                        FileService.queue_for_deletion(fileName)
                else:
                    try:
                        fileId = int(fileName)
                        try:
                            session.query(File).filter(File.id==fileId).one()
                        except sqlalchemy.orm.exc.NoResultFound, nrf:
                            FileService.queue_for_deletion(fileName)
                    except Exception, e:
                        cherrypy.log.error("There was a file that did not match Filelocker's naming convention in the vault: %s. It has not been purged." % fileName)
        except Exception, e:
            cherrypy.log.error("[system] [routine_maintenance] [There was a problem while trying to delete an orphaned file %s: %s]" % (str(fileName), str(e)))
            session.rollback()

def midnightloghandler(fn, level, backups):
    from logging import handlers
    h = handlers.TimedRotatingFileHandler(fn, "midnight", 1, backupCount=backups)
    h.setLevel(level)
    h.setFormatter(cherrypy._cplogging.logfmt)
    return h


def start(configfile=None, daemonize=False, pidfile=None):
    cherrypy.file_uploads = dict()
    cherrypy.file_downloads = dict()
    if configfile is None:
        configfile = os.path.join(os.getcwd(),"etc","filelocker.conf")
    cherrypy.config.update(configfile)
    logLevel = 40

    from controller import RootController
    app = cherrypy.tree.mount(RootController.RootController(), '/', config=configfile)
    
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
    
    #This line override the cgi Fieldstorage with the one we defined in order to track upload progress
    try:
        class FileRequestBody(cherrypy._cpreqbody.RequestBody):
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
                        tempFileName = self.file_location.split(os.path.sep)[-1]
                        FileService.queue_for_deletion(tempFileName)
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
                    if cherrypy.session.has_key("uploadRequest"):
                        uploadKey = cherrypy.session.get("uploadRequest").owner_id+":"+cherrypy.session.get("uploadRequest").id
                    elif cherrypy.session.has_key("user"):
                        uploadKey = cherrypy.session.get('user').id

                    if cherrypy.file_uploads.has_key(uploadKey):
                        cherrypy.file_uploads[uploadKey].append(fo)
                    else:
                        cherrypy.file_uploads[uploadKey] = [fo,]
                    return fo
                else:
                    return StringIO.StringIO("")
        cherrypy._cpreqbody.RequestBody = FileRequestBody
    except Exception:
        class FileFieldStorage(cherrypy._cpcgifs.FieldStorage):
            def __del__(self, *args, **kwargs):
                try:
                    uploadKey = None
                    if cherrypy.session.has_key("user"):
                        uploadKey = cherrypy.session.get('user').id
                    elif cherrypy.session.has_key("uploadRequest"):
                        uploadKey = cherrypy.session.has_key("uploadRequest").owner_id+":"+cherrypy.session.has_key("uploadRequest").id
                    if cherrypy.file_uploads.has_key(uploadKey):
                        for transfer in cherrypy.file_uploads[uploadKey]:
                            if transfer.file_object.name == self.file_location:
                                cherrypy.file_uploads[uploadKey].remove(transfer)
                        if len(cherrypy.file_uploads[uploadKey]) == 0:
                            del cherrypy.file_uploads[uploadKey]
                    if os.path.isfile(self.file_location):
                        tempFileName = self.file_location.split(os.path.sep)[-1]
                        FileService.queue_for_deletion(tempFileName)
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
        cherrypy._cpcgifs.FieldStorage = FileFieldStorage
        
    engine.start()
    configure_session_for_app(app)
    app.config['filelocker']['version'] = __version__
    #Set max file size upload size, in bytes
    try:
        maxSizeParam = session.query(ConfigParameter).filter(ConfigParameter.name == "max_file_size").one()
        maxSize = long(maxSizeParam.value)
        cherrypy.config.update({'server.max_request_body_size': maxSize*1024*1024})
    except Exception, e:
        cherrypy.log.error("[system] [maintenance] [Problem setting max file size: %s]" % str(e))

    #Maintenance Loop
    try:
        while True:
            if cluster_elections(app.config): #only run the  
                try:                
                    currentNode = session.query(ClusterNode).filter(ClusterNode.member_id==int(app.config['filelocker']["cluster_member_id"])).one()
                    if currentNode.is_master: # This will allow you set up other front ends that don't run maintenance on the DB or FS
                        purge_expired_nodes()
                        routine_maintenance(app.config)
                        FileService.process_deletion_queue(app.config) #process deletion queue every 12 minutes
                except Exception, e:
                    cherrypy.log.error("[system] [maintenance] [There was a problem loading data for node[%s]: %s\nIf this message appears repeatedly there could be a problem with the election process. Verify that each cluster node has a unique ID in the config.]" % (app.config['filelocker']["cluster_member_id"], str(e)))
            
            try:
                clean_temp_files(app.config)
            except Exception, e:
                cherrypy.log.error("[system] [maintenance] [There was an error while cleaning temp files: %s]" % str(e))
            
            time.sleep(60) #Sleep 15 seconds after everything is done
    except KeyboardInterrupt, ki:
        print "Keyboard Interrupt"
        cherrypy.log.error("Keyboard interrupt")
        engine.exit()
        sys.exit(1)
    except Exception, e:
        print "Exception in maintenance loop: %s" % str(e)
        cherrypy.log.error("Exception in maintenance loop: %s" % str(e))
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

def check_updates(config):
    if config.has_key("database"):
        proceed = raw_input("""You appear to have an outdated style of config file and database schema.
        Would you like to attempt to automatically port the database and config?[y/n]: """ )
        if proceed.lower().startswith("y"):
            confirm = raw_input("""\n(WARNING: This will completely
        rebuild your current database by backing up your current data and rebuilding the tables. If this process is interrupted,
        all user data may be lost. You can manually run a DB backup from the Filelocker.py executable by using the syntax \n
        $> Filelocker.py -a backup_db\n\nThis command generates an XML data dump that can be imported later.)\n
        Proceed with in place upgrade?[y/n]: """)
            if confirm.lower().startswith("y"):
                dburi = "mysql+mysqldb://%s:%s@%s/%s" % (config['database']['dbuser'], config['database']['dbpassword'], config['database']['dbhost'], config['database']['dbname'] )
                backupFile = port_database(config, config['database']['dbhost'], config['database']['dbuser'], config['database']['dbpassword'],config['database']['dbname'])
                print "Backup complete. Rebuilding database..."
                build_database(dburi)
                print "Filelocker requires an admin account to be set. You will now be prompted to create a local password for the local admin account"
                create_admin(dburi)



    
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

    dburi = None
    configParser = ConfigParser.SafeConfigParser()
    if options.configfile is not None:
        configParser.read(options.configfile)
    else:
        configfile = os.path.join(os.getcwd(),"etc","filelocker.conf")
        if os.path.exists(configfile)==False:
            configfile = os.path.join("/","etc","filelocker.conf")
        if os.path.exists(configfile)==False:
            raise Exception("Could not find config file, please specify one using the -c option")
        configParser.read(configfile)
    dburi = configParser.get("/","tools.SATransaction.dburi").replace("\"", "").replace("'","")

    if options.action:
        if options.action == "stop":
            stop(options.pidfile)
        elif options.action == "restart":
            stop(options.pidfile)
            start(options.configfile, options.daemonize, options.pidfile)
        elif options.action == "start":
            start(options.configfile, options.daemonize, options.pidfile)
    else:
        start(options.configfile, options.daemonize, options.pidfile)
