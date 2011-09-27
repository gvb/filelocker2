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
__author__="wbdavis"
__date__ ="$Sep 25, 2011 9:36:56 PM$"

class RootController:
    fl = None
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
        fl, msg, errorMessage, authType = (cherrypy.thread_data.flDict['app'], None, None, None)
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
            authType = fl.authType
        if authType == "cas":
            pass
        elif authType == "ldap" or authType == "local":
            currentYear = datetime.date.today().year
            footerText = str(Template(file=fl.get_template_file('footer_text.tmpl'), searchList=[locals(),globals()]))
            tpl = Template(file=fl.get_template_file('login.tmpl'), searchList=[locals(),globals()])
            return str(tpl)
        else:
            logging.error("[system] [login] [No authentication variable set in config]")
            raise cherrypy.HTTPError(403, "No authentication mechanism")

    @cherrypy.expose
    def expired_json(self, **kwargs):
        fMessages = ["expired"]
        return fl_response([], fMessages, "json")

    @cherrypy.expose
    def expired_text(self, **kwargs):
        fl = cherrypy.thread_data.flDict['app']
        tpl = Template(file=fl.get_template_file('expired.tmpl'), searchList=[locals(), globals()])
        return str(tpl)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def logout(self):
        fl = cherrypy.thread_data.flDict['app']
        if fl.authType == "cas":
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
        fl = cherrypy.thread_data.flDict['app']
        currentYear = datetime.date.today().year
        footerText = str(Template(file=fl.get_template_file('footer_text.tmpl'), searchList=[locals(),globals()]))
        tpl = Template(file=fl.get_template_file('cas_logout_confirmation.tmpl'), searchList=[locals(), globals()])
        return str(tpl)

    @cherrypy.expose
    def process_login(self, username, password, **kwargs):
        fl, authType = cherrypy.thread_data.flDict['app'], None
        if kwargs.has_key("authType"):
            authType = kwargs['authType']
        else:
            authType = fl.authType
        username = strip_tags(username)
        if authType == "cas":
            pass
        else:
            if password is None or password == "":
                raise cherrypy.HTTPRedirect("%s/login?msg=3&authType=%s" % (fl.rootURL, authType))
            elif (authType == "local" and fl.localDirectory.authenticate(username, password)) or (authType!="local" and fl.directory.authenticate(username, password)):
                currentUser = fl.get_user(username, True) #if they are authenticated and local, this MUST return a user object
                if currentUser is not None:
                    if authType == "local":
                        currentUser.isLocal = True #Tags a user if they used a local login, in case we want to use this later
                    if currentUser.authorized == False:
                        raise cherrypy.HTTPError(403, "You do not have permission to access this system")
                    cherrypy.session['user'], cherrypy.session['original_user'], cherrypy.session['sMessages'], cherrypy.session['fMessages'] = currentUser, currentUser, [], []
                    fl.record_login(cherrypy.session.get("user"), cherrypy.request.remote.ip)
                    raise cherrypy.HTTPRedirect(fl.rootURL)
                else: #This should only happen in the case of a user existing in the external directory, but having never logged in before
                    try:
                        newUser = fl.directory.lookup_user(username)
                        fl.install_user(newUser)
                        currentUser = fl.get_user(username, True)
                        if currentUser is not None and currentUser.authorized != False:
                            cherrypy.session['user'], cherrypy.session['original_user'], cherrypy.session['sMessages'], cherrypy.session['fMessages'] = currentUser, currentUser, [], []
                            raise cherrypy.HTTPRedirect(fl.rootURL)
                        else:
                            raise cherrypy.HTTPError(403, "You do not have permission to access this system")
                    except FLError, fle:
                        return "Unable to install user: %s" % fle.failureMessages
            else:
                raise cherrypy.HTTPRedirect("%s/login?msg=1&authType=%s" % (fl.rootURL, authType))

    @cherrypy.expose
    def css(self, style):
        fl = cherrypy.thread_data.flDict['app']
        cherrypy.response.headers['Content-Type'] = 'text/css'
        staticDir = os.path.join(fl.rootURL,"static")
        tplPath = None
        if style=="filelocker":
            tplPath=os.path.join(fl.templatePath,'css','filelocker.css')
        elif style=="jquery-ui":
            tplPath=os.path.join(fl.templatePath,'css','jquery-ui.css')
        elif style=="visualize":
            tplPath=os.path.join(fl.templatePath,'css','visualize.css')
        return str(Template(file=tplPath, searchList=[locals(),globals()]))

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def index(self, **kwargs):
        user, fl, originalUser = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], cherrypy.session.get("original_user"))
        roles = fl.get_user_roles(user)
        defaultExpiration = datetime.date.today() + (datetime.timedelta(days=fl.maxFileLifeDays))
        currentYear = datetime.date.today().year
        startDateFormatted, endDateFormatted = None, None
        sevenDays = datetime.timedelta(days=7)
        today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        sevenDaysAgo = today - sevenDays
        sevenDaysAgo = sevenDaysAgo.replace(hour=0, minute=0, second=0, microsecond=0)
        startDateFormatted = sevenDaysAgo
        endDateFormatted = today
        messageSearchWidget = HTTP_User.get_search_widget(HTTP_User(), "messages")
        header = Template(file=fl.get_template_file('header.tmpl'), searchList=[locals(),globals()])
        footerText = str(Template(file=fl.get_template_file('footer_text.tmpl'), searchList=[locals(),globals()]))
        footer = Template(file=fl.get_template_file('footer.tmpl'), searchList=[locals(),globals()])
        defaultExpiration = datetime.date.today() + (datetime.timedelta(days=fl.maxFileLifeDays))
        uploadTickets = fl.get_upload_tickets_by_user(user, user.userId)
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
        fl = cherrypy.thread_data.flDict['app']
        if cherrypy.session.has_key("user") and cherrypy.session.get("user") is not None:
            user = cherrypy.session.get("user")
            roles = fl.get_user_roles(user)
            if kwargs.has_key('action') and kwargs['action']=="sign":
                try:
                    fl.sign_tos(user)
                    cherrypy.session['user'] = fl.get_user(user.userId, True)
                    raise cherrypy.HTTPRedirect(fl.rootURL)
                except FLError, fle:
                    logging.error("[%s] [signTos] [Failed to sign TOS: %s]" % (user.userId, str(fle.failureMessages)))
                    return "Failed to sign TOS: %s. The administrator has been notified of this error." % str(fle.failureMessages)
            else:
                currentYear = datetime.date.today().year
                footerText = str(Template(file=fl.get_template_file('footer_text.tmpl'), searchList=[locals(),globals()]))
                return str(Template(file=fl.get_template_file('tos.tmpl'), searchList=[locals(),globals()]))
        else:
            raise cherrypy.HTTPRedirect(fl.rootURL)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def admin(self, **kwargs):
        user, fl = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'])
        userFiles = self.file_interface.get_user_file_list(format="list")
        templateFiles = os.listdir(fl.templatePath)
        configParameters = fl.get_config(user)
        flUsers = fl.get_all_users(user, 0, 50)
        totalFileCount = fl.get_file_count(user)
        totalUserCount = fl.get_user_count(user)
        totalMessageCount = fl.get_message_count(user)
        currentUsersList = []
        currentUploads = len(cherrypy.file_uploads)
        logsFile = open(fl.logFile)
        logs = tail(logsFile, 50)

        attributes = fl.get_available_attributes_by_user(user)
        currentUserIds = []
        sessionCache = {}
        if cherrypy.config['tools.sessions.storage_type'] == "db":
            sessionCache = cherrypy.session.get_all_sessions()
        else:
            sessionCache = cherrypy.session.cache
        for key in sessionCache.keys():
            try:
                if sessionCache[key][0].has_key('user') and sessionCache[key][0]['user'] is not None and sessionCache[key][0]['user'].userId not in currentUserIds:
                    currentUser = sessionCache[key][0]['user']
                    currentUsersList.append(currentUser)
                    currentUserIds.append(currentUser.userId)
            except Exception, e:
                logging.error("[%s] [admin] [Unable to read user session: %s]" % (user.userId, str(e)))
        tpl = Template(file=fl.get_template_file('admin.tmpl'), searchList=[locals(),globals()])
        return str(tpl)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def history(self, userId=None, startDate=None, endDate=None, logAction=None, format="html", **kwargs):
        sMessages, fMessages, user, fl = ([],[],cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'])
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
            if logAction is None or logAction == "":
                logAction = "all_minus_login"
            if userId is None:
                userId = user.userId
            actionLogList = fl.get_audit_log(user, userId, startDateFormatted, endDateFormatted, logAction)
            for log in actionLogList:
                log.displayClass = "%s_%s" % ("audit", log.action.replace(" ", "_").lower())
                log.displayClass = re.sub('_\(.*?\)', '', log.displayClass) # Removes (You) and (Recipient) from Read Message actions
            actionNames = fl.get_audit_log_action_names(user, userId)
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
        user, fl, systemFiles = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [])
        if fl.check_admin(user):
            systemFiles = self.file_interface.get_user_file_list(format="list", userId="system")
        defaultExpiration = datetime.date.today() + (datetime.timedelta(days=fl.maxFileLifeDays))
        uploadTickets = fl.get_upload_tickets_by_user(user, user.userId)
        userFiles = self.file_interface.get_user_file_list(format="list")
        userShareableAttributes = fl.get_available_attributes_by_user(user)
        attributeFilesDict = fl.get_attribute_shares_by_user(user, user.userId)
        sharedFiles = self.file_interface.get_files_shared_with_user_list(format="list")
        tpl = Template(file=fl.get_template_file('files.tmpl'), searchList=[locals(),globals()])
        return str(tpl)

    @cherrypy.expose
    def help(self, **kwargs):
        fl = cherrypy.thread_data.flDict['app']
        tpl = Template(file=fl.get_template_file('halp.tmpl'), searchList=[locals(),globals()])
        return str(tpl)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def manage_groups(self, **kwargs):
        user, fl = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'])
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
        fl = cherrypy.thread_data.flDict['app']
        if platform=="cli":
            return serve_file(os.path.join(fl.clientPath,"cliFilelocker.py"), "application/x-download", "attachment")
        #elif platform="windows":
            #return serve_file(os.path.join(fl.clientPath,"windowsFilelocker.exe"), "application/x-download", "attachment")
        #elif platform="macintosh":
            #return serve_file(os.path.join(fl.clientPath,"macintoshFilelocker.dmg"), "application/x-download", "attachment")
        #elif platform="ios":
            #return serve_file(os.path.join(fl.clientPath,"iosFilelocker.app"), "application/x-download", "attachment")
        #elif platform="android":
            #return serve_file(os.path.join(fl.clientPath,"androidFilelocker.app"), "application/x-download", "attachment")