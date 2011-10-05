import cherrypy
import logging
import datetime
from Cheetah.Template import Template
from lib.SQLAlchemyTool import session
from sqlalchemy import *
from model.File import File
__author__="wbdavis"
__date__ ="$Sep 25, 2011 9:28:54 PM$"

class FileController:
    
    def get_vault_usage(self):
        s = os.statvfs(self.vault)
        freeSpaceMB = int((s.f_bavail * s.f_frsize) / 1024 / 1024)
        totalSizeMB = int((s.f_blocks * s.f_frsize) / 1024 / 1024 )
        return freeSpaceMB, totalSizeMB
    
    def get_user_quota_usage_bytes(self, userId):
            quotaUsage = session.query(func.sum(File.size).filter(File.owner_id==user.id))
            return int(quotaUsage)

        
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_quota_usage(self, format="json", **kwargs):
        user, fl, sMessages, fMessages, quotaMB, quotaUsed = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [], 0, 0)
        try:
            quotaMB = user.quota
            quotaUsage = self.get_user_quota_usage_bytes(user.id)
            quotaUsedMB = int(quotaUsage) / 1024 / 1024
        except Exception, e:
            fMessages.append(str(e))
        return fl_response(sMessages, fMessages, format, data={'quotaMB': quotaMB , 'quotaUsedMB': quotaUsedMB})

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_download_statistics(self, fileId, startDate=None, endDate=None, format="json", **kwargs):
        user, fl, sMessages, fMessages, stats = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [], None)
        try:
            flFile = session.query(File).filter(File.id == fileId).one()
            startDateFormatted, endDateFormatted = None, None
            thirtyDays = datetime.timedelta(days=30)
            today = datetime.datetime.now()
            thirtyDaysAgo = today - thirtyDays
            if startDate is not None:
                startDateFormatted = datetime.datetime(*time.strptime(Formatters.strip_tags(startDate), "%m/%d/%Y")[0:5])
            else:
                startDateFormatted =  thirtyDaysAgo
            if endDate is not None:
                endDateFormatted = datetime.datetime(*time.strptime(Formatters.strip_tags(endDate), "%m/%d/%Y")[0:5])
            else:
                endDateFormatted = today
            flFile = self.get_file(user, fileId)
            if flFile.owner_id == user.id or self.check_admin(user):
                if endDate is not None:
                    endDate = endDate + datetime.timedelta(days=1)
                stats = self.db.getDownloadStatistics(fileId, startDate, endDate)
        except Exception, e:
            fMessages.append(str(e)
        return fl_response(sMessages, fMessages, format, data=stats)
        
            #def getDownloadStatistics(self, fileId, startDate=None, endDate=None):
        #totalDownloadSql = "SELECT DATE(audit_log_datetime) AS 'day', count(*) AS 'Downloads' FROM audit_log WHERE audit_log_action = 'Download File' AND audit_log_message LIKE '%%[File ID: %s]'"
        #uniqueDownloadSql = "SELECT audit_log_datetime AS 'day', count(*) AS 'Unique User Downloads' FROM (SELECT DISTINCT audit_log_initiator_user_id, DATE(audit_log_datetime) AS audit_log_datetime FROM audit_log WHERE audit_log_action = 'Download File' AND audit_log_message LIKE '%%[File ID: %s]') AS t1"
        #fileIdInt = int(fileId)
        #sql_args = [fileIdInt]
        #if startDate is not None:
            #totalDownloadSql += " AND audit_log_datetime >= %s"
            #uniqueDownloadSql += " WHERE audit_log_datetime >= %s"
            #sql_args.append(startDate)
        #if endDate is not None:
            #totalDownloadSql += " AND audit_log_datetime <= %s"
            #if startDate is not None:
                #uniqueDownloadSql += " AND"
            #else:
                #uniqueDownloadSql += " WHERE"
            #uniqueDownloadSql += " audit_log_datetime <= %s"
            #sql_args.append(endDate)
        #totalDownloadSql +=" GROUP BY DATE(audit_log_datetime) ORDER BY audit_log_datetime"
        #uniqueDownloadSql +=" GROUP BY DATE(audit_log_datetime) ORDER BY audit_log_datetime"
        #results = self.execute(totalDownloadSql, sql_args)
        #totalDownloadStats = []
        #for row in results:
            #stat = (str(row['day']), row['Downloads'])
            #totalDownloadStats.append(stat)
        #uniqueDownloadStats = []
        #results = self.execute(uniqueDownloadSql, sql_args)
        #for row in results:
            #stat = (str(row['day']), row['Unique User Downloads'])
            #uniqueDownloadStats.append(stat)
        #return {"total":totalDownloadStats, "unique":uniqueDownloadStats}

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_hourly_statistics(self, format="json", **kwargs):
        user, fl, sMessages, fMessages, stats = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [], None)
        try:
            stats = fl.get_hourly_statistics(user)
        except FLError, fle:
            fMessages.extend(fle.failureMessages)
            sMessages.extend(fle.successMessages)
        return fl_response(sMessages, fMessages, format, data=stats)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_daily_statistics(self, format="json", **kwargs):
        user, fl, sMessages, fMessages, stats = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [], None)
        try:
            stats = fl.get_daily_statistics(user)
        except FLError, fle:
            fMessages.extend(fle.failureMessages)
            sMessages.extend(fle.successMessages)
        return fl_response(sMessages, fMessages, format, data=stats)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_monthly_statistics(self, format="json", **kwargs):
        user, fl, sMessages, fMessages, stats = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [], None)
        try:
            stats = fl.get_monthly_statistics(user)
        except FLError, fle:
            fMessages.extend(fle.failureMessages)
            sMessages.extend(fle.successMessages)
        return fl_response(sMessages, fMessages, format, data=stats)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_user_file_list(self, fileIdList=None, format="json", **kwargs):
        """Get File List

        Oh god this function makes so many database calls, there may be a more efficient way to do this as the scope
        of this function kept getting bigger and bigger. Please someone rewrite this!!!"""
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        userId = user.userId
        if kwargs.has_key("userId"):
            userId = kwargs['userId']
        myFilesList = []
        if fileIdList is None:
            myFilesList = fl.get_files_by_user(user, userId)
        else:
            fileIdList = split_list_sanitized(fileIdList)
            for fileId in fileIdList:
                flFile = fl.get_file(user, fileId)
                myFilesList.append(flFile)

        for flFile in myFilesList: #attachments to the file objects for this function
            flFile.publicShare = None
            flFile.shares = []
            flFile.groupShares = []
            flFile.documentType = "document"

        #Determine how to display the files in the interface
        privateSharedList, publicSharedList, bothSharedList = [], [], []
        for publicShareObject in fl.get_public_shares_by_user(user, userId):
            publicSharedList.append(publicShareObject.fileId)
            for flFile in myFilesList:
                if flFile.fileId == publicShareObject.fileId:
                    flFile.publicShare = publicShareObject #This implies that there can be only one public share
                    break
        for shareObject in fl.get_private_shares_by_user(user, userId):
            privateSharedList.append(shareObject.fileId)
            shareObject.user = fl.get_user(shareObject.targetId) #Get the real user object for the share target
            for flFile in myFilesList:
                if flFile.fileId == shareObject.fileId:
                    if shareObject.user is None:
                        shareObject.user = fl.directory.lookup_user(shareObject.targetId) # In case the user hasn't logged in yet
                    if shareObject.user is None: #This user doesn't exist anymore
                        shareObject.user = User("User no longer exists", "", "", None, None, None, shareObject.targetId)
                    flFile.shares.append(shareObject)
                    break
        for groupShareObject in fl.get_private_group_shares_by_user(user, userId):
            privateSharedList.append(groupShareObject.fileId)
            groupShareObject.group = fl.get_group(user, groupShareObject.targetId) #Get the info about the group for each group share
            for flFile in myFilesList:
                if flFile.fileId == groupShareObject.fileId:
                    flFile.groupShares.append(groupShareObject)
                    break
        bothSharedList = [val for val in publicSharedList if val in privateSharedList]

        for flFile in myFilesList:
            if flFile.fileId in privateSharedList:
                flFile.documentType = "document_person"
            if flFile.fileId in publicSharedList:
                flFile.documentType = "document_globe"
            if flFile.fileId in bothSharedList:
                flFile.documentType = "document_both"
                #TODO: Account for attribute shares here 'document_attribute'
        if format=="json" or format=="searchbox_html" or format=="cli":
            myFilesJSON = []
            groups = fl.get_user_groups(user, user.userId)
            userShareableAttributes = fl.get_available_attributes_by_user(user)
            for flFile in myFilesList:
                flFile.fileUserShares, flFile.fileGroupShares, flFile.availableGroups, flFile.sharedGroupsList, flFile.fileAttributeShares = ([],[],[],[],[])
                for sharedFile in flFile.shares:
                    flFile.fileUserShares.append({'id': sharedFile.targetId, 'name': sharedFile.user.userDisplayName})
                for sharedFile in flFile.groupShares:
                    flFile.fileGroupShares.append({'id': sharedFile.targetId, 'name': sharedFile.group.groupName})
                for attribute in userShareableAttributes:
                    attrFiles = fl.get_files_shared_by_attribute(user, attribute.attributeId)
                    for af in attrFiles:
                        if af.fileId == flFile.fileId:
                            flFile.fileAttributeShares.append({'id': attribute.attributeId, 'name': attribute.attributeName})
                for group in groups:
                    if str(group.groupId) not in flFile.sharedGroupsList:
                        flFile.availableGroups.append({'id': group.groupId, 'name': group.groupName})
                if flFile.fileExpirationDatetime is not None:
                    flFile.fileExpirationDatetime = flFile.fileExpirationDatetime.strftime("%m/%d/%Y")
                myFilesJSON.append({'fileName': flFile.fileName, 'fileId': flFile.fileId, 'fileOwnerId': flFile.fileOwnerId, 'fileSizeBytes': flFile.fileSizeBytes, 'fileUploadedDatetime': flFile.fileUploadedDatetime.strftime("%m/%d/%Y"), 'fileExpirationDatetime': flFile.fileExpirationDatetime, 'filePassedAvScan':flFile.filePassedAvScan, 'documentType': flFile.documentType, 'fileUserShares': flFile.fileUserShares, 'fileGroupShares': flFile.fileGroupShares, 'availableGroups': flFile.availableGroups, 'fileAttributeShares': flFile.fileAttributeShares})
            if format=="json":
                return fl_response(sMessages, fMessages, format, data=myFilesJSON)
            elif format=="searchbox_html":
                selectedFileIds = ",".join(fileIdList)
                searchWidget = str(HTTP_User.get_search_widget(HTTP_User(), "private_sharing"))
                tpl = Template(file=fl.get_template_file('share_files.tmpl'), searchList=[locals(),globals()])
                return str(tpl)
            elif format=="cli":
                myFilesJSON = sorted(myFilesJSON, key=lambda k: k['fileId'])
                myFilesXML = ""
                for myFile in myFilesJSON:
                    myFilesXML += "<file id='%s' name='%s' size='%s' passedAvScan='%s'></file>" % (myFile['fileId'], myFile['fileName'], myFile['fileSizeBytes'], myFile['filePassedAvScan'])
                return fl_response(sMessages, fMessages, format, data=myFilesXML)
        elif format=="list":
            return myFilesList
        else:
            return str(myFilesList)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_files_shared_with_user_list(self, fileIdList=None, format="json", **kwargs):
        #Determine which files are shared with the user
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        sharedFilesList = []
        for sharedFile in fl.get_files_shared_with_user(user, user.userId):
            sharedFile.documentType = "document_shared_in"
            if fl.is_share_hidden(user, sharedFile.fileId) is False:
                sharedFilesList.append(sharedFile)
        if format=="json":
            sharedFilesJSON = []
            for flFile in sharedFilesList:
                sharedFilesJSON.append({'fileName': flFile.fileName, 'fileId': flFile.fileId, 'fileOwnerId': flFile.fileOwnerId, 'fileSizeBytes': flFile.fileSizeBytes, 'fileUploadedDatetime': flFile.fileUploadedDatetime.strftime("%m/%d/%Y"), 'fileExpirationDatetime': flFile.fileExpirationDatetime.strftime("%m/%d/%Y"), 'filePassedAvScan':flFile.filePassedAvScan, 'documentType': flFile.documentType})
            return fl_response(sMessags, fMessages, format, data=sharedFilesJSON)
        elif format=="list":
            return sharedFilesList
        else:
            return str(sharedFilesList)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def take_file(self, fileId, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            fl.duplicate_and_take_file(user, fileId)
            flFile = fl.get_file(user, fileId)
            sMessages.append("Successfully took ownership of file %s. This file can now be shared with other users just as if you had uploaded it. " % flFile.fileName)
        except FLError, fle:
            fMessages.extend(fle.failureMessages)
            sMessages.extend(fle.successMessages)
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def delete_files(self, fileIds=None, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        fileIds = split_list_sanitized(fileIds)
        for fileId in fileIds:
            try:
                fileId = int(Formatters.strip_tags(str(fileId)))
                flFile = fl.get_file(user, fileId)
                if flFile.fileOwnerId == user.userId or fl.check_admin(user):
                    fl.delete_file(user, fileId)
                    sMessages.append("File %s deleted successfully" % flFile.fileName)
                else:
                    fMessages.append("You do not have permission to delete file %s" % flFile.fileName)
            except FLError, fle:
                fMessages.extend(fle.failureMessages)
                sMessages.extend(fle.successMessages)
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def update_file(self, fileId, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        fileId = Formatters.strip_tags(fileId)
        try:
            flFile = fl.get_file(user, fileId)
            if kwargs.has_key("fileName"):
                flFile.fileName = Formatters.strip_tags(kwargs['fileName'])
            if kwargs.has_key('notifyOnDownload'):
                if kwargs['notifyOnDownload'] == "true":
                    flFile.fileNotifyOnDownload = True
                elif kwargs['notifyOnDownload'] == "false":
                    flFile.fileNotifyOnDownload = False
            if kwargs.has_key('fileNotes'):
                flFile.fileNotes = Formatters.strip_tags(kwargs['fileNotes'])
            fl.update_file(user, flFile)
            sMessages.append("Successfully updated file %s" % flFile.fileName)
        except FLError, fle:
            fMessages.extend(fle.failureMessages)
            sMessages.extend(fle.successMessages)
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.before_upload()
    def upload(self, format="json", **kwargs):
        fl, user, sMessages, fMessages, uploadTicket, newFile, uploadKey, uploadIndex, uploadTicket, createdFile = cherrypy.thread_data.flDict['app'], None, [], [], None, None, None, None, None, None
        if cherrypy.session.has_key("uploadTicket") and cherrypy.session.get("uploadTicket") is not None:
            uploadTicket = cherrypy.session.get("uploadTicket")
            user = fl.get_user(uploadTicket.ownerId)
            uploadKey = user.userId+":"+uploadTicket.ticketId
        else:
            user, sMessages, fMessages = cherrypy.session.get("user"), cherrypy.session.get("sMessages"), cherrypy.session.get("fMessages")
            uploadKey = user.userId
        cherrypy.session.release_lock()
        lcHDRS = {}
        for key, val in cherrypy.request.headers.iteritems():
            lcHDRS[key.lower()] = val
        #Get the file name
        fileName, tempFileName, fileUploadComplete = None,None,True
        if fileName is None and lcHDRS.has_key('x-file-name'):
            fileName = lcHDRS['x-file-name']
        if kwargs.has_key("fileName"):
            fileName = kwargs['fileName']
        if fileName is not None and fileName.split("\\")[-1] is not None:
            fileName = fileName.split("\\")[-1]
        if fileName is None: #This is to accomodate a poorly behaving browser that's not sending the file name
            fileName = "Unknown"

        #Set upload index if it's found in the arguments
        if kwargs.has_key('uploadIndex'):
            uploadIndex = kwargs['uploadIndex']

        fileSizeBytes = int(lcHDRS['content-length'])
        if lcHDRS['content-type'] == "application/octet-stream":
            #Create the temp file to store the uploaded file
            file_object = get_temp_file()
            tempFileName = file_object.name.split(os.path.sep)[-1]
            #Read the file from the client
            #Create the progress file object and drop it into the transfer dictionary
            upFile = ProgressFile(8192, fileName, file_object, uploadIndex)
            if cherrypy.file_uploads.has_key(uploadKey): #Drop the transfer into the global transfer list
                cherrypy.file_uploads[uploadKey].append(upFile)
            else:
                cherrypy.file_uploads[uploadKey] = [upFile,]
            bytesRemaining = fileSizeBytes
            while True:
                if bytesRemaining >= 8192:
                    block = cherrypy.request.rfile.read(8192)
                else:
                    block = cherrypy.request.rfile.read(bytesRemaining)
                upFile.write(block)
                bytesRemaining -= 8192
                if bytesRemaining <= 0: break
            upFile.seek(0)
            #If the file didn't get all the way there
            if long(os.path.getsize(upFile.file_object.name)) != long(fileSizeBytes): #The file transfer stopped prematurely, take out of transfers and queue partial file for deletion
                fileUploadComplete = False
                logging.debug("[system] [upload] [File upload was prematurely stopped, rejected]")
                fl.queue_for_deletion(tempFileName)
                fMessages.append("The file %s did not upload completely before the transfer ended" % fileName)
                if cherrypy.file_uploads.has_key(uploadKey):
                    for fileTransfer in cherrypy.file_uploads[uploadKey]:
                        if fileTransfer.file_object.name == upFile.file_object.name:
                            cherrypy.file_uploads[uploadKey].remove(fileTransfer)
                    if len(cherrypy.file_uploads[uploadKey]) == 0:
                        del cherrypy.file_uploads[uploadKey]
        else:
            cherrypy.request.headers['uploadindex'] = uploadIndex
            formFields = myFieldStorage(fp=cherrypy.request.rfile,
                                        headers=lcHDRS,
                                        environ={'REQUEST_METHOD':'POST'},
                                        keep_blank_values=True)


            upFile = formFields['fileName']
            if fileName == "Unknown":
                fileName = upFile.filename
            addToUploads = True
            if str(type(upFile.file)) == '<type \'cStringIO.StringO\'>' or isinstance(upFile.file, StringIO.StringIO):
                newTempFile = get_temp_file()
                newTempFile.write(str(upFile.file.getvalue()))
                newTempFile.seek(0)
                upFile = ProgressFile(8192, fileName, newTempFile)
                if cherrypy.file_uploads.has_key(uploadKey): #Drop the transfer into the global transfer list
                    cherrypy.file_uploads[uploadKey].append(upFile)
                else:
                    cherrypy.file_uploads[uploadKey] = [upFile,]
            else:
                upFile = upFile.file
            tempFileName = upFile.file_object.name.split(os.path.sep)[-1]

        if fileUploadComplete:
            #The file has been successfully uploaded by this point, process the rest of the variables regarding the file
            fileNotes = None
            if kwargs.has_key("fileNotes"):
                fileNotes = Formatters.strip_tags(kwargs['fileNotes'])
            if fileNotes is None:
                fileNotes = ""
            else:
                fileNotes = Formatters.strip_tags(fileNotes)
                if len(fileNotes) > 256:
                    fileNotes = fileNotes[0:256]
            ownerId = None #Owner ID is a separate variable since uploads can be owned by the system
            try:
                ownerId = user.userId

                if fl.check_admin(user) and (kwargs.has_key('systemUpload') and kwargs['systemUpload'] == "yes"):
                    ownerId = "system"
                expiration=None
                if kwargs.has_key("expiration"):
                    expiration = kwargs['expiration']
                #Process the expiration data for the file
                maxExpiration = datetime.datetime.today() + datetime.timedelta(days=fl.maxFileLifeDays)
                if (expiration is None or expiration == "" or expiration.lower() =="never"):
                    if fl.check_permission(user, "expiration_exempt") or fl.check_admin(user): #Check permission before allowing a non-expiring upload
                        expiration = None
                    else:
                        expiration = maxExpiration
                else:
                    expiration = datetime.datetime(*time.strptime(Formatters.strip_tags(expiration), "%m/%d/%Y")[0:5])
                    if maxExpiration < expiration and fl.check_permission(user, "expiration_exempt")==False:
                        raise FLError(False, ["Expiration date must be between now and %s" % maxExpiration.strftime("%m/%d/%Y")])

                #Virus scanning - Tells check_in whether to scan the file, and delete if infected. For upload tickets, scanning may be set by the requestor.
                scanFile = ""
                if kwargs.has_key("scanFile"):
                    scanFile = Formatters.strip_tags(kwargs['scanFile'])
                if scanFile.lower() == "true":
                    scanFile = True
                elif uploadTicket is not None and uploadTicket.scanFile:
                    scanFile = True
                else:
                    scanFile = False

                #Download notification - if "yes" then the owner will be notified whenever the file is downloaded by other users
                notifyOnDownload = ""
                if kwargs.has_key("notifyOnDownload"):
                    scanFile = Formatters.strip_tags(kwargs['notifyOnDownload'])
                if notifyOnDownload.lower() == "on":
                    notifyOnDownload = True
                else:
                    notifyOnDownload = False

                #Build the Filelocker File objects and check them in to Filelocker
                if uploadTicket is not None:
                    newFile = File(fileName, None, fileNotes, fileSizeBytes, datetime.datetime.now(), user.userId, expiration, False, None, None, "Processing File", "local", notifyOnDownload, uploadTicket.ticketId)
                else:
                    newFile = File(fileName, None, fileNotes, fileSizeBytes, datetime.datetime.now(), ownerId, expiration, False, None, None, "Processing File", "local", notifyOnDownload, None)
                if cherrypy.file_uploads.has_key(uploadKey):
                    for fileTransfer in cherrypy.file_uploads[uploadKey]:
                        if fileTransfer.file_object.name == upFile.file_object.name:
                            if scanFile == True:
                                fileTransfer.status = "Scanning and Encrypting"
                            else:fileTransfer.status = "Encrypting"
                createdFile = fl.check_in_file(user, upFile.file_object.name, newFile, scanFile)
                sMessages.append("File %s uploaded successfully." % str(fileName))

                #If this is an upload request, check to see if it's a single use request and nullify the ticket if so, now that the file has been successfully uploaded
                if uploadTicket is not None:
                    if uploadTicket.ticketType == "single":
                        fl.log_action(uploadTicket.ownerId, "Upload Requested File", None, "File %s has been uploaded by an external user to your Filelocker account. This was a single user request and the request has now expired." % (newFile.fileName))
                        fl.delete_upload_ticket(user, uploadTicket.ticketId)
                        cherrypy.session['uploadTicket'].expired = True
                    else:
                        fl.log_action(uploadTicket.ownerId, "Upload Requested File", None, "File %s has been uploaded by an external user to your Filelocker account." % (newFile.fileName))
            except ValueError, ve:
                fMessages.append("Invalid expiration date format. Date must be in mm/dd/yyyy format.")
            except FLError, fle:
                fMessages.extend(fle.failureMessages)
                sMessages.extend(fle.successMessages)
                logging.error("[%s] [upload] [FL Error uploading file: %s]" % (uploadKey, str(fle.failureMessages)))
            except Exception, e:
                fMessages.append("Could not upload file: %s." % str(e))
                logging.error("[%s] [upload] [Error uploading file: %s]" % (uploadKey, str(e)))

            #At this point the file upload is done, one way or the other. Remove the ProgressFile from the transfer dictionary
            try:
                if cherrypy.file_uploads.has_key(uploadKey):
                    for fileTransfer in cherrypy.file_uploads[uploadKey]:
                        if fileTransfer.file_object.name == upFile.file_object.name:
                            cherrypy.file_uploads[uploadKey].remove(fileTransfer)
                    if len(cherrypy.file_uploads[uploadKey]) == 0:
                        del cherrypy.file_uploads[uploadKey]
            except KeyError, ke:
                logging.warning("[%s] [upload] [Key error deleting entry in file_transfer]" % user.userId)

            #Queue the temp file for secure erasure
            fl.queue_for_deletion(tempFileName)

        #Return the response
        if format=="cli":
            newFileXML = "<file id='%s' name='%s'></file>" % (createdFile.fileId, createdFile.fileName)
            return fl_response(sMessages, fMessages, format, data=newFileXML)
        else:
            return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def download(self, fileId, **kwargs):
        cherrypy.response.timeout = 36000
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        cherrypy.session.release_lock()
        try:
            flFile = fl.get_file(user, fileId)
            #if kwargs.has_key("encryptionKey") and kwargs['encryptionKey'] !="" and kwargs['encryptionKey'] is not None:
                #flFile.fileEncryptionKey = kwargs['encryptionKey']
            #if flFile.fileEncryptionKey is None:
                #raise HTTPError(412, "This file requires you to supply an encryption key to decrypt the file.")
            return self.serve_file(flFile)
        except FLError, fle:
            logging.error("[%s] [download] [Error while trying to initiate download: %s]" % (user.userId, str(fle.failureMessages)))
            cherrypy.session['fMessages'].append("Unable to download: %s" % str(fle.failureMessages))
            raise HTTPError(404, "Unable to download: %s" % str(fle.failureMessages))

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def generate_upload_ticket(self, password, expiration, scanFile, requestType, maxFileSize=None, emailAddresses=None, personalMessage=None, format="json", **kwargs):
        fl, user, uploadURL, sMessages, fMessages = cherrypy.thread_data.flDict['app'], cherrypy.session.get("user"), "", [], []
        try:
            expiration = datetime.datetime(*time.strptime(Formatters.strip_tags(expiration), "%m/%d/%Y")[0:5])
            if expiration < datetime.datetime.now():
                raise FLError(False, ["Expiration date cannot be before today"])
            #maxFileSize = Formatters.strip_tags(maxFileSize)
            #if maxFileSize == "" or maxFileSize=="0" or maxFileSize == 0:
                #maxFileSize = None
            #else:
                #maxFileSize = int(Formatters.strip_tags(maxFileSize))
            scanFile = Formatters.strip_tags(scanFile)
            scanFile = scanFile.lower()
            if password == "":
                password = None
            if scanFile == "true":
                scanFile = True
            else:
                scanFile = False
            if emailAddresses is not None and emailAddresses != "":
                emailAddresses = emailAddresses.replace(";", ",")
                emailAddresses = split_list_sanitized(emailAddresses)
            else:
                emailAddress = []
            if personalMessage is not None:
                personalMessage = Formatters.strip_tags(personalMessage)
            requestType = Formatters.strip_tags(requestType.lower())
            if requestType != "multi" and requestType != "single": #Complete failure conditions
                fMessages.append("Request type must be specified as either 'single' or 'multi'");
            #elif maxFileSize is not None and maxFileSize < 1: #Complete failure condition
                #fMessages.append("Max file size for upload tickets must be a positive whole number")
            else:
                try:
                    ticketId = fl.generate_upload_ticket(user, password, None, expiration, scanFile, requestType, emailAddresses, personalMessage)
                    uploadURL = fl.rootURL+"/public_upload?ticketId=%s" % str(ticketId)
                    sMessages.append("Successfully generated upload ticket")
                except FLError, fle:
                    fMessages.extend(fle.failureMessages)
        except FLError, fle:
            fMessages.extend(fle.failureMessages)
            sMessages.extend(fle.successMessages)
        except Exception, e:
            if expiration is None or expiration == "":
                fMessages.append("Upload requests must have an expiration date.")
            else:
                fMessages.append("Invalid expiration date format. Date must be in mm/dd/yyyy format.")
        return fl_response(sMessages, fMessages, format, data=uploadURL)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def delete_upload_ticket(self, ticketId, format="json"):
        fl, user, uploadURL, sMessages, fMessages = cherrypy.thread_data.flDict['app'], cherrypy.session.get("user"), "", [], []
        try:
            ticketId = Formatters.strip_tags(ticketId)
            fl.delete_upload_ticket(user, ticketId)
            sMessages.append("Upload ticket deleted")
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)

    def serve_file(self, flFile, fl=None, user=None, content_type=None, publicShareId=None):
        cherrypy.response.headers['Pragma']="cache"
        cherrypy.response.headers['Cache-Control']="private"
        cherrypy.response.headers['Content-Length'] = flFile.fileSizeBytes
        cherrypy.response.stream = True
        """Set status, headers, and body in order to serve the given file.

        The Content-Type header will be set to the content_type arg, if provided.
        If not provided, the Content-Type will be guessed by the file extension
        of the 'path' argument.

        If disposition is not None, the Content-Disposition header will be set
        to "<disposition>; filename=<name>". If name is None, it will be set
        to the basename of path. If disposition is None, no Content-Disposition
        header will be written.
        """
        success, message = (True, "")
        if fl is None:
            fl = cherrypy.thread_data.flDict['app']
        if user is None:
            user = cherrypy.session.get("user")
        disposition = "attachment"
        path = os.path.join(fl.vault, str(flFile.fileId))
        response = cherrypy.response
        try:
            st = os.stat(path)
        except OSError, ose:
            logging.error("OSError while trying to serve file: %s" % str(ose))
            raise cherrypy.NotFound()
        # Check if path is a directory.
        if stat.S_ISDIR(st.st_mode):
            # Let the caller deal with it as they like.
            raise cherrypy.NotFound()

        # Set the Last-Modified response header, so that
        # modified-since validation code can work.
        response.headers['Last-Modified'] = http.HTTPDate(st.st_mtime)
        #cptools.validate_since()
        if content_type is None:
            # Set content-type based on filename extension
            ext = ""
            i = path.rfind('.')
            if i != -1:
                ext = path[i:].lower()
            content_type = mimetypes.types_map.get(ext, "text/plain")
        response.headers['Content-Type'] = content_type
        if disposition is not None:
            cd = '%s; filename="%s"' % (disposition, flFile.fileName)
            response.headers["Content-Disposition"] = cd

        # Set Content-Length and use an iterable (file object)
        #   this way CP won't load the whole file in memory
        c_len = st.st_size
        bodyfile = open(path, 'rb')
        salt = bodyfile.read(16)
        decrypter = encryption.new_decrypter(flFile.fileEncryptionKey, salt)
        try:
            response.body = self.enc_file_generator(user, decrypter, bodyfile, flFile.fileId, publicShareId)
            return response.body
        except HTTPError, he:
            raise he

    def enc_file_generator(self, user, decrypter, dFile, fileId=None, publicShareId=None):
        fl = cherrypy.thread_data.flDict['app']
        endOfFile = False
        readData = dFile.read(1024*8)
        data = decrypter.decrypt(readData)
        #If the data is less than one block long, just process it and send it out
        #try:
        if len(data) < (1024*8):
            padding = int(str(data[-1:]),16)
            #A 0 represents that the file had a multiple of 16 bytes, and 16 bytes of padding were added
            if padding==0:
                padding=16
            endOfFile = True
            fl.file_download_complete(user, fileId, publicShareId)
            yield data[:len(data)-padding]
        else:
            #For multiblock files
            while True:
                if endOfFile:
                    fl.file_download_complete(user, fileId, publicShareId)
                    break
                next_data = decrypter.decrypt(dFile.read(1024*8))
                if (next_data is not None and next_data != "") and not len(next_data)<(1024*8):
                    yData = data
                    data = next_data
                    yield yData
                #This prevents padding going across block boundaries by aggregating the last two blocks and processing
                #as a whole if the next block is less than a full block (signifying end of file)
                else:
                    data = data + next_data
                    padding = int(str(data[-1:]),16)
                    #A 0 represents that the file had a multiple of 16 bytes, and 16 bytes of padding were added
                    if padding==0:
                        padding=16
                    endOfFile = True
                    yield data[:len(data)-padding]
        #except Exception, e:
            #logging.info("[%s] [decryptFile] [Decryption failed due to bad encryption key: %s]" % (user.userId, str(e)))
            #if cherrypy.session.has_key("fMessages"):
                #cherrypy.session['fMessages'].append("Decryption failed due to bad encryption key")
            #raise HTTPError(403, "Decryption failed due to bad encryption key.")

    @cherrypy.expose
    def upload_stats(self, format="json", **kwargs):
        sMessages, fMessages, uploadStats, uploadKey = [], [], [], None
        try:
            if cherrypy.session.has_key("user") and cherrypy.session.get("user") is not None:
                userId = cherrypy.session.get("user").userId
                for key in cherrypy.file_uploads.keys():
                    if key.split(":")[0] == cherrypy.session.get('user').userId: # This will actually get uploads by the user and uploads using a ticket they generated
                        for fileStat in cherrypy.file_uploads[key]:
                            uploadStats.append(fileStat.stat_dict())
            elif cherrypy.session.has_key("uploadTicket"):
                uploadTicket = cherrypy.session.get("uploadTicket")
                uploadKey = uploadTicket.ownerId + ":" + uploadTicket.ticketId
                if cherrypy.file_uploads.has_key(uploadKey):
                    for fileStat in cherrypy.file_uploads[uploadKey]:
                        uploadStats.append(fileStat.stat_dict())
            if format=='cli':
                uploadStatsXML = ""
                for fileUpload in uploadStats:
                    uploadStatsXML += "<upFile "
                    for k,v in fileUpload.iteritems():
                        uploadStatsXML += k+"='"+v+"' "
                    uploadStatsXML += "></upFile>"
                uploadStats = uploadStatsXML
        except KeyError:
            sMessages = ["No active uploads"]
        yield fl_response(sMessages, fMessages, format, data=uploadStats)
    
    def check_expirations(self):
        expiredFiles = session.query(File).filter(File.file_expiration_datetime < datetime.datetime.now())
        for flFile in expiredFiles:
            try:
                for share in flFile.private_shares:
                    session.delete(share)
                for share in flFile.private_group_shares:
                    session.delete(share)
                for share in flFile.public_shares:
                    session.delete(share)
                session.delete(flFile)

                self.queue_for_deletion(str(flFile.fileId))
                session.commit()
                self.log_action("system", "Delete File", flFile.fileOwnerId, "File %s (ID:%s) has expired and has been purged by the system." % (flFile.fileName, flFile.fileId))
            except Exception, e:
                session.rollback()
                logging.error("[system] [checkExpirations] [Error while deleting expired file: %s]" % str(e))
        expiredMessages = self.db.getExpiredMessages()
        for message in expiredMessages:
            self.db.deleteMessage(message.messageId)
            self.queue_for_deletion("m%s" % str(message.messageId))
            self.log_action("system", "Delete Message", message.messageOwnerId, "Message %s (ID:%s) has expired and has been deleted by the system." % (message.messageSubject, message.messageId))
        expiredPublicShares = self.db.getExpiredPublicShares()
        for publicShare in expiredPublicShares:
            try:
                publicShareFile = self.db.getFile(publicShare.fileId)
                self.db.deletePublicShare(publicShare.shareId)
                fileName = "[unavailable]"
                if publicShareFile is not None:
                    fileName = publicShareFile.fileName
                self.log_action("system", "Delete Public Share", publicShare.ownerId, "Public share of file %s has expired." % fileName)
            except Exception, e:
                logging.error("[system] [checkExpirations] [Error while deleting expired public share: %s]" % str(e))
        expiredUploadTickets = self.db.getExpiredUploadTickets()
        for uploadTicket in expiredUploadTickets:
            try:
                self.db.deleteUploadTicket(uploadTicket.ticketId)
                self.log_action("system", "Delete Upload Request", uploadTicket.ownerId, "Upload request %s has expired." % uploadTicket.ticketId)
            except Exception, e:
                logging.error("[system] [checkExpirations] [Error while deleting expired upload ticket: %s]" % (str(e)))
        expiredUsers = self.db.getExpiredUsers(self.maxUserInactivityDays)
        for user in expiredUsers:
            self.db.deleteUser(user.userId)
            self.log_action("system", "Delete User", None, "User %s was deleted due to inactivity. All files and shares associated with this user have been purged as well" % str(user.userId))


    def clean_temp_files(self, validTempFiles):
        vaultFileList = os.listdir(self.vault)
        for fileName in vaultFileList:
            try:
                if fileName.endswith(".tmp") and fileName.startswith("[%s]" % self.clusterMemberId): #This is a temp file and made by this cluster member
                    if fileName not in validTempFiles:
                        self.queue_for_deletion(fileName)
            except Exception, e:
                logging.error("[system] [cleanTempFiles] [There was a problem while trying to clean a stale temp file %s: %s]" % (str(fileName), str(e)))

    def delete_orphaned_files(self):
        vaultFileList = os.listdir(self.vault)
        for fileName in vaultFileList:
            try:
                if fileName.endswith(".tmp")==False and fileName.startswith(".") == False and fileName !="custom": #this is a file id, not a temp file
                    if fileName.startswith("m"):
                        messageId = fileName.split("m")[1]
                        flMessage = self.db.getMessage(messageId)
                        if flMessage is None:
                            self.queue_for_deletion(fileName)
                    else:
                        try:
                            fileId = int(fileName)
                            flFile = self.db.getFile(fileId)
                            if flFile is None:
                                self.queue_for_deletion(fileName)
                        except Exception, e:
                            logging.warning("There was a file that did not match Filelocker's naming convention in the vault: %s. It has not been purged." % fileName)
            except Exception, e:
                logging.error("[system] [deleteOrphanedFiles] [There was a problem while trying to delete an orphaned file %s: %s]" % (str(fileName), str(e)))

    def queue_for_deletion(self, filePath):
        try:
            self.db.queueForDeletion(filePath)
            logging.info("[system] [queueForDeletion] [File queued for deletion: %s]" % (str(filePath)))
        except Exception, e:
            raise FLError(False, ["Unable to queue file for deletion: %s" % str(e)])

    def process_deletion_queue(self):
        filePaths = self.db.getFilesQueuedForDeletion()
        for filePath in filePaths:
            try:
                if os.path.isfile(os.path.join(self.vault,filePath)):
                    self.secure_delete(filePath)
                    if os.path.isfile(os.path.join(self.vault,filePath))==False:
                        logging.debug("Dequeuing %s because secure delete ran and the os.path.isfile came up negative" % os.path.join(self.vault,filePath))
                        self.db.deQueueForDeletion(filePath)
                    else:
                        #This isn't necessarily an error, it just means that the file finally got deleted
                        logging.debug("[system] [processDeletionQueue] [Deletion of file must have failed - still exists after secure delete ran]")
                else:
                    logging.debug("[system] [processDeletionQueue] [File %s not deleted because it doesn't exist - dequeuing]" % os.path.join(self.vault,filePath))
                    self.db.deQueueForDeletion(filePath)
            except Exception, e:
                logging.critical("[system] [processDeletionQueue] [Couldn't delete file in deletion queue: %s]" % str(e))

    def get_vault_usage(self):
        s = os.statvfs(self.vault)
        freeSpaceMB = int((s.f_bavail * s.f_frsize) / 1024 / 1024)
        totalSizeMB = int((s.f_blocks * s.f_frsize) / 1024 / 1024 )
        return freeSpaceMB, totalSizeMB

    def secure_delete(self, filePath):
        import errno
        deleteList = []
        deleteList.append(self.deleteCommand)
        for argument in self.deleteArguments.split(" "):
            deleteList.append(argument)
        deleteList.append(os.path.join(self.vault,filePath))
        try:
            p = subprocess.Popen(deleteList, stdout=subprocess.PIPE)
            output = p.communicate()[0]
            if(p.returncode != 0):
                logging.error("[%s] [checkDelete] [The command to delete the file returned a failure code of %s: %s]" % ("system", p.returncode, output))
            else:
                self.db.deQueueForDeletion(filePath)
        except OSError, oe:
            if oe.errno == errno.ENOENT:
                logging.error("[system] [secureDelete] [Couldn't delete because the file was not found (dequeing): %s]" % str(oe))
                self.db.deQueueForDeletion(filePath)
            else:
                logging.error("[system] [secureDelete] [Generic system error while deleting file: %s" % str(oe))
        except Exception, e:
           logging.error("[system] [secureDelete] [Couldn't securely delete file: %s]" % str(e))

