import os
import stat
import shutil
from stat import ST_SIZE
import random
import cherrypy
from cherrypy.lib import cptools, http, file_generator_limited
import mimetypes
mimetypes.init()
mimetypes.types_map['.dwg']='image/x-dwg'
mimetypes.types_map['.ico']='image/x-icon'
import logging
import datetime
import subprocess
from Cheetah.Template import Template
from lib.SQLAlchemyTool import session
import sqlalchemy
from sqlalchemy import *
from sqlalchemy.sql import select, delete, insert
from lib.Models import *
from lib.Formatters import *
from lib import Encryption
import AccountController
__author__="wbdavis"
__date__ ="$Sep 25, 2011 9:28:54 PM$"

class FileController(object):

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_quota_usage(self, format="json", **kwargs):
        user, sMessages, fMessages, quotaMB, quotaUsedMB = (cherrypy.session.get("user"),[], [], 0, 0)
        try:
            quotaMB, quotaUsage = 0,0
            if cherrypy.session.get("current_role") is not None:
                quotaMB = cherrypy.session.get("current_role").quota
                quotaUsage = get_role_quota_usage_bytes(cherrypy.session.get("current_role").id)
            else:
                quotaMB = user.quota
                quotaUsage = get_user_quota_usage_bytes(user.id)
            quotaUsedMB = int(quotaUsage) / 1024 / 1024
        except Exception, e:
            fMessages.append(str(e))
        return fl_response(sMessages, fMessages, format, data={'quotaMB': quotaMB , 'quotaUsedMB': quotaUsedMB})

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_download_statistics(self, fileId, startDate=None, endDate=None, format="json", **kwargs):
        user, sMessages, fMessages, stats = (cherrypy.session.get("user"),  [], [], None)
        try:
            flFile = session.query(File).filter(File.id == fileId).one()
            startDateFormatted, endDateFormatted = None, None
            thirtyDays = datetime.timedelta(days=30)
            today = datetime.datetime.now()
            thirtyDaysAgo = today - thirtyDays
            if startDate is not None:
                startDateFormatted = datetime.datetime(*time.strptime(strip_tags(startDate), "%m/%d/%Y")[0:5])
            else:
                startDateFormatted =  thirtyDaysAgo
            if endDate is not None:
                endDateFormatted = datetime.datetime(*time.strptime(strip_tags(endDate), "%m/%d/%Y")[0:5])
            else:
                endDateFormatted = today
                
            if flFile.owner_id == user.id or AccuontController.user_has_permission(user, "admin"):
                if endDate is not None:
                    endDate = endDate + datetime.timedelta(days=1)
                     #for row in results:

                uniqueDownloads = session.query(func.date(AuditLog.date), func.count(distinct(AuditLog.initiator_user_id))).\
                filter(AuditLog.action=='Download File').\
                filter(AuditLog.message.like('%%[File ID: %d]' % flFile.id)).\
                group_by(func.date(AuditLog.date)).all()
                print "Unique Downloads:%s" % str(uniqueDownloads)
                uniqueDownloadStats = []
                for row in uniqueDownloads:
                    uniqueDownloadStats.append((row[0].strftime("%m/%d/%Y"), row[1]))

                totalDownloads = session.query(func.date(AuditLog.date), func.count(AuditLog.initiator_user_id)).\
                filter(AuditLog.action=='Download File').\
                filter(AuditLog.message.like('%%[File ID: %d]' % flFile.id)).\
                group_by(func.date(AuditLog.date)).all()
                totalDownloadStats = []
                for row in totalDownloads:
                    totalDownloadStats.append((row[0].strftime("%m/%d/%Y"), row[1]))
                stats = {"total":totalDownloadStats, "unique":uniqueDownloadStats}
        except sqlalchemy.orm.exc.NoResultFound, nrf:
            fMessages.append("Could not find file with ID: %s" % str(fileId))
        except Exception, e:
            fMessages.append(str(e))
        return fl_response(sMessages, fMessages, format, data=stats)
        
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_user_file_list(self, fileIdList=None, format="json", **kwargs):
        """Get File List"""
        user, role, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.session.get("current_role"), [], [])
        myFilesList = []
        hiddenShares = session.query(HiddenShare).filter(HiddenShare.owner_id==user.id).all()
        hiddenShareIds = []
        for hiddenShare in hiddenShares:
            hiddenShareIds.append(hiddenShare.file_id)
        if fileIdList is None:
            allFilesList = session.query(File).filter(File.owner_id == user.id).all() if role is None else session.query(File).filter(File.role_owner_id==role.id).all()
            for flFile in allFilesList:
                if flFile.id not in hiddenShareIds:
                    myFilesList.append(flFile)
        else:
            fileIdList = split_list_sanitized(fileIdList)
            for fileId in fileIdList:
                flFile = session.query(File).filter(File.id==fileId).one()
                if (flFile.owner_id == user.id or flFile.shared_with(user)) and flFile.id not in hiddenShareIds:
                    myFilesList.append(flFile)
        for flFile in myFilesList: #attachments to the file objects for this function, purely cosmetic
            if (len(flFile.public_shares) > 0) and (len(flFile.user_shares) > 0 or len(flFile.group_shares) > 0 ):
                flFile.documentType = "document_both"
            elif len(flFile.public_shares) > 0:
                flFile.documentType = "document_globe"
            elif len(flFile.public_shares) == 0 and (len(flFile.user_shares) > 0 or len(flFile.group_shares) > 0):
                flFile.documentType = "document_person"
            else:
                flFile.documentType = "document"
            #TODO: Account for attribute shares here 'document_attribute'
        if format=="json" or format=="searchbox_html" or format=="cli":
            myFilesJSON = []
            userShareableAttributes = AccountController.get_shareable_attributes_by_user(user) if role is None else AccountController.get_shareable_attributes_by_role(role)
            for flFile in myFilesList:
                flFile.fileUserShares, flFile.fileGroupShares, flFile.availableGroups, sharedGroupsList, flFile.fileAttributeShares = ([],[],[],[],[])
                for share in flFile.user_shares:
                    flFile.fileUserShares.append({'id': share.user.id, 'name': share.user.display_name})
                sharedGroupIds = []
                for share in flFile.group_shares:
                    sharedGroupIds.append(share.group.id)
                    flFile.fileGroupShares.append({'id': share.group.id, 'name': share.group.name})
                for share in flFile.attribute_shares:
                    flFile.fileAttributeShares.append({'id': share.attribute.id, 'name': share.attribute.name})
                for group in session.query(Group).filter(Group.owner_id==user.id):
                    if group.id not in sharedGroupIds:
                        flFile.availableGroups.append({'id': group.id, 'name': group.name})
                myFilesJSON.append({'fileName': flFile.name, 'fileId': flFile.id, 'fileOwnerId': flFile.owner_id, 'fileSizeBytes': flFile.size, 'fileUploadedDatetime': flFile.date_uploaded.strftime("%m/%d/%Y"), 'fileExpirationDatetime': flFile.date_expires.strftime("%m/%d/%Y") if flFile.date_expires is not None else "Never", 'filePassedAvScan':flFile.passed_avscan, 'documentType': flFile.documentType, 'fileUserShares': flFile.fileUserShares, 'fileGroupShares': flFile.fileGroupShares, 'availableGroups': flFile.availableGroups, 'fileAttributeShares': flFile.fileAttributeShares})
            if format=="json":
                return fl_response(sMessages, fMessages, format, data=myFilesJSON)
            elif format=="searchbox_html":
                selectedFileIds = ",".join(fileIdList)
                context = "private_sharing"
                groups = session.query(Group).filter(Group.owner_id == user.id).all()
                searchWidget = str(Template(file=get_template_file('search_widget.tmpl'), searchList=[locals(),globals()]))
                tpl = Template(file=get_template_file('share_files.tmpl'), searchList=[locals(),globals()])
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
    def take_file(self, fileId, format="json", **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"), [], [])
        config = cherrypy.request.app.config['filelocker']
        try:
            flFile = session.query(File).filter(File.id==fileId).one()
            if flFile.owner_id == user.id:
                fMessages.append("You cannot take your owne file")
            elif flFile.shared_with(user) or AccountController.user_has_permission(user, "admin"):
                if (get_user_quota_usage_bytes(user) + flFile.size) >= (user.quota*1024*1024):
                    logging.warning("[%s] [take_file] [User has insufficient quota space remaining to check in file: %s]" % (user.id, flFile.name))
                    raise Exception("You may not copy this file because doing so would exceed your quota")
                takenFile = flFile.get_copy()
                takenFile.owner_id = user.id
                takenFile.date_uploaded = datetime.datetime.now()
                takenFile.notify_on_download = False
                session.add(takenFile)
                session.commit()
                shutil.copy(os.path.join(config['vault'],str(flFile.id)), os.path.join(config['vault'],str(takenFile.id)))
                sMessages.append("Successfully took ownership of file %s. This file can now be shared with other users just as if you had uploaded it. " % flFile.name)
            else:
                fMessages.append("You do not have permission to take this file")
        except sqlalchemy.orm.exc.NoResultFound, nrf:
            fMessages.append("Could not find file with ID: %s" % str(fileId))
        except Except, e:
            session.rollback()
            fMessages.append(str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def delete_files(self, fileIds, format="json", **kwargs):
        user, role, sMessages, fMessages = (cherrypy.session.get("user"),cherrypy.session.get("current_role"), [], [])
        fileIds = split_list_sanitized(fileIds)
        for fileId in fileIds:
            try:
                fileId = int(fileId)
                flFile = session.query(File).filter(File.id == fileId).one()
                if flFile.role_owner_id is not None and role is not None and flFile.role_owner_id == role.id:
                    queue_for_deletion(flFile.id)
                    session.delete(flFile)
                    session.add(AuditLog(user.id, "Delete File", "File %s (%s) owned by role %s has been deleted by user %s. " % (flFile.name, flFile.id, role.name, user.id, role.id)))
                    session.commit()
                    sMessages.append("File %s deleted successfully" % flFile.name)
                elif flFile.owner_id == user.id or AccountController.user_has_permission(user, "admin"):
                    queue_for_deletion(flFile.id)
                    session.delete(flFile)
                    session.add(AuditLog(user.id, "Delete File", "File %s (%s) has been deleted" % (flFile.name, flFile.id)))
                    session.commit()
                    sMessages.append("File %s deleted successfully" % flFile.name)
                else:
                    fMessages.append("You do not have permission to delete file %s" % flFile.name)
            except sqlalchemy.orm.exc.NoResultFound, nrf:
                fMessages.append("Could not find file with ID: %s" % str(fileId))
            except Exception, e:
                session.rollback()
                logging.error("[%s] [delete_files] [Could not delete file: %s]" % (user.id, str(e)))
                fMessages.append("File not deleted: %s" % str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def update_file(self, fileId, format="json", **kwargs):
        user,  sMessages, fMessages = (cherrypy.session.get("user"), [], [])
        fileId = strip_tags(fileId)
        try:
            flFile = session.query(File).filter(File.id==fileId).one()
            if flFile.owner_id == user.id or AccountController.user_has_permission(user, "admin"):
                if kwargs.has_key("fileName"):
                    flFile.name = strip_tags(kwargs['fileName'])
                if kwargs.has_key('notifyOnDownload'):
                    flFile.notify_on_download = True if kwargs['notifyOnDownload'].lower()=="true" else False
                if kwargs.has_key('fileNotes'):
                    flFile.notes = strip_tags(kwargs['fileNotes'])
                session.commit()
                sMessages.append("Successfully updated file %s" % flFile.name)
            else:
                fMessages.append("You do not have permission to update file with ID: %s" % str(flFile.id))
        except sqlalchemy.orm.exc.NoResultFound, nrf:
            fMessages.append("Could not find file with ID: %s" % str(fileId))
        except Exception, e:
            fMessages.append(str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.before_upload()
    def upload(self, format="json", **kwargs):
        cherrypy.response.timeout = 86400
        user, role, uploadRequest, uploadKey, config, sMessages, fMessages = None, None, None, None, cherrypy.request.app.config['filelocker'], [], []

        #Check Permission to upload since we can't wrap in requires login for public uploads
        if cherrypy.session.has_key("uploadRequest") and cherrypy.session.get("uploadRequest") is not None and cherrypy.session.get("uploadRequest").expired == False:
            uploadRequest = cherrypy.session.get("uploadRequest")
            user = AccountController.get_user(uploadRequest.owner_id)
            uploadKey = "%s:%s" % (user.id, uploadRequest.id)
        else:
            cherrypy.tools.requires_login()
            user, sMessages, fMessages = cherrypy.session.get("user"), cherrypy.session.get("sMessages"), cherrypy.session.get("fMessages")
            uploadKey = user.id
            if cherrypy.session.get("current_role") is not None:
                role = cherrypy.session.get("current_role")

        #Check upload size
        lcHDRS = {}
        for key, val in cherrypy.request.headers.iteritems():
            lcHDRS[key.lower()] = val
        try:
            fileSizeBytes = int(lcHDRS['content-length'])
        except KeyError, ke:
            fMessages.append("Request must have a valid content length")
            raise HTTPError(411, "Request must have a valid content length")
        fileSizeMB = ((fileSizeBytes/1024)/1024)
        vaultSpaceFreeMB, vaultCapacityMB = get_vault_usage()
        
        if (fileSizeMB*2) >= vaultSpaceFreeMB:
            logging.critical("[system] [upload] [File vault is running out of space and cannot fit this file. Remaining Space is %s MB, fileSizeBytes is %s]" % (vaultSpaceFreeMB, fileSizeBytes))
            fMessages.append("The server doesn't have enough space left on its drive to fit this file. The administrator has been notified.")
            raise HTTPError(413, "The server doesn't have enough space left on its drive to fit this file. The administrator has been notified.")
        quotaSpaceRemainingBytes = 0
        if role is not None:
            quotaSpaceRemainingBytes = (role.quota*1024*1024) - get_role_quota_usage_bytes(role.id)
        else:
            quotaSpaceRemainingBytes = (user.quota*1024*1024) - get_user_quota_usage_bytes(user.id)
        if fileSizeBytes > quotaSpaceRemainingBytes:
            fMessages.append("File size is larger than your quota will accomodate")
            raise HTTPError(413, "File size is larger than your quota will accomodate")

        #The server won't respond to additional user requests (polling) until we release the lock
        cherrypy.session.release_lock()

        newFile = File()
        newFile.size = fileSizeBytes
        #Get the file name
        fileName, tempFileName = None,None
        if fileName is None and lcHDRS.has_key('x-file-name'):
            fileName = lcHDRS['x-file-name']
        if kwargs.has_key("fileName"):
            fileName = kwargs['fileName']
        if fileName is not None and fileName.split("\\")[-1] is not None:
            fileName = fileName.split("\\")[-1]

        #Set upload index if it's found in the arguments
        if kwargs.has_key('uploadIndex'):
            uploadIndex = kwargs['uploadIndex']

        #Read file from client
        if lcHDRS['content-type'] == "application/octet-stream":
            file_object = get_temp_file()
            tempFileName = file_object.name.split(os.path.sep)[-1]
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
                logging.debug("[system] [upload] [File upload was prematurely stopped, rejected]")
                queue_for_deletion(tempFileName)
                fMessages.append("The file %s did not upload completely before the transfer ended" % fileName)
                if cherrypy.file_uploads.has_key(uploadKey):
                    for fileTransfer in cherrypy.file_uploads[uploadKey]:
                        if fileTransfer.file_object.name == upFile.file_object.name:
                            cherrypy.file_uploads[uploadKey].remove(fileTransfer)
                    if len(cherrypy.file_uploads[uploadKey]) == 0:
                        del cherrypy.file_uploads[uploadKey]
                raise cherrypy.HTTPError("412 Precondition Failed", "The file transfer completed, but the file appears to be missing data. If you did not intentionally cancel the file, please try re-uploading.")
        else:
            cherrypy.request.headers['uploadindex'] = uploadIndex
            formFields = myFieldStorage(fp=cherrypy.request.rfile,
                                        headers=lcHDRS,
                                        environ={'REQUEST_METHOD':'POST'},
                                        keep_blank_values=True)
            upFile = formFields['fileName']
            if fileName is None:
                fileName = upFile.filename
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

        #The file has been successfully uploaded by this point, process the rest of the variables regarding the file
        newFile.name = fileName
        fileNotes = strip_tags(kwargs['fileNotes']) if kwargs.has_key("fileNotes") else ""
        if fileNotes is not None and len(fileNotes) > 256:
            fileNotes = fileNotes[0:256]
        newFile.notes = fileNotes

        #Owner ID is a separate variable since uploads can be owned by the system
        if role is not None:
            newFile.role_owner_id = role.id
        else:
            newFile.owner_id = user.id

        #Process date provided
        maxExpiration = datetime.datetime.today() + datetime.timedelta(days=config['max_file_life_days'])
        expiration = kwargs['expiration'] if kwargs.has_key("expiration") else None
        if (expiration is None or expiration == "" or expiration.lower() =="never"):
            if role is not None and AccountController.role_has_permission(role, "expiration_exempt") or AccountController.role_has_permission(role, "admin"):
                expiration = None
            elif AccountController.user_has_permission(user,  "expiration_exempt") or AccountController.user_has_permission(user, "admin"): #Check permission before allowing a non-expiring upload
                expiration = None
            else:
                expiration = maxExpiration
        else:
            expiration = datetime.datetime(*time.strptime(strip_tags(expiration), "%m/%d/%Y")[0:5])
            if expiration > maxExpiration and AccountController.user_has_permission(user,  "expiration_exempt")==False:
                fMessages.append("Expiration date was invalid. Expiration set to %s" % maxExpiration.strftime("%m/%d/%Y"))
                expiration = maxExpiration
        newFile.date_expires = expiration

        scanFile = True if ((kwargs.has_key("scanFile") and kwargs['scanFile'].lower() == "true") or (uploadRequest is not None and uploadRequest.scan_file)) else False

        newFile.notify_on_download = True if (kwargs.has_key("notifyOnDownload") and strip_tags(notifyOnDownload.lower()) == "on") else False
        newFile.date_uploaded = datetime.datetime.now()
        newFile.status = "Processing"
        newFile.upload_request_id = None if (uploadRequest is None) else uploadRequest.id
        session.add(newFile)
        session.commit()

        #Set status to scanning
        if cherrypy.file_uploads.has_key(uploadKey):
            for fileTransfer in cherrypy.file_uploads[uploadKey]:
                if fileTransfer.file_object.name == upFile.file_object.name:
                    fileTransfer.status = "Scanning and Encrypting" if scanFile else "Encrypting"
        #Check in the file
        try:
            check_in_file(tempFileName, newFile)
            #If this is an upload request, check to see if it's a single use request and nullify the ticket if so, now that the file has been successfully uploaded
            if uploadRequest is not None:
                if uploadRequest.type == "single":
                    session.add(AuditLog(cherrypy.request.remote.ip, "Upload Requested File", "File %s has been uploaded by an external user to your Filelocker account. This was a single user request and the request has now expired." % (newFile.name), uploadRequest.owner_id))
                    attachedUploadRequest = session.query(UploadRequest).filter(UploadRequest.id == uploadRequest.id).one()
                    session.delete(attachedUploadRequest)
                    cherrypy.session['uploadRequest'].expired = True
                else:
                    session.add(AuditLog(cherrypy.request.remote.ip, "Upload Requested File", "File %s has been uploaded by an external user to your Filelocker account." % (newFile.name), uploadRequest.owner_id))
            checkInLog = AuditLog(user.id, "Check In File", "File %s (%s) checked in to Filelocker: MD5 %s " % (newFile.name, newFile.id, newFile.md5))
            if role is not None:
                checkInLog.affected_role_id = role.id
            session.add(checkInLog)
            sMessages.append("File %s uploaded successfully." % str(fileName))
            session.commit()
        except sqlalchemy.orm.exc.NoResultFound, nrf:
            fMessages.append("Could not find upload request with ID: %s" % str(uploadRequest.id))
        except Exception, e:
            logging.error("[%s] [upload] [Couldn't check in file: %s]" % (user.id, str(e)))
            fMessages.append("File couldn't be checked in to the file repository: %s" % str(e))


        #At this point the file upload is done, one way or the other. Remove the ProgressFile from the transfer dictionary
        try:
            if cherrypy.file_uploads.has_key(uploadKey):
                for fileTransfer in cherrypy.file_uploads[uploadKey]:
                    if fileTransfer.file_object.name == upFile.file_object.name:
                        cherrypy.file_uploads[uploadKey].remove(fileTransfer)
                if len(cherrypy.file_uploads[uploadKey]) == 0:
                    del cherrypy.file_uploads[uploadKey]
        except KeyError, ke:
            logging.warning("[%s] [upload] [Key error deleting entry in file_transfer]" % user.id)

        #Queue the temp file for secure erasure
        queue_for_deletion(tempFileName)

        #Return the response
        if format=="cli":
            newFileXML = "<file id='%s' name='%s'></file>" % (createdFile.id, createdFile.name)
            return fl_response(sMessages, fMessages, format, data=newFileXML)
        else:
            return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    def download(self, fileId, **kwargs):
        serveFile, publicShareId, requestedFile = False, None, None
        if cherrypy.session.has_key("public_share_id"):
            publicShareId = cherrypy.session.get("public_share_id")
            try:
                publicShare = session.query(PublicShare).filter(PublicShare.id == publicShareId).one()
                requestedFile = session.query(File).filter(File.id == fileId).one()
                if requestedFile not in publicShare.files:
                    raise cherrypy.HTTPError(401)
                else:
                    serveFile = True
            except sqlalchemy.orm.exc.NoResultFound, nrf:
                raise cherrypy.HTTPError(404, "Could not find share or file")
        else:
            cherrypy.tools.requires_login()
            user = cherrypy.session.get("user")
            try:
                requestedFile = session.query(File).filter(File.id==fileId).one()
                if requestedFile.owner_id == user.id or requestedFile.shared_with(user) or AccountController.user_has_permission(user, "admin"):
                    serveFile = True
            except sqlalchemy.orm.exc.NoResultFound, nrf:
                raise cherrypy.HTTPError(404, "Could not find file")

        cherrypy.response.timeout = 36000
        cherrypy.session.release_lock()

        if serveFile:
            return self.serve_file(requestedFile, publicShareId=publicShareId)
        else:
            raise cherrypy.HTTPError(403, "You do not have access to this file")

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def create_upload_request(self, password, expiration, scanFile, requestType, maxFileSize=None, emailAddresses=None, personalMessage=None, format="json", **kwargs):
        user, config, uploadURL, sMessages, fMessages = cherrypy.session.get("user"),cherrypy.request.app.config['filelocker'],"", [], []
        try:
            expiration = parse_date(expiration, datetime.datetime.now())
        except Exception, e:
            fMessages.append(str(e))
        try:
            maxFileSize = int(strip_tags(maxFileSize)) if (maxFileSize == "" or maxFileSize=="0" or maxFileSize == 0) else None
            if maxFileSize is not None and maxFileSize < 0:
                fMessages.append("Max file size must be a positive number")
            scanFile = True if scanFile.lower()=="true" else False
            password = None if password == "" else password
            emailAddresses = emailAddresses.replace(";", ",") if (emailAddresses is not None and emailAddresses != "") else []
            personalMessage = strip_tags(personalMessage)
            requestType = "multi" if requestType.lower() == "multi" else "single"
            uploadRequest = UploadRequest(date_expires=expiration, max_file_size=maxFileSize, scan_file=scanFile, type=requestType, owner_id=user.id)
            if password is not None:
                uploadRequest.set_password(password)
            if requestType == "multi" and password == None:
                fMessages.append("You must specify a password for upload requests that allow more than 1 file to be uploaded")
            else:
                uploadRequest.generate_id()
                session.add(uploadRequest)
                session.commit()
                uploadURL = config['root_url']+"/public_upload?ticketId=%s" % str(uploadRequest.id)
                sMessages.append("Successfully generated upload ticket")
        except Exception, e:
            fMessages.append(str(e))
        return fl_response(sMessages, fMessages, format, data=uploadURL)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def delete_upload_request(self, ticketId, format="json"):
        user,  sMessages, fMessages = cherrypy.session.get("user"), [], []
        try:
            ticketId = strip_tags(ticketId)
            uploadRequest = session.query(UploadRequest).filter(UploadRequest.id == ticketId).one()
            if uploadRequest.owner_id == user.id or AccountController.user_has_permission(user, "admin"):
                session.delete(uploadRequest)
                session.commit()
                sMessages.append("Upload request deleted")
            else:
                fMessages.append("You do not have permission to delete this upload request")
        except Exception, e:
            fMessages.append(str(e))
        return fl_response(sMessages, fMessages, format)

    def serve_file(self, flFile, user=None, content_type=None, publicShareId=None):
        config = cherrypy.request.app.config['filelocker']
        cherrypy.response.headers['Pragma']="cache"
        cherrypy.response.headers['Cache-Control']="private"
        cherrypy.response.headers['Content-Length'] = flFile.size
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
        if user is None:
            user = cherrypy.session.get("user")
        disposition = "attachment"
        path = os.path.join(config['vault'], str(flFile.id))
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
            cd = '%s; filename="%s"' % (disposition, flFile.name)
            response.headers["Content-Disposition"] = cd

        # Set Content-Length and use an iterable (file object)
        #   this way CP won't load the whole file in memory
        c_len = st.st_size
        bodyfile = open(path, 'rb')
        salt = bodyfile.read(16)
        decrypter = Encryption.new_decrypter(flFile.encryption_key, salt)
        try:
            response.body = self.enc_file_generator(user, decrypter, bodyfile, flFile.id, publicShareId)
            return response.body
        except HTTPError, he:
            raise he

    def enc_file_generator(self, user, decrypter, dFile, fileId=None, publicShareId=None):
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
            file_download_complete(user, fileId, publicShareId)
            yield data[:len(data)-padding]
        else:
            #For multiblock files
            while True:
                if endOfFile:
                    file_download_complete(user, fileId, publicShareId)
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
                userId = cherrypy.session.get("user").id
                for key in cherrypy.file_uploads.keys():
                    if key.split(":")[0] == cherrypy.session.get('user').id: # This will actually get uploads by the user and uploads using a ticket they generated
                        for fileStat in cherrypy.file_uploads[key]:
                            uploadStats.append(fileStat.stat_dict())
            elif cherrypy.session.has_key("uploadRequest"):
                uploadRequest = cherrypy.session.get("uploadRequest")
                uploadKey = uploadRequest.owner_id + ":" + uploadRequest.id
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

def file_download_complete(user, fileId, publicShareId=None):
    try:
        flFile = session.query(File).filter(File.id==fileId).one()
        if user.id != flFile.owner_id and flFile.notify_on_download:
            try:
                owner = session.query(User).filter(User.id==flFile.owner_id).one()
                if owner.email is not None and owner.email != "":
                    self.mail.notify(self.get_template_file('download_notification.tmpl'),{'sender': None, 'recipient': owner.email, 'fileName': flFile.name, 'downloadUserId': user.id, 'downloadUserName': user.display_name})
            except Exception, e:
                logging.error("[%s] [file_download_complete] [Unable to notify user %s of download completion: %s]" % (user.id, owner.id, str(e)))

        if publicShareId is not None:
            publicShare = session.query(PublicShare).filter(PublicShare.id == publicShareId).one()
            session.add(AuditLog(flFile.owner_id,"Download File", "File %s downloaded via Public Share. [File ID: %s]" % (flFile.name, flFile.id)))
            if flFile.notify_on_download:
                try:
                    owner = session.query(User).filter(User.id == flFile.owner_id).one()
                    if owner.email is not None and owner.email != "":
                        Mail.notify(get_template_file('public_download_notification.tmpl'),{'sender': None, 'recipient': owner.email, 'fileName': flFile.name})
                except Exception, e:
                    logging.error("[%s] [file_download_complete] [Unable to notify user %s of download completion: %s]" % (user.id, owner.id, str(e)))
            if publicShare.reuse == "single":
                publicShare.files.remove(flFile)
                session.commit()
                if len(publicShare.files) == 0:
                    session.delete(publicShare)
                    session.add(AuditLog(flFile.owner_id, "Delete Public Share", "File %s downloaded via single use public share. File is no longer publicly shared. [File ID: %s]" % (flFile.name, flFile.id)))
                    session.commit()
        else:
            session.add(AuditLog(user.id, "Download File", "File %s downloaded by user %s. [File ID: %s]" % (flFile.name, user.id, flFile.id)))
        session.commit()
    except Exception, e:
        logging.error("[%s] [file_download_complete] [Unable to finish download completion: %s]" % (user.id, str(e)))

def get_upload_ticket_by_password(ticketId, password):
    uploadRequest = session.query(UploadRequest).filter(UploadRequest.id == ticketId)
    if uploadRequest is None:
        raise Exception("Invalid Upload Request ID")
    if password == None and uploadRequest.password == None:
        return uploadRequest
    else:
        isValid = lib.Encryption.compare_password_hash(password, uploadRequest.password)
        if isValid and len(uploadRequest.password) == 32:
            newHash = lib.Encryption.hash_password(password)
            uploadRequest.password = newHash
            session.commit() #New has stored in the db
            return uploadRequest
        else:
            raise Exception("You must enter the correct password to access this upload request.")

def get_temp_file():
    config = cherrypy.request.app.config['filelocker']
    fileList, filePrefix, fileSuffix = os.listdir(config['vault']), "[%s]fltmp" % str(config['cluster_member_id']), ".tmp"
    randomNumber = random.randint(1, 1000000)
    tempFileName = os.path.join(config['vault'], filePrefix + str(randomNumber) + fileSuffix)
    while tempFileName in fileList:
        randomNumber = random.randint(1, 1000000)
        tempFileName = os.path.join(config['vault'], filePrefix + str(randomNumber) + fileSuffix)
    file_object = open(tempFileName, "wb")
    return file_object

def check_in_file(tempFileName, flFile):
    config = cherrypy.request.app.config['filelocker']
    filePath = os.path.join(config['vault'], tempFileName)
    #Virus scanning if requested
    avCommandList = config['antivirus_command'].split(" ")
    avCommandList.append(filePath)
    try:
        p = subprocess.Popen(avCommandList, stdout=subprocess.PIPE)
        output = p.communicate()[0]
        if(p.returncode != 0):
            logging.warning("[%s] [check_in_file] [File %s did not pass requested virus scan, return code: %s, output: %s]" % (flFile.owner_id, flFile.name, p.returncode, output))
            queue_for_deletion(tempFileName)
            flFile.passed_avscan = False
        else:
            flFile.passed_avscan = True
    except OSError, oe:
        logging.critical("[%s] [check_in_file] [AVSCAN execution failed: %s]", (flFile.owner_id, str(oe)))
        flFile.passed_avscan = False

    md5sum = None
    try:
        p = subprocess.Popen(["md5sum",filePath], stdout=subprocess.PIPE)
        md5sum = p.communicate()[0].split(" ")[0]
    except Exception, e:
        logging.error("Couldn't calculate file md5sum: %s" % str(e))
    flFile.md5 = md5sum
    #Determine file size and check against quota
    try:
        flFile.size = os.stat(filePath)[ST_SIZE]
        if (flFile.owner_id != "system"):
            user = session.query(User).filter(User.id == flFile.owner_id).one()
            if (get_user_quota_usage_bytes(user.id) + flFile.size) >= (user.quota*1024*1024):
                logging.warning("[%s] [check_in_file] [User has insufficient quota space remaining to check in file: %s]" % (user.id, flFile.name))
                raise Exception("You may not upload this file as doing so would exceed your quota")
    except Exception, e:
        logging.critical("[%s] [check_in_file] [Couldn't determine file size, using one set from content-length: %s]" % (flFile.owner_id, str(e)))

    #determine file type
    flFile.type = "Unknown"
    try:
        fileres = os.popen("%s %s" % (config['file_command'], filePath), "r")
        data = fileres.read().strip()
        fileres.close()
        if data.find(";") >= 0:
            (ftype, lo) = data.split(";")
            del(lo)
            flFile.fileType = ftype.strip()
        else:
            flFile.fileType = data.strip()
    except Exception, e:
        logging.error("[%s] [checkInFile] [Unable to determine file type: %s]" % (user.id, str(e)))

    #Logic is a little strange here - if the user supplied an encryptionKey, then don't save it with the file
    encryptionKey = None
    flFile.encryption_key = Encryption.generatePassword()
    encryptionKey = flFile.encryption_key
    os.umask(077)
    newFile = open(filePath, "rb")
    f = open(os.path.join(config['vault'], str(flFile.id)), "wb")
    encrypter, salt = Encryption.new_encrypter(encryptionKey)
    padding, endOfFile = (0, False)
    f.write(salt)
    data = newFile.read(1024*8)
    #If File is only one block long, handle it here
    if len(data) < (1024*8):
        padding = 16-(len(data)%16)
        if padding == 16:
            paddingByte = "%X" % 0
        else:
            paddingByte = "%X" % padding
        for i in range(padding): data+=paddingByte
        f.write(encrypter.encrypt(data))
    else:
        while 1:
            if endOfFile: break
            else:
                next_data = newFile.read(1024*8)
                #this only happens if we are at the end, meaning the next block is the last
                #so we have to handle the padding by aggregating the two blocks and determining pad
                if len(next_data) < (1024*8):
                    data+=next_data
                    padding = 16-(len(data)%16)
                    if padding == 16: paddingByte = "%X" % 0
                    else: paddingByte = "%X" % padding
                    for i in range(padding): data+=paddingByte
                    endOfFile = True
            f.write(encrypter.encrypt(data))
            data = next_data

        newFile.close()
        f.close()
        flFile.status = "Checked In"
        logging.info("[%s] [check_in_file] [User checked in a new file %s]" % (user.id, flFile.name))

def clean_temp_files(config, validTempFiles):
    vaultFileList = os.listdir(config['filelocker']['vault'])
    for fileName in vaultFileList:
        try:
            if fileName.endswith(".tmp") and fileName.startswith("[%s]" % config['filelocker']['cluster_member_id']): #This is a temp file and made by this cluster member
                if fileName not in validTempFiles:
                    queue_for_deletion(fileName)
        except Exception, e:
            logging.error("[system] [cleanTempFiles] [There was a problem while trying to clean a stale temp file %s: %s]" % (str(fileName), str(e)))

def queue_for_deletion(filePath):
    try:
        if session.query(DeletedFile).filter(DeletedFile.file_name==filePath).scalar() == None:
            session.add(DeletedFile(file_name=filePath))
            session.commit()
        logging.info("[system] [queueForDeletion] [File queued for deletion: %s]" % (str(filePath)))
    except Exception, e:
        logging.critical("Unable to queue file for deletion: %s" % str(e))

def process_deletion_queue(config):
    vault = config['filelocker']['vault']
    fileRows = session.query(DeletedFile.file_name).all()
    for fileRow in fileRows:
        try:
            if os.path.isfile(os.path.join(vault, fileRow.file_name)):
                secure_delete(config, fileRow.file_name)
                if os.path.isfile(os.path.join(vault,fileRow.file_name))==False:
                    logging.debug("Dequeuing %s because secure delete ran and the os.path.isfile came up negative" % os.path.join(vault, fileRow.file_name))
                    deletedFile = session.query(DeletedFile).filter(DeletedFile.file_name==fileRow.file_name).scalar()
                    if deletedFile is not None:
                        session.delete(deletedFile)
                        session.commit()
                else:
                    #This isn't necessarily an error, it just means that the file finally got deleted
                    logging.debug("[system] [processDeletionQueue] [Deletion of file must have failed - still exists after secure delete ran]")
            else:
                logging.debug("[system] [processDeletionQueue] [File %s not deleted because it doesn't exist - dequeuing]" % os.path.join(vault, fileRow.file_name))
                deletedFile = session.query(DeletedFile).filter(DeletedFile.file_name==fileRow.file_name).scalar()
                if deletedFile is not None:
                    session.delete(deletedFile)
                    session.commit()
        except Exception, e:
            logging.critical("[system] [processDeletionQueue] [Couldn't delete file in deletion queue: %s]" % str(e))


def secure_delete(config, fileName):
    import errno
    vault = config['filelocker']['vault']
    deleteCommand = config['filelocker']['delete_command']
    deleteArguments = config['filelocker']['delete_arguments']
    deleteList = []
    deleteList.append(deleteCommand)
    for argument in deleteArguments.split(" "):
        deleteList.append(argument)
    deleteList.append(os.path.join(vault,fileName))
    try:
        p = subprocess.Popen(deleteList, stdout=subprocess.PIPE)
        output = p.communicate()[0]
        if(p.returncode != 0):
            logging.error("[%s] [checkDelete] [The command to delete the file returned a failure code of %s: %s]" % ("system", p.returncode, output))
        else:
            deletedFile = session.query(DeletedFile).filter(DeletedFile.file_name==fileName).scalar()
            if deletedFile is not None:
                session.delete(deletedFile)
                session.commit()
    except OSError, oe:
        if oe.errno == errno.ENOENT:
            logging.error("[system] [secureDelete] [Couldn't delete because the file was not found (dequeing): %s]" % str(oe))
            deletedFile = session.query(DeletedFile).filter(DeletedFile.file_name==fileName).scalar()
            if deletedFile is not None:
                session.delete(deletedFile)
                session.commit()
        else:
            logging.error("[system] [secureDelete] [Generic system error while deleting file: %s" % str(oe))
    except Exception, e:
       logging.error("[system] [secureDelete] [Couldn't securely delete file: %s]" % str(e))

def get_vault_usage():
    s = os.statvfs(cherrypy.request.app.config['filelocker']['vault'])
    freeSpaceMB = int((s.f_bavail * s.f_frsize) / 1024 / 1024)
    totalSizeMB = int((s.f_blocks * s.f_frsize) / 1024 / 1024 )
    return freeSpaceMB, totalSizeMB

def get_user_quota_usage_bytes(userId):
    quotaUsage = session.query(func.sum(File.size)).select_from(File).filter(File.owner_id==userId).scalar()
    if quotaUsage is None:
        return 0
    else:
        return int(quotaUsage)

def get_role_quota_usage_bytes(roleId):
    quotaUsage = session.query(func.sum(File.size)).select_from(File).filter(File.role_owner_id==roleId).scalar()
    if quotaUsage is None:
        return 0
    else:
        return int(quotaUsage)