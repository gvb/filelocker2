import cherrypy
import re
import os
import logging
from Cheetah.Template import Template
import ShareController
from controller.FileController import FileController
from controller.AccountController import AccountController
from controller.MessageController import MessageController
from controller.AdminController import AdminController
from lib.Formatters import *
__author__="wbdavis"
__date__ ="$Sep 25, 2011 9:36:56 PM$"

class RootController:
    share_interface = ShareController
    file_interface = FileController
    account_interface = AccountController
    admin_interface = AdminController
    message_interface = MessageController
    #DropPrivileges(cherrypy.engine, umask=077, uid='nobody', gid='nogroup').subscribe()

    def __init__(self):
        pass

    @cherrypy.expose
    def local(self, **kwargs):
        return self.login(authType="local")

    @cherrypy.expose
    def login(self, **kwargs):
        msg, errorMessage, authType, rootURL = ( None, None, None, cherrypy.request.app.config['filelocker']['root_url'])
        if kwargs.has_key("msg"):
            msg = kwargs['msg']
        if kwargs.has_key("authType"):
            authType = kwargs['authType']
        loginPage = fl.rootURL + "/process_login"
        if msg is not None and str(strip_tags(msg))=="1":
            errorMessage = "Invalid username or password"
        elif msg is not None and str(strip_tags(msg))=="2":
            errorMessage = "You have been logged out of the application"
        elif msg is not None and str(strip_tags(msg))=="3":
            errorMessage = "Password cannot be blank"
        if authType is None:
            authType = cherrypy.request.app.config['filelocker']['auth_type']
        if authType == "cas":
            pass
        elif authType == "ldap" or authType == "local":
            currentYear = datetime.date.today().year
            footerText = str(Template(file=get_template_file('footer_text.tmpl'), searchList=[locals(),globals()]))
            tpl = Template(file=get_template_file('login.tmpl'), searchList=[locals(),globals()])
            return str(tpl)
        else:
            logging.error("[system] [login] [No authentication variable set in config]")
            raise cherrypy.HTTPError(403, "No authentication mechanism")

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def logout(self):
        if cherrypy.request.app.config['filelocker']['auth_type'] == "cas":
            casLogoutUrl =  fl.CAS.logout_url()+"?redirectUrl="+fl.rootURL+"/logout_cas"
            currentYear = datetime.date.today().year
            footerText = str(Template(file=fl.get_template_file('footer_text.tmpl'), searchList=[locals(),globals()]))
            tpl = Template(file=fl.get_template_file('cas_logout.tmpl'), searchList=[locals(), globals()])
            cherrypy.session['user'], cherrypy.response.cookie['filelocker']['expires'] = None, 0
            return str(tpl)
        else:
            cherrypy.session['user'], cherrypy.response.cookie['filelocker']['expires'] = None, 0
            raise cherrypy.HTTPRedirect(fl.rootURL+'/login?msg=2')

    @cherrypy.expose
    def logout_cas(self):
        from lib.CAS import CAS
        orgURL = cherrypy.response.cookie['filelocker']['org_url']
        orgName = cherrypy.response.cookie['filelocker']['org_name']
        rootURL = cherrypy.response.cookie['filelocker']['root_url']
        currentYear = datetime.date.today().year
        footerText = str(Template(file=get_template_file('footer_text.tmpl'), searchList=[locals(),globals()]))
        tpl = Template(file=get_template_file('cas_logout_confirmation.tmpl'), searchList=[locals(), globals()])
        return str(tpl)

    @cherrypy.expose
    def process_login(self, username, password, **kwargs):
        authType, rootURL = cherrypy.request.app.config['filelocker']['auth_type'], cherrypy.request.app.config['filelocker']['root_url']
        if kwargs.has_key("authType"):
            authType = kwargs['authType']
        username = strip_tags(username)
        if authType == "cas":
            pass
        else:
            if password is None or password == "":
                raise cherrypy.HTTPRedirect("%s/login?msg=3&authType=%s" % (rootURL, authType))
            else:
                directory = AccountController.ExternalDirectory()
                if directory.authenticate(username, password):
                    currentUser = AccountController.get_user(username, True) #if they are authenticated and local, this MUST return a user object
                    if currentUser is not None:
                        if authType == "local":
                            currentUser.isLocal = True #Tags a user if they used a local login, in case we want to use this later
                        if currentUser.authorized == False:
                            raise cherrypy.HTTPError(403, "You do not have permission to access this system")
                        cherrypy.session['user'], cherrypy.session['original_user'], cherrypy.session['sMessages'], cherrypy.session['fMessages'] = currentUser, currentUser, [], []
                        session.add(AuditLog(cherrypy.session.get("user").id, "Login", "User %s logged in successfully from IP %s" % (currentUser.id, cherrypy.request.remote.ip)))
                        session.commit()
                        raise cherrypy.HTTPRedirect(rootURL)
                    else: #This should only happen in the case of a user existing in the external directory, but having never logged in before
                        try:
                            newUser = directory.lookup_user(username)
                            AccountController.install_user(newUser)
                            currentUser = AccountController.get_user(username, True)
                            if currentUser is not None and currentUser.authorized != False:
                                cherrypy.session['user'], cherrypy.session['original_user'], cherrypy.session['sMessages'], cherrypy.session['fMessages'] = currentUser, currentUser, [], []
                                raise cherrypy.HTTPRedirect(rootURL)
                            else:
                                raise cherrypy.HTTPError(403, "You do not have permission to access this system")
                        except Exception, e:
                            return "Unable to install user: %s" % str(e)
                else:
                    raise cherrypy.HTTPRedirect("%s/login?msg=1&authType=%s" % (rootURL, authType))

    @cherrypy.expose
    def css(self, style):
        rootURL = cherrypy.request.app.config['filelocker']['root_url']
        cherrypy.response.headers['Content-Type'] = 'text/css'
        staticDir = os.path.join(rootURL,"static")
        tplPath = None
        return str(Template(file=get_template_path(styleFile), searchList=[locals(),globals()]))

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def index(self, **kwargs):
        user, originalUser, maxDays = (cherrypy.session.get("user"),  cherrypy.session.get("original_user"), cherrypy.request.app.config['filelocker']['max_file_life_days'])
        roles = AccountController.get_user_roles(user)
        currentYear = datetime.date.today().year
        startDateFormatted, endDateFormatted = None, None
        today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        sevenDays = datetime.timedelta(days=7)
        sevenDaysAgo = today - sevenDays
        sevenDaysAgo = sevenDaysAgo.replace(hour=0, minute=0, second=0, microsecond=0)
        defaultExpiration = datetime.date.today() + (datetime.timedelta(days=maxDays))
        startDateFormatted = sevenDaysAgo
        endDateFormatted = today
        messageSearchWidget = account_interface.get_search_widget(account_interface, "messages")
        header = Template(file=get_template_file('header.tmpl'), searchList=[locals(),globals()])
        footerText = str(Template(file=get_template_file('footer_text.tmpl'), searchList=[locals(),globals()]))
        footer = Template(file=get_template_file('footer.tmpl'), searchList=[locals(),globals()])
        filesSection = self.files()
        indexHTML = str(header) + str(filesSection) + str(footer)
        self.saw_banner()
        return str(indexHTML)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def saw_banner(self, **kwargs):
        cherrypy.session['sawBanner'] = True
        return ""

    @cherrypy.expose
    def sign_tos(self, **kwargs):
        rootURL = cherrypy.request.app.confg['filelocker']['root_url']
        if cherrypy.session.has_key("user") and cherrypy.session.get("user") is not None:
            user = cherrypy.session.get("user")
            if kwargs.has_key('action') and kwargs['action']=="sign":
                try:
                    user.date_tos_accept(datetime.datetime.now())
                    session.commit()
                    raise cherrypy.HTTPRedirect(rootURL)
                except Exception, e:
                    logging.error("[%s] [signTos] [Failed to sign TOS: %s]" % (user.userId, str(e)))
                    return "Failed to sign TOS: %s. The administrator has been notified of this error." % str(e)
            else:
                currentYear = datetime.date.today().year
                footerText = str(Template(file=get_template_file('footer_text.tmpl'), searchList=[locals(),globals()]))
                return str(Template(file=get_template_file('tos.tmpl'), searchList=[locals(),globals()]))
        else:
            raise cherrypy.HTTPRedirect(rootURL)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def admin(self, **kwargs):
        user = cherrypy.session.get("user")
        userFiles = FileController.get_user_file_list(format="list")
        templateFiles = os.listdir(os.path.join(cherrypy.request.app.config['filelocker']['root_path'], "view"))
        configParameters = session.query(ConfigParameter).all()
        flUsers = session.query(User).slice(0,50)
        totalFileCount = session.query(func.count(File.id))
        totalUserCount = session.query(func.count(User.id))
        totalMessageCount = session.query(func.count(Message.id))
        currentUsersList = []
        currentUploads = len(cherrypy.file_uploads)
        logsFile = open(cherrypy.config["log.error_file"])
        logs = tail(logsFile, 50)
        attributes = ShareController.get_user_shareable_attributes(user)
        currentUserIds = []
        sessionCache = {}
        sessionCache = cherrypy.session.cache
        for key in sessionCache.keys():
            try:
                if sessionCache[key][0].has_key('user') and sessionCache[key][0]['user'] is not None and sessionCache[key][0]['user'].id not in currentUserIds:
                    currentUser = sessionCache[key][0]['user']
                    currentUsersList.append(currentUser)
                    currentUserIds.append(currentUser.id)
            except Exception, e:
                logging.error("[%s] [admin] [Unable to read user session: %s]" % (user.id, str(e)))
        tpl = Template(file=get_template_file('admin.tmpl'), searchList=[locals(),globals()])
        return str(tpl)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def history(self, userId=None, startDate=None, endDate=None, logAction=None, format="html", **kwargs):
        sMessages, fMessages, user= ([],[],cherrypy.session.get("user"))
        if (userId != user.id and AccountController.user_has_permission(user, "admin")==False)
            raise cherrypy.HTTPError(403)
        actionList, actionLogList = ([], [])
        try:
            startDateFormatted, endDateFormatted = None, None
            sevenDays = datetime.timedelta(days=7)
            today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            sevenDaysAgo = today - sevenDays
            sevenDaysAgo = sevenDaysAgo.replace(hour=0, minute=0, second=0, microsecond=0)
            if startDate is not None:
                startDateFormatted = datetime.datetime(*time.strptime(strip_tags(startDate), "%m/%d/%Y")[0:5])
            else:
                startDateFormatted = sevenDaysAgo
            if endDate is not None:
                endDateFormatted = datetime.datetime(*time.strptime(strip_tags(endDate), "%m/%d/%Y")[0:5])
            else:
                endDateFormatted = today
            actionLogList = session.query(AuditLog).filter(and_(AuditLog.date > startDateFormatted, AuditLog.date < endDateFormatted))

            if logAction is None or logAction == "":
                logAction = "all_minus_login"
                actionLogList.filter(AuditLog.action != "Login")
            if userId is None:
                userId = user.userId
            
            for log in actionLogList:
                log.displayClass = "%s_%s" % ("audit", log.action.replace(" ", "_").lower())
                log.displayClass = re.sub('_\(.*?\)', '', log.displayClass) # Removes (You) and (Recipient) from Read Message actions
            actionNames = session.query(AuditLog.action).filter(or_(AuditLog.initiator_user_id==userId, AuditLog.affected_user_id==userId)).distinct()
            for actionLog in actionNames:
                if actionLog not in actionList:
                    actionList.append(actionLog)
        except FLError, fle:
            fMessages.extend(fle.failureMessages)
            sMessages.extend(fle.successMessages)
        if format == "html":
            tpl = Template(file=fl.get_template_file('history.tmpl'), searchList=[locals(),globals()])
            return str(tpl)
        else:
            actionLogJSONlist = []
            for actionLog in actionLogList:
                actionLogJSONlist.append(actionLog.get_dict())
            return fl_response(sMessages, fMessages, format, data=actionLogJSONlist)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def files(self, **kwargs):
        user, systemFiles = (cherrypy.session.get("user"), [])
        if AccountController.user_has_permission(user, "admin"):
            systemFiles = session.query(File).filter(File.owner_id == "system").all()
        defaultExpiration = datetime.date.today() + (datetime.timedelta(days=fl.maxFileLifeDays))
        uploadRequests = session.query(UploadRequest).filter(UploadRequest.owner_id==user.id).all()
        userFiles = session.query(File).filter(File.owner_id == user.id).all()
        userShareableAttributes = ShareController.get_user_shareable_attributes(user)
        #TODO: Figure this out
        attributeFilesDict = ShareController.get_files_shared_with_user_by_attribute(user)
        sharedFiles = ShareController.get_files_shared_with_user_privately(user)
        tpl = Template(file=get_template_file('files.tmpl'), searchList=[locals(),globals()])
        return str(tpl)

    @cherrypy.expose
    def help(self, **kwargs):
        tpl = Template(file=get_template_file('halp.tmpl'), searchList=[locals(),globals()])
        return str(tpl)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    #TODO: This
    def manage_groups(self, **kwargs):
        user = cherrypy.session.get("user")
        groups = fl.get_user_groups(user, user.userId)
        tpl = Template(file=fl.get_template_file('manageGroups.tmpl'), searchList=[locals(),globals()])
        return str(tpl)

    @cherrypy.expose
    def toobig(self, **kwargs):
        return fl_response([], ['File is too big'], "json")

    @cherrypy.expose
    def public_upload(self, ticketId=None, password=None, **kwargs):
        #TODO: This logic I know can be cleaned up somehow
        ticketOwner, uploadTicket, tpl, fl, messages  = (None, None, None, cherrypy.thread_data.flDict['app'], [])
        defaultExpiration = datetime.date.today() + (datetime.timedelta(days=fl.maxFileLifeDays))
        ticketFiles = []
        if ticketId is not None and ticketId != "":
            ticketId = strip_tags(ticketId)
            if cherrypy.session.has_key("uploadTicket"):
                if cherrypy.session.get("uploadTicket").ticketId != ticketId:
                    del(cherrypy.session['uploadTicket'])
            if cherrypy.session.has_key("uploadTicket"): #Their ticketId and the session uploadTicket's ID matched, let them keep the session
                uploadTicket = cherrypy.session.get("uploadTicket")
                try:
                    ticketOwner = fl.get_user(uploadTicket.ownerId)
                except FLError, fle:
                    logging.warning("Unable to load upload ticket: %s" % str(fle.failureMessages))
                    message = "Unable to load upload ticket: %s " % str(fle.failureMessages)
            elif password is None or password =="": #If they come in with a ticket - fill it in a prompt for password
                try:
                    uploadTicket = fl.get_upload_ticket_by_password(ticketId, None)
                    if uploadTicket is not None:
                        cherrypy.session['uploadTicket'] = uploadTicket
                        ticketOwner = fl.get_user(uploadTicket.ownerId)
                except FLError, fle:
                    messages.extend(fle.failureMessages)
            elif password is not None and password!="": # if they do have a password and ticketId, try to load the whole upload ticket
                try:
                    uploadTicket = fl.get_upload_ticket_by_password(ticketId, password)
                    cherrypy.session['uploadTicket'] = uploadTicket
                    ticketOwner = fl.get_user(uploadTicket.ownerId)
                except FLError, fle:
                    logging.warning("Unable to load upload ticket: %s" % str(fle.failureMessages))
                    message = "Unable to load upload ticket: %s " % str(fle.failureMessages)
        elif cherrypy.session.has_key("uploadTicket"):
            uploadTicket = cherrypy.session.get("uploadTicket")
            ticketOwner = fl.get_user(uploadTicket.ownerId)
        if uploadTicket is not None:
            fileList = fl.get_files_by_upload_ticket(uploadTicket)
            for flFile in fileList:
                flFile.documentType = "document"
                if flFile.fileExpirationDatetime is not None:
                    flFile.fileExpirationDatetime = flFile.fileExpirationDatetime.strftime("%m/%d/%Y")
                ticketFiles.append({'fileName': flFile.fileName, 'fileId': flFile.fileId, 'fileOwnerId': flFile.fileOwnerId, 'fileSizeBytes': flFile.fileSizeBytes, 'fileUploadedDatetime': flFile.fileUploadedDatetime.strftime("%m/%d/%Y"), 'fileExpirationDatetime': flFile.fileExpirationDatetime, 'filePassedAvScan':flFile.filePassedAvScan, 'documentType': flFile.documentType})
        content = Template(file=fl.get_template_file('public_upload_content.tmpl'), searchList=[locals(),globals()])
        tpl = ""
        if kwargs.has_key("format") and kwargs['format']=="content_only":
            tpl = content
        else:
            currentYear = datetime.date.today().year
            footerText = str(Template(file=fl.get_template_file('footer_text.tmpl'), searchList=[locals(),globals()]))
            tpl = Template(file=fl.get_template_file('public_upload.tmpl'), searchList=[locals(),globals()])
        return str(tpl)

    @cherrypy.expose
    def public_download(self, shareId, **kwargs):
        message = None
        cherrypy.response.timeout = 36000
        shareId = strip_tags(shareId)
        try:
            fl = cherrypy.thread_data.flDict['app']
            password = None
            if kwargs.has_key("password"):
               password = kwargs['password']
            publicShare = fl.get_public_share(shareId, password)
            if publicShare is not None and publicShare.passwordHash is not None and password == None:
                message = "This file is password protected."
                currentYear = datetime.date.today().year
                footerText = str(Template(file=fl.get_template_file('footer_text.tmpl'), searchList=[locals(),globals()]))
                tpl = Template(file=fl.get_template_file('public_download_landing.tmpl'), searchList=[locals(),globals()])
                return str(tpl)
            elif publicShare is not None:
                publicShareOwner = fl.get_user(publicShare.ownerId)
                flFile = fl.get_file(publicShareOwner, publicShare.fileId)
                cherrypy.session['fMessages'], cherrypy.session['sMessages'] = ([], [])
                return self.file_interface.serve_file(flFile, fl, publicShareOwner, None, publicShare.shareId)
            else:
                raise FLError(False, ["Invalid public share ID"])
        except FLError, fle:
            message = "<br />".join(fle.failureMessages)
            currentYear = datetime.date.today().year
            footerText = str(Template(file=fl.get_template_file('footer_text.tmpl'), searchList=[locals(),globals()]))
            tpl = Template(file=fl.get_template_file('public_download_landing.tmpl'), searchList=[locals(),globals()])
            return str(tpl)

    @cherrypy.expose
    def get_server_messages(self, format="json", **kwargs):
        sMessages, fMessages = [], []
        if cherrypy.session.has_key("sMessages") and cherrypy.session.has_key("fMessages"):
            for message in cherrypy.session.get("sMessages"):
                if message not in sMessages: #Interestingly, either the browser or the ajax upload script tries to re-submit a rejected file a few times resulting in duplicate messages
                    sMessages.append(message)
            for message in cherrypy.session.get("fMessages"):
                if message not in fMessages:
                    fMessages.append(message)
            (cherrypy.session["sMessages"], cherrypy.session["fMessages"]) = [], []
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def download_filelocker_client(self, platform, **kwargs):
        clientPath = os.path.join(cherrypy.request.app.config['root_path'], "static", "clients")
        if platform=="cli":
            return serve_file(os.path.join(clientPath,"cliFilelocker.py"), "application/x-download", "attachment")
        #elif platform="windows":
            #return serve_file(os.path.join(fl.clientPath,"windowsFilelocker.exe"), "application/x-download", "attachment")
        #elif platform="macintosh":
            #return serve_file(os.path.join(fl.clientPath,"macintoshFilelocker.dmg"), "application/x-download", "attachment")
        #elif platform="ios":
            #return serve_file(os.path.join(fl.clientPath,"iosFilelocker.app"), "application/x-download", "attachment")
        #elif platform="android":
            #return serve_file(os.path.join(fl.clientPath,"androidFilelocker.app"), "application/x-download", "attachment")