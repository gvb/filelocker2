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
import json
JSON_WRITE = None

try: #This bit here is to handle backwards compatibility with python-json modules. The .write and .dumps methods work analagously as far as I can tell
    json.write("test")
    JSON_WRITE = json.write
except AttributeError, ae:
    JSON_WRITE = json.dumps
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

class myFieldStorage(cgi.FieldStorage):
    _tempFileName = None
    def __del__(self):
      if self._tempFileName in cherrypy.active_temp_files:
        cherrypy.active_temp_files.remove(self._tempFileName)
    def make_file(self, binary=None):
        tempFile = get_temp_file()
        self._tempFileName = tempFile.name.split(os.path.sep)[-1]
        cherrypy.active_temp_files.append(self._tempFileName)
        return tempFile
      

def noBodyProcess():
    cherrypy.request.process_request_body = False
cherrypy.tools.noBodyProcess = cherrypy.Tool('before_request_body', noBodyProcess)

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
    cherrypy.session
    cherrypy.request.process_request_body = False
    
def requires_login(**kwargs):
    cherrypy.response.headers['Pragma']="no-cache"
    cherrypy.response.headers['Cache-Control']="no-cache" 
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
                    setup_session(currentUser)
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
       
cherrypy.tools.requires_login = cherrypy.Tool('before_request_body', requires_login, priority=70)
cherrypy.tools.before_upload = cherrypy.Tool('before_request_body', before_upload, priority=71)
cherrypy.active_temp_files = []
class HTTP_Admin:
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_all_users(self, start=0, length=50, format="json", **kwargs):
        user, fl, flUserList, sMessages, fMessages = cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], None, [], []
        try:
            start, length = int(strip_tags(start)), int(strip_tags(length)) 
            flUsers = fl.get_all_users(user, start, length)
            flUserList = []
            for user in flUsers:
                flUserList.append(user.get_dict())
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        except Exception, e:
            fMessages.append("Problem getting users: %s" % str(e))
        return fl_response(sMessages, fMessages, format, data=flUserList)  
        
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_user_permissions(self, userId, format="json", **kwargs):
        user, fl, sMessages, fMessages, permissionData = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [], [])
        try:
            if user.userId == userId or fl.check_admin(user): #To prevent user enumeration attacks
                userPermissions, groupPermissions = fl.get_user_permissions(userId)
                allPermissions = fl.get_all_permissions(user)
                for permission in allPermissions:
                    for gPerm in groupPermissions:
                        if gPerm.permissionId == permission.permissionId:
                            permissionData.append({'permissionId': permission.permissionId, 'permissionName': permission.permissionName, 'inheritedFrom': "(group) %s" % gPerm.inheritedFrom})
                            break
                    for uPerm in userPermissions:
                        if uPerm.permissionId == permission.permissionId:
                            permissionData.append({'permissionId': permission.permissionId, 'permissionName': permission.permissionName, 'inheritedFrom': "user"})
                            break
                    else:
                        permissionData.append({'permissionId': permission.permissionId, 'permissionName': permission.permissionName, 'inheritedFrom': ""})
            else:
                fMessages.append("You do not have permission to view permissions for this user")
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format, data=permissionData)        

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def create_user(self, userId, firstName, lastName, email, quota, isRole, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            try:
                quota = int(quota)
            except Exception, e:
                fMessages.append("Invalid number entered for quota. Quota set to 0.")
                quota = 0
            userId, firstName, lastName, email, quota = strip_tags(userId), strip_tags(firstName), strip_tags(lastName), strip_tags(email), quota
            newUser = User(firstName, lastName, email, quota, None, None, userId)
            password = None
            if kwargs.has_key("password"):
                password = kwargs['password']
            fl.create_user(user, newUser, password)
            if isRole == "yes":
                fl.make_role(user, newUser.userId)
            sMessages.append("Created user %s (%s)" % (newUser.userDisplayName, newUser.userId))
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)
        
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def bulk_create_user(self, quota, password, permissions, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            permissions = split_list_sanitized(permissions)
            line = cherrypy.request.body.readline()
            count = 0
            while line != "":
                (userId, userFirstName, userLastName, userEmailAddress) = split_list_sanitized(line)
                if fl.get_user(userId) is None:
                    newUser = User(userFirstName, userLastName, userEmailAddress.replace("\n",""), quota, None, None, userId)
                    fl.create_user(user, newUser, password)
                    for permission in permissions:
                        fl.grant_user_permission(user, userId, permission)
                    count = count + 1
                else:
                    fMessages.append("User %s already exists." % userId)
                line = cherrypy.request.body.readline()
            if len(fMessages) == 0:
                sMessages.append("Created %s users" % count)
        except ValueError, ve:
            fMessages.append("CSV file not parsed correctly, possibly in wrong format.")
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)
        
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def download_user_data(self):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            userList = fl.get_all_users(user, None, None)
            mycsv = ""
            for flUser in userList:
                mycsv = mycsv + flUser.userId + ", " + flUser.userFirstName + ", " + flUser.userLastName + ", " + flUser.userEmail + "\n"
            response = cherrypy.response
            response.headers['Cache-Control'] = "no-cache"
            response.headers['Content-Disposition'] = '%s; filename="%s"' % ("attachment", "fileLockerUsers.csv")
            response.headers['Content-Type'] = "application/x-download"
            response.headers['Pragma']="no-cache"
            response.body = mycsv
            response.headers['Content-Length'] = len(response.body[0])
            response.stream = True
            return response.body
        except Exception, e:
            fMessages.append("Error creating CSV of all users.")
            logging.error("Error: %s" % str(e))
            raise HTTPError(500, "Unable to serve user data CSV: %s" % str(e))
    
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def make_user_role(self, roleUserId, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            fl.make_role(user, roleUserId)
            sMessages.append("Successfully created a role for user %s. Other users who are granted the permission to assume this role may act on behalf of this user now." % str(roleUserId))
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)
    
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def delete_user_role(self, roleUserId, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            fl.delete_role(user, roleUserId)
            sMessages.append("Successfully deleted the role aspect for user %s." % str(roleUserId))
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)
        
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def grant_user_permission(self, userId, permissionId, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            fl.grant_user_permission(user, userId, permissionId)
            sMessages.append("User %s granted permission %s" % (userId, permissionId))
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)
    
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def revoke_user_permission(self, userId, permissionId, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            fl.revoke_user_permission(user, userId, permissionId)
            sMessages.append("User permission revoked")
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)
    
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def update_filelocker_user(self, userId, quota, email, firstName, lastName, password, confirmPassword, isRole, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            userId = strip_tags(userId)
            updateUser = fl.get_user(userId)
            try:
                newQuota = int(strip_tags(quota))
                updateUser.userQuota = newQuota
            except Exception, e:
                fMessages.append("Invalid quota entered: Quota must be a valid integer greater than 0")
            updateUser.userEmail = strip_tags(email)
            updateUser.userFirstName = strip_tags(firstName)
            updateUser.userLastName = strip_tags(lastName)
            if isRole == "yes":
                fl.make_role(user, userId) #Since this is more a function of making a permission, not updating the user
            else:
                fl.delete_role(user, userId)
            if password != "" and password != None and confirmPassword != "" and confirmPassword != None:
                if password == confirmPassword:
                    fl.update_user(user, updateUser, password)
                    sMessages.append("Successfully updated user settings")
                else:
                    fMessages.append("Passwords do not match")
            else:
                fl.update_user(user, updateUser)
                sMessages.append("Successfully updated user settings")
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        except Exception, e:
            fMessages.append("Problem while updating user object: %s" % str(e))
        return fl_response(sMessages, fMessages, format)
        
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_vault_usage(self, format="json", **kwargs):
        user, fl, sMessages, fMessages, vaultUsedMB, vaultCapacityMB = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [], 0, 0)
        try:
            vaultSpaceFreeMB, vaultCapacityMB = fl.get_vault_usage()
            vaultUsedMB = vaultCapacityMB - vaultSpaceFreeMB
        except FLError, fle:
            logging.error("[%s] [getVaultUsage] [Error while getting quota: %s]" % (user.userId,str(fle.failureMessages)))
            fMessages.extend(fle.failureMessages)
            sMessages.extend(fle.successMessages)
        return fl_response(sMessages, fMessages, format, data={'vaultCapacityMB': vaultCapacityMB , 'vaultUsedMB': vaultUsedMB})
            
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def delete_users(self, userIds, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        userIds = split_list_sanitized(userIds)
        try:
            for userId in userIds:
                try:
                    fl.delete_user(user, userId)
                    sMessages.append("Successfully deleted user %s" % userId)
                except FLError, fle:
                    sMessages.extend(fle.successMessages)
                    fMessages.extend(fle.failureMessages)
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        except Exception, e:
            fMessages.append("Unable to delete user: %s" % str(e))
        return fl_response(sMessages, fMessages, format)
    
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def update_local_directory_user(self, userId, firstName, lastName, email, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        password = None
        if kwargs.has_key("password"):
            password = kwargs['password']
        try:
            userId, firstName, lastName, email = strip_tags(userId), strip_tags(firstName), strip_tags(lastName), strip_tags(email)
            updateUser = User(firstName, lastName, email, None, None, None, userId)
            fl.update_local_user(user, updateUser, password)
            sMessags.append("Updated user %s" % userId)
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        except Exception, e:
            fMessages.append("Unable to update user: %s" % str(e))
        return fl_response(sMessages, fMessages, format)
    
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def update_server_config(self, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        configParameterList = []
        try:
            for key in kwargs:
                if key.startswith("config_name_"):
                    parameterName = key[12:]
                    description = kwargs['config_desc_%s' % parameterName]
                    if parameterName.endswith("pass"): #Don't strip characters from passwords
                        value = kwargs[key]
                    else:
                        value = strip_tags(kwargs[key])
                    parameter = Parameter(parameterName, description, None, value) #Type won't change, don't need to store or set
                    configParameterList.append(parameter)
            fl.update_config(user, configParameterList)
            for fl_instance in cherrypy.FLThreads:
                fl_instance['app'] = None
                fl_instance['app'] = Filelocker(cherrypy.request.app.config)
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        except Exception, e:
            fMessages.append("Unable to update config: %s" % str(e))
        return fl_response(sMessages, fMessages, format)
        
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def update_config_password(self, parameter, password, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        parameterName = parameter
        try:
            configParameterList = [Parameter(parameterName,None, "text", password),]
            fl.update_config(user, configParameterList)
            sMessages.append("Password parameter %s updated." % parameterName)
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        except Exception, e:
            fMessages.append("Unable to update config: %s" % str(e))
        return fl_response(sMessages, fMessages, format)
        
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def create_attribute(self, attributeName, attributeId, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            attributeName = strip_tags(attributeName)
            attributeId = strip_tags(attributeId)
            if attributeId is None or attributeId == "":
                fMessages.append("You must specify an ID for an attribute")
            elif attributeName is None or attributeName == "":
                fMessages.append("You must give this attribute a name")
            else:
                newAttribute = Attribute(attributeId, attributeName)
                fl.create_attribute(user, newAttribute)
                sMessages.append("Successfully created a new attribute")
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        except Exception, e:
            fMessages.append("Unable to create attribute: %s" % str(e))
        return fl_response(sMessages, fMessages, format)
    
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def delete_attributes(self, attributeIds, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            attributeIdList = split_list_sanitized(attributeIds)
            for attributeId in attributeIdList:
                fl.delete_attribute(user, strip_tags(attributeId))
                sMessages.append("Successfully deleted attribute: %s" % attributeId)
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        except Exception, e:
            fMessages.append("Unable to delete attribute: %s" % str(e))
        return fl_response(sMessages, fMessages, format)
    
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_template_text(self, templateName, format="json", **kwargs):
        user, fl, sMessages, fMessages, templateText = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [], "")
        try:
            if fl.check_admin(user):
                templateName = strip_tags(templateName)
                templateFilePath = fl.get_template_file(templateName)
                templateFile = open(templateFilePath)
                templateText = templateFile.read()
            else:
                raise FLError(False, ["You do not have permission to view or edit template files."])
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        except Exception, e:
            fMessages.append("Unable to load template text: %s" % str(e))
        return fl_response(sMessages, fMessages, format, data=templateText)
    
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def save_template(self, templateName, templateText, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            templateName = strip_tags(templateName)
            fl.save_custom_template(user, templateName, templateText)
            sMessages.append("Successfully saved custom template file")
            templateFile = open(fl.get_template_file(templateName))
            templateText = templateFile.read()
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        except Exception, e:
            fMessages.append("Unable to save template text: %s" % str(e))
        return fl_response(sMessages, fMessages, format, data=templateText)
        
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def revert_template(self, templateName, format="json", **kwargs):
        user, fl, sMessages, fMessages, templateText = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [], "")
        try:
            templateName = strip_tags(templateName)
            fl.delete_custom_template(user, templateName)
            sMessages.append("Successfully reverted template file %s to original." % templateName)
            templateFile = open(fl.get_template_file(templateName))
            templateText = templateFile.read()
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        except Exception, e:
            fMessages.append("Unable to save template text: %s" % str(e))
        return fl_response(sMessages, fMessages, format, data=templateText)
        
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    @cherrypy.tools.before_upload()
    def upload_logo(self, format="json", **kwargs):
        uploadTicket, newFile, uploadKey, uploadIndex, uploadTicket, createdFile = None, None, None, None, None, None
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        ##print cherrypy.request.rfile
        try:
            if fl.check_admin(user):
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
                fileSizeBytes = int(lcHDRS['content-length'])
                
                if lcHDRS['content-type'] == "application/octet-stream":
                    #Create the temp file to store the uploaded file 
                    file_object = get_temp_file()
                    tempFileName = file_object.name.split(os.path.sep)[-1]
                    cherrypy.active_temp_files.append(tempFileName)
                    cherrypy.session.get("uploads").append(fileName)
                    #Read the file from the client 
                    #Create the progress file object and drop it into the transfer dictionary
                    print "==================Reading in File====================="
                    bytesRemaining = fileSizeBytes
                    while True:
                        if bytesRemaining >= 8192:
                            block = cherrypy.request.rfile.read(8192)
                        else:
                            block = cherrypy.request.rfile.read(bytesRemaining)
                        file_object.write(block)
                        bytesRemaining -= 8192
                        if bytesRemaining <= 0: break
                    file_object.seek(0)
                    #If the file didn't get all the way there
                    if long(os.path.getsize(file_object.name)) != long(fileSizeBytes): #The file transfer stopped prematurely, take out of transfers and queue partial file for deletion
                        fileUploadComplete = False
                        logging.debug("[system] [upload] [File upload was prematurely stopped, rejected]")
                        #fl.queue_for_deletion(tempFileName)
                        if tempFileName in cherrypy.active_temp_files:
                            cherrypy.active_temp_files.remove(tempFileName)
                        fMessages.append("The file %s did not upload completely before the transfer ended" % fileName)
                else:
                    formFields = myFieldStorage(fp=cherrypy.request.rfile,
                                                headers=lcHDRS,
                                                environ={'REQUEST_METHOD':'POST'},
                                                keep_blank_values=True)
                    file_object = formFields['fileName']
                    fileName = file_object.filename.split(os.path.sep)[-1]
                    addToUploads = True
                    #if str(type(upFile.file)) == '<type \'cStringIO.StringO\'>' or isinstance(upFile.file, StringIO.StringIO): 
                        #newTempFile = get_temp_file()
                        #tempFileName = newTempFile.name.split(os.path.sep)[-1]
                        #cherrypy.active_temp_files.append(tempFileName)
                        #upFile = ProgressFile(8192, fileName, newTempFile)
                        #cherrypy.session.get("uploads").append(upFile)
                        #upFile.write(str(upFile.file.getvalue()))
                        #upFile.seek(0)
                        #cherrypy.session.get("uploads").remove(upFile)
                    tempFileName = file_object.name.split(os.path.sep)[-1]
            else:
                raise FLError(False, ["You do not have permission to upload a new logo."])
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        except Exception, e:
            fMessages.append("Unable to upload new logo: %s" % str(e))
        return fl_response(sMessages, fMessages, format, None)
        
class HTTP_Groups:
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def create_group(self, groupName, groupMemberIds=None, groupScope=None, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        if groupMemberIds is not None:
            groupMemberIds = split_list_sanitized(groupMemberIds)
        else:
            groupMemberIds = []
        groupName = strip_tags(groupName)
        if groupScope is not None:
            groupScope = strip_tags(groupScope)
        else:
            groupScope = "private"
        try:
            if groupName != "":
                fl.create_group(user, groupName, groupMemberIds, groupScope)
                sMessages.append("Group %s created successfully" % str(groupName))
            else:
                fMessages.append("Group name is not valid")
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)

    @cherrypy.tools.requires_login()
    @cherrypy.expose
    def delete_group(self, groupId, format="json", **kwargs):
        user, fl, sMessages, fMessages  = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        groupIdList = split_list_sanitized(groupId)
        for groupId in groupIdList:
            try:
                groupName = fl.delete_group(user, groupId)
                sMessages.append("Group %s deleted successfully" % groupName)
            except FLError, fle:
                sMessages.extend(fle.successMessages)
                fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)
    
    @cherrypy.tools.requires_login()
    @cherrypy.expose
    def update_group(self, groupId, users=None, groupName=None, groupScope="private", format="json", **kwargs):
        user, fl, sMessages, fMessages  = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            userIds = split_list_sanitized(users)
            groupName = strip_tags(groupName)
            if groupScope is not None:
                groupScope = strip_tags(groupScope.lower())
            fl.update_group(user, groupId, userIds, groupName, groupScope)
        except FLError, fle:
            fMessages.extend(fle.failureMessages)
            sMessages.extend(fle.successMessages)
        return fl_response(sMessages, fMessages, format)
            
    @cherrypy.tools.requires_login()
    @cherrypy.expose
    def remove_user_from_group(self, userId, groupId, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        userIds = split_list_sanitized(userId)
        for memberId in userIds:
            try:
                fl.remove_user_from_group(user, memberId, groupId)
                sMessages.append("Member %s removed successfully" % memberId)
            except FLError, fle:
                fMessages.extend(fle.failureMessages)
                sMessages.extend(fle.successMessages)
        return fl_response(sMessages, fMessages, format)
            
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def add_user_to_group(self, userId, groupId, format="json", **kwargs):
        user, fl, sMessages, fMessages  = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        groupIdList = split_list_sanitized(groupId)
        for groupIdFromList in groupIdList:
            try:
                fl.add_user_to_group(user, userId, groupIdFromList)
            except FLError, fle:
                sMessages.extend(fle.successMessages)
                fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_group_members(self, groupId, format="searchbox_html", **kwargs):
        user, fl = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'])
        group = fl.get_group(user, groupId)
        searchWidget = HTTP_User.get_search_widget(HTTP_User(), "manage_groups")
        templateFile = fl.get_template_file('view_group.tmpl')
        tpl = Template(file=templateFile, searchList=[locals(),globals()])  
        return str(tpl)
        
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_groups(self, format="json"):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            groups = fl.get_user_groups(user, user.userId)
            groups = sorted(groups, key=lambda k: k.groupId)
            if format == "cli":
                groupsXML = ""
                for group in groups:
                    groupsXML += "<group id='%s' name='%s'></group>" % (group.groupId, group.groupName)
                groups = groupsXML
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        yield fl_response(sMessages, fMessages, format, data=groups)
        
class HTTP_Share:
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def create_private_share(self, fileIds, targetId=None, groupId=None, notify="no", format="json", **kwargs):
        user, fl, sMessages, fMessages  = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        fileIds = split_list_sanitized(fileIds)
        if targetId == "":
            targetId = None
        if targetId is not None: 
            targetId = strip_tags(targetId)
        if groupId == "":
            groupId = None
        if groupId is not None:
            groupId = strip_tags(groupId)
        if notify != "yes":
            notify = False
        else:
            notify = True
        targetUser = None
        data = None
        try:
            if targetId is not None:
                fl.private_share_files_user(user, fileIds, targetId, notify)
                sMessages.append("Shared file(s) successfully")
                targetUser = fl.directory.lookup_user(targetId)
            if groupId is not None:
                fl.private_share_files_group(user, fileIds, groupId, notify)
                sMessages.append("Shared file(s) successfully")
            if format=="cli":
                data = str(Template(file=fl.get_template_file('user_xml.tmpl'), searchList=[locals(),globals()])) 
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format, data=data)
    
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def create_private_attribute_shares(self, fileIds, attributeId, format="json", **kwargs):
        user, fl, sMessages, fMessages  = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            fileIds = split_list_sanitized(fileIds)
            for fileId in fileIds:
                fl.private_attribute_share_file(user, fileId, attributeId)
            sMessages.append("Successfully shared file(s) with users having the %s attribute" % attributeId )
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def delete_private_attribute_shares(self, fileIds, attributeId, format="json", **kwargs):
        user, fl, sMessages, fMessages  = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            fileIdList = split_list_sanitized(fileIds)
            for fileId in fileIdList:
                fl.delete_private_attribute_share(user, fileId, attributeId)
            sMessages.append("Successfully unshared file(s) with users having the %s attribute") % attributeId
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)
            
    @cherrypy.expose    
    @cherrypy.tools.requires_login()
    def create_public_share(self, fileId, expiration, shareType, notifyEmails, format="json", **kwargs):
        user, fl, sMessages, fMessages, shareId = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [], None)
        fileId = strip_tags(fileId)
        try:
            expiration = datetime.datetime(*(time.strptime(strip_tags(expiration), "%m/%d/%Y")[0:6]))
            try:
                notifyEmailList = split_list_sanitized(notifyEmails)
                password = None
                if shareType != "multi":
                    shareType = "single"
                if kwargs.has_key("password") and kwargs['password']!="":
                    password = kwargs['password']
                shareId = fl.public_share_file(user, fileId, password, expiration, shareType, notifyEmailList)
                sMessages.append("File shared successfully")
            except FLError, fle:
                sMessages.extend(fle.successMessages)
                fMessages.extend(fle.failureMessages)
        except Exception, e:
            if expiration is None or expiration == "":
                fMessages.append("Public shares must have an expiration date.")
            else:
                fMessages.append("Invalid expiration date format. Date must be in mm/dd/yyyy format.")
            logging.error("[%s] [createPublicShare] [Unable to create public share: %s]" % (user.userId, str(e)))
        return fl_response(sMessages, fMessages, format, data=shareId)
    
    @cherrypy.expose    
    @cherrypy.tools.requires_login()
    def delete_public_share(self, fileId, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        fileId = strip_tags(fileId)
        try:
            fl.delete_public_share(user, fileId)
            sMessages.append("Successfully unshared file")
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose     
    @cherrypy.tools.requires_login()
    def delete_share(self, fileIds, targetId=None, shareType="private", format="json"):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        shareType = strip_tags(shareType.lower())
        fileIds = split_list_sanitized(fileIds)
        for fileId in fileIds:
            flFile = fl.get_file(user, fileId)
            try:
                if shareType == "private" or shareType =="private_group":
                    if targetId is not None:
                        if shareType == "private":
                            targetName = "User not found"
                            targetUser = fl.directory.lookup_user(targetId)
                            fl.delete_private_share(user, fileId, targetId)
                            if(targetUser is not None):
                                targetName = targetUser.userDisplayName
                            sMessages.append("Successfully unshared file %s with user %s" % (flFile.fileName, targetName))
                        elif shareType == "private_group":
                            group = fl.get_group(user, targetId)
                            fl.delete_private_group_share(user, fileId, targetId)
                            sMessages.append("Successfully unshared file %s with group %s" % (flFile.fileName, group.groupName))
                    else:
                        fMessages.append("A user, group, or share ID must be specified in order to delete a share")
                elif shareType == "all":
                    fl.delete_all_shares(user, fileId)
                    sMessages.append("Successfully deleted all shares for the file %s" % flFile.fileName)
                elif shareType=="private_attribute":
                    if targetId is not None:
                        for fileId in fileIds:
                            fl.delete_private_attribute_share(user, fileId, targetId)
                        sMessages.append("Successfully unshared file(s) with users having the %s attribute" % targetId)
                    else:
                        fMessages.append("An attribute ID must be specified in order to delete a share")
                else:
                    fMessages.append("Unrecognized share type: %s" % shareType)
            except FLError, fle:
                fMessages.extend(fle.failureMessages)
                sMessages.extend(fle.successMessages)
        return fl_response(sMessages, fMessages, format)
        
    @cherrypy.expose     
    @cherrypy.tools.requires_login()
    def unhide_all_shares(self, format="json"):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            fl.unhide_all_private_shares(user)
            sMessages.append("Successfully unhid shares")
        except FLError, fle:
            fMessages.extend(fle.failureMessages)
            sMessages.extend(fle.successMessages)
        return fl_response(sMessages, fMessages, format)
        
    @cherrypy.expose     
    @cherrypy.tools.requires_login()
    def hide_share(self, fileIds, format="json"):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        fileIds = split_list_sanitized(fileIds)
        for fileId in fileIds:
            try:
                fl.hide_private_share(user, fileId)
                sMessages.append("Successfully hid share. Unhide shares in Account Settings.")
            except FLError, fle:
                fMessages.extend(fle.failureMessages)
                sMessages.extend(fle.successMessages)
        return fl_response(sMessages, fMessages, format)
                 
class HTTP_File:
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_quota_usage(self, format="json", **kwargs):
        user, fl, sMessages, fMessages, quotaMB, quotaUsed = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [], 0, 0)
        try:
            quotaMB = user.userQuota
            quotaUsedMB = fl.get_user_quota_usage(user, user.userId) / 1024 / 1024
        except FLError, fle:
            fMessages.extend(fle.failureMessages)
            sMessages.extend(fle.successMessages)
        return fl_response(sMessages, fMessages, format, data={'quotaMB': quotaMB , 'quotaUsedMB': quotaUsedMB})
    
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_download_statistics(self, fileId, startDate=None, endDate=None, format="json", **kwargs):
        user, fl, sMessages, fMessages, stats = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [], None)
        try:
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
            stats = fl.get_download_statistics(user, fileId, startDateFormatted, endDateFormatted)
        except FLError, fle:
            fMessages.extend(fle.failureMessages)
            sMessages.extend(fle.successMessages)
        return fl_response(sMessages, fMessages, format, data=stats)
        
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
                fileId = int(strip_tags(str(fileId)))
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
        fileId = strip_tags(fileId)
        try:
            flFile = fl.get_file(user, fileId)
            if kwargs.has_key("fileName"):
                flFile.fileName = strip_tags(kwargs['fileName'])
            if kwargs.has_key('notifyOnDownload'):
                if kwargs['notifyOnDownload'].lower() == "true":
                    flFile.fileNotifyOnDownload = True
                elif kwargs['notifyOnDownload'].lower() == "false":
                    flFile.fileNotifyOnDownload = False
            if kwargs.has_key('fileNotes'):
                flFile.fileNotes = strip_tags(kwargs['fileNotes'])
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
        else:
            user, sMessages, fMessages = cherrypy.session.get("user"), cherrypy.session.get("sMessages"), cherrypy.session.get("fMessages")
        cherrypy.session.release_lock()
        lcHDRS = {}
        for key, val in cherrypy.request.headers.iteritems():
            lcHDRS[key.lower()] = val
        #Get the file name
        fileName, tempFileName, fileUploadComplete = None,None,True
        
        if lcHDRS.has_key('x-file-name'):
                fileName = lcHDRS['x-file-name']
        if fileName is not None and fileName.split("\\")[-1] is not None:
            fileName = fileName.split("\\")[-1]
        if fileName is None: #This is to accomodate a poorly behaving browser that's not sending the file name
            fileName = "Unknown"
        
        fileSizeBytes = int(lcHDRS['content-length'])
                
        if lcHDRS['content-type'] == "application/octet-stream":
            if kwargs.has_key("qqfile"):
                fileName = kwargs['qqfile']
            #Create the temp file to store the uploaded file 
            file_object = get_temp_file()
            tempFileName = file_object.name.split(os.path.sep)[-1]
			logging.error("tempFileName(octet): %s" % file_object.name)
            cherrypy.active_temp_files.append(tempFileName)
            cherrypy.session.get("uploads").append(fileName)
            #Read the file from the client 
            #Create the progress file object and drop it into the transfer dictionary
            logging.error("==================Reading in File, Octet Stream=====================")
            bytesRemaining = fileSizeBytes
            while True:
                if bytesRemaining >= 8192:
                    block = cherrypy.request.rfile.read(8192)
                else:
                    block = cherrypy.request.rfile.read(bytesRemaining)
                file_object.write(block)
                bytesRemaining -= 8192
                if bytesRemaining <= 0: break
            file_object.seek(0)
            if fileName in cherrypy.session.get("uploads"):
                cherrypy.session.get("uploads").remove(fileName)
            #If the file didn't get all the way there
            if long(os.path.getsize(file_object.name)) != long(fileSizeBytes): #The file transfer stopped prematurely, take out of transfers and queue partial file for deletion
                fileUploadComplete = False
                logging.debug("[system] [upload] [File upload was prematurely stopped, rejected]")
                #fl.queue_for_deletion(tempFileName)
                if tempFileName in cherrypy.active_temp_files:
                    cherrypy.active_temp_files.remove(tempFileName)
                if fileName in cherrypy.session.get("uploads"):
                    cherrypy.session.get("uploads").remove(fileName)
                fMessages.append("The file %s did not upload completely before the transfer ended" % fileName)
        else:
            cherrypy.session.get("uploads").append(fileName)
            formFields = myFieldStorage(fp=cherrypy.request.rfile,
                                        headers=lcHDRS,
                                        environ={'REQUEST_METHOD':'POST'},
                                        keep_blank_values=True)
            if fileName in cherrypy.session.get("uploads"):
                cherrypy.session.get("uploads").remove(fileName)
            file_object = formFields['qqfile']
            logging.error("filename: %s" % file_object.filename)
            logging.error("tempFileName(mpfd): %s" % file_object.name)
            fileName = file_object.filename
            tempFileName = file_object.name.split(os.path.sep)[-1]
        
        if fileUploadComplete:
            #The file has been successfully uploaded by this point, process the rest of the variables regarding the file
            fileNotes = None
            if kwargs.has_key("fileNotes"):
                fileNotes = strip_tags(kwargs['fileNotes'])
            if fileNotes is None:
                fileNotes = ""
            else:
                fileNotes = strip_tags(fileNotes)
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
                    expiration = datetime.datetime(*time.strptime(strip_tags(expiration), "%m/%d/%Y")[0:5])
                    if maxExpiration < expiration and fl.check_permission(user, "expiration_exempt")==False:
                        raise FLError(False, ["Expiration date must be between now and %s" % maxExpiration.strftime("%m/%d/%Y")])
                    
                #Virus scanning - Tells check_in whether to scan the file, and delete if infected. For upload tickets, scanning may be set by the requestor.
                scanFile = ""
                if kwargs.has_key("scanFile"):
                    scanFile = strip_tags(kwargs['scanFile'])
                if scanFile.lower() == "true":
                    scanFile = True
                elif uploadTicket is not None and uploadTicket.scanFile:
                    scanFile = True
                else:
                    scanFile = False
                    
                #Download notification - if "yes" then the owner will be notified whenever the file is downloaded by other users
                notifyOnDownload = ""
                if kwargs.has_key("notifyOnDownload"):
                    scanFile = strip_tags(kwargs['notifyOnDownload'])
                if notifyOnDownload.lower() == "on":
                    notifyOnDownload = True
                else:
                    notifyOnDownload = False
                    
                #Build the Filelocker File objects and check them in to Filelocker
                if uploadTicket is not None:
                    newFile = File(fileName, None, fileNotes, fileSizeBytes, datetime.datetime.now(), user.userId, expiration, False, None, None, "Processing File", "local", notifyOnDownload, uploadTicket.ticketId)
                else:
                    newFile = File(fileName, None, fileNotes, fileSizeBytes, datetime.datetime.now(), ownerId, expiration, False, None, None, "Processing File", "local", notifyOnDownload, None)
                createdFile = fl.check_in_file(user, os.path.join(fl.vault, str(tempFileName)), newFile, scanFile)
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
            except KeyError, ke:
                logging.warning("[%s] [upload] [Key error deleting entry in file_transfer]" % user.userId)
            except Exception, e:
                fMessages.append("Could not upload file: %s." % str(e))
                logging.error("[%s] [upload] [Error uploading file: %s]" % (uploadKey, str(e)))
            
            #Release the temp file
            if tempFileName in cherrypy.active_temp_files:
                cherrypy.active_temp_files.remove(tempFileName)
        
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
            expiration = datetime.datetime(*time.strptime(strip_tags(expiration), "%m/%d/%Y")[0:5])
            if expiration < datetime.datetime.now():
                raise FLError(False, ["Expiration date cannot be before today"])
            #maxFileSize = strip_tags(maxFileSize)
            #if maxFileSize == "" or maxFileSize=="0" or maxFileSize == 0:
                #maxFileSize = None
            #else:
                #maxFileSize = int(strip_tags(maxFileSize))
            scanFile = strip_tags(scanFile)
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
                personalMessage = strip_tags(personalMessage)
            requestType = strip_tags(requestType.lower())
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
            ticketId = strip_tags(ticketId)
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

    #@cherrypy.expose
    #def upload_stats(self, format="json", **kwargs):
        #sMessages, fMessages, uploadStats, uploadKey = [], [], [], None
        #try:
            ##if cherrypy.session.has_key("user"):
                ##userId = cherrypy.session.get("user").userId
                ##for key in cherrypy.file_transfers.keys():
                    ##if key.split(":")[0] == cherrypy.session.get('user').userId: # This will actually get uploads by the user and uploads using a ticket they generated
                        ##for fileStat in cherrypy.file_transfers[key]:
                            ##uploadStats.append(fileStat.stat_dict())
            #if cherrypy.session.has_key("user"):
                #for key in cherrypy.session.get("uploads"):
                    #for fileStat in cherrypy.session.get("uploads")[key]:
                        #uploadStats.append(fileStat)
            #elif cherrypy.session.has_key("uploadTicket"):
                #uploadTicket = cherrypy.session.get("uploadTicket")
                #uploadKey = uploadTicket.ownerId + ":" + uploadTicket.ticketId
                #if cherrypy.file_transfers.has_key(uploadKey):
                    #for fileStat in cherrypy.file_transfers[uploadKey]:
                        #uploadStats.append(fileStat.stat_dict()) 
            #if format=='cli':
                #uploadStatsXML = ""
                #for fileUpload in uploadStats:
                    #uploadStatsXML += "<upFile "
                    #for k,v in fileUpload.iteritems():
                        #uploadStatsXML += k+"='"+v+"' "
                    #uploadStatsXML += "></upFile>"
                #uploadStats = uploadStatsXML
        #except KeyError:
            #sMessages = ["No active uploads"]
        #yield fl_response(sMessages, fMessages, format, data=uploadStats)


class HTTP_Message:
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def send_message(self, subject, body, recipientIds, expiration=None, format="json", **kwargs):
        fl, user, sMessages, fMessages = cherrypy.thread_data.flDict['app'], cherrypy.session.get("user"), [], []
        try:
            recipientIdList = split_list_sanitized(recipientIds)
            subject= strip_tags(subject)
            if kwargs.has_key("expiration"):
                expiration = kwargs['expiration']
            #Process the expiration data for the file
            maxExpiration = datetime.datetime.today() + datetime.timedelta(days=fl.maxFileLifeDays)
            if (expiration is None or expiration == "" or expiration.lower() == "never"): 
                if fl.check_permission(user, "expiration_exempt") or fl.check_admin(user): #Check permission before allowing a non-expiring upload
                    expiration = None
                else:
                    expiration = maxExpiration
            else:
                expiration = datetime.datetime(*time.strptime(strip_tags(expiration), "%m/%d/%Y")[0:5])
                if maxExpiration < expiration and fl.check_permission(user, "expiration_exempt")==False:
                    raise FLError(False, ["Expiration date must be between now and %s." % maxExpiration.strftime("%m/%d/%Y")])
            newMessage = Message(subject, body, datetime.datetime.now(), user.userId, expiration, recipientIdList)
            fl.send_message(user, newMessage)
            sMessages.append("Message \"%s\" sent." % subject)
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        except Exception, e:
            fMessages.append("Invalid expiration date format. Date must be in mm/dd/yyyy format.")
        return fl_response(sMessages, fMessages, format)
            
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_new_message_count(self, format="json", **kwargs):
        fl, user, sMessages, fMessages, newMessageCount = cherrypy.thread_data.flDict['app'], cherrypy.session.get("user"), [], [], []
        try:
            newMessageCount = fl.get_new_message_count(user)
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format, data=newMessageCount)
            
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_messages(self, format="json", **kwargs):
        fl, user, sMessages, fMessages, responseData = cherrypy.thread_data.flDict['app'], cherrypy.session.get("user"), [], [], None
        messagesList, recvMessagesList, sentMessagesList, messageIdList = [], [], [], None
        try:
            if kwargs.has_key("messageIds"):
                messageIdList = split_list_sanitized(kwargs['messageIds'])
            recvMessages = fl.get_received_messages(user, user.userId, messageIdList)
            sentMessages = fl.get_sent_messages(user, user.userId, messageIdList)
            if format == "cli":
                responseData = str(Template(file=fl.get_template_file('messages_xml.tmpl'), searchList=[locals(),globals()]))
            else:
                for message in recvMessages:
                    messageDict = message.get_dict()
                    messageBody = strip_tags(cgi.escape(messageDict['body']), True)
                    messageDict['body'] = str(Template("$messageBody", searchList=[locals()], filter=WebSafe))
                    recvMessagesList.append(messageDict)
                    
                for message in sentMessages:
                    messageDict = message.get_dict()
                    messageBody = strip_tags(cgi.escape(messageDict['body']), True)
                    messageDict['body'] = str(Template("$messageBody", searchList=[locals()], filter=WebSafe))
                    sentMessagesList.append(messageDict)
                messagesList.append(recvMessagesList)
                messagesList.append(sentMessagesList)
                responseData = messagesList
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format, data=responseData)
        
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def read_message(self, messageId, format="json", **kwargs):
        fl, user, sMessages, fMessages = cherrypy.thread_data.flDict['app'], cherrypy.session.get("user"), [], []
        try:
            fl.read_message(user, messageId)
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)
        
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def delete_messages(self, messageIds, format="json", **kwargs):
        fl, user, sMessages, fMessages = cherrypy.thread_data.flDict['app'], cherrypy.session.get("user"), [], []
        try:
            messageIdList = split_list_sanitized(messageIds)
            for messageId in messageIdList:
                fl.delete_message(user, messageId)
            sMessages.append("Message(s) deleted")
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)
            
class HTTP_User:
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def update_user(self, emailAddress, format="json", **kwargs):
        fl, user, sMessages, fMessages = cherrypy.thread_data.flDict['app'], cherrypy.session.get("user"), [], []
        updatedUserObject = User(user.userFirstName, user.userLastName, emailAddress, user.userQuota, user.userLastLogin, user.userTosAcceptDatetime, user.userId)
        try:
            if kwargs.has_key("password") and kwargs.has_key("confirmPassword"):
                if kwargs['password'] != kwargs['confirmPassword']:
                    fMessages.append("Passwords do match. Please retype your new password")
                elif kwargs['password'] != None and kwargs['password'] != "":
                    fl.reset_password(user, user.userId, kwargs['password'])
                    sMessages.append("Password successfully changed")
                else:
                    fMessages.append("Password cannot be blank")
            fl.update_user(user, updatedUserObject)
            sMessages.append("Email address successfully updated")
        except FLError, fle:
            fMessages.extend(fle.failureMessages)
            sMessages.extend(fle.successMessages)
        return fl_response(sMessages, fMessages, format)
    
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def switch_roles(self, roleUserId=None, format="json", **kwargs):
        user, fl= (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'])
        try:
            if roleUserId is None:
                cherrypy.session['user'] = fl.get_user(cherrypy.session.get("original_user").userId, True)
                cherrypy.session['sMessages'].append("Role reverted back to %s" % str(cherrypy.session.get("user").userId))
            elif fl.check_permission(user, "(role)%s" % roleUserId) or (cherrypy.session.has_key("original_user") and cherrypy.session.get("original_user").userId == roleUserId):
                cherrypy.session['user'] = fl.get_user(roleUserId, True)
                cherrypy.session['sMessages'].append("Role successfully changed to %s" % str(roleUserId))
            else:
                cherrypy.session['fMessages'].append("You do not have permission to switch to this role")
        except FLError, fle:
            cherrypy.session['sMessages'].extend(fle.successMessages)
            cherrypy.session['fMessages'].extend(fle.failureMessages)
        return fl_response(cherrypy.session['sMessages'], cherrypy.session['fMessages'], format)
    
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_search_widget(self, context, **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        groups = fl.get_user_groups(user, user.userId)
        userShareableAttributes = fl.get_available_attributes_by_user(user)
        tpl = Template(file=fl.get_template_file('search_widget.tmpl'), searchList=[locals(),globals()])  
        return str(tpl)
        
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def search_users(self, firstName=None, lastName=None, userId=None, format="json", external=False, **kwargs):
        user, fl, foundUsersJSON, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [], [])
        tooManyResults = False
        if external == "true":
            external = True
        else:
            external = False
        try:
            if firstName is not None or lastName is not None or userId is not None: #Must have something to search on 
                if firstName == "": firstName = None
                if lastName == "": lastName = None
                if userId == "": userId = None
                if userId is not None:
                    userId = strip_tags(userId)
                if firstName is not None:
                    firstName = strip_tags(firstName)
                if lastName is not None:
                    lastName = strip_tags(lastName)
                foundUsers = fl.search_users(external, firstName, lastName, userId)
                for foundUser in foundUsers:
                    foundUsersJSON.append({"displayName": foundUser.userDisplayName, "userId": foundUser.userId})
                sMessages.append("User search complete")
            else:
                fMessages.append("Please specify the first name, last name, or username of the user for whom you are searching")
        except FLError, fle:
            if fle.partialSuccess:
                tooManyResults = True
            else:
                logging.error("[%s] [searchUsers] [Errors during directory search: %s]" % (user.userId, str(fMessages)))
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
      
        if format=="json":
            return fl_response(sMessages, fMessages, format, data=foundUsersJSON)
        elif format=="autocomplete":
            shareLinkList = []
            if len(fMessages) > 0:
                shareLinkList.append({'value': 0, 'label': fMessages[-1]})
                if tooManyResults:
                    fMessages = [] #no need for a failure message on too many results, that'll display in result window
                sMessage = [] #We don't need to flash a success message every time a search completes
            else:
                for foundUser in foundUsersJSON:
                    shareLinkList.append({'value': foundUser['userId'], 'label': foundUser['displayName']})
            return fl_response(sMessages, fMessages, "json", data=shareLinkList) #This is kind of a hack since autocomplete requires a unique data structure, eventually we may be able to move this to the formatter
            
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
            
class Root:
    fl = None
    share_interface = HTTP_Share()
    file_interface = HTTP_File()
    group_interface = HTTP_Groups()
    admin_interface = HTTP_Admin()
    user_interface = HTTP_User()
    message_interface = HTTP_Message()
    cli_interface = HTTP_CLI()
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
                    setup_session(currentUser)
                    fl.record_login(cherrypy.session.get("user"), cherrypy.request.remote.ip)
                    raise cherrypy.HTTPRedirect(fl.rootURL)
                else: #This should only happen in the case of a user existing in the external directory, but having never logged in before
                    try:
                        newUser = fl.directory.lookup_user(username)
                        fl.install_user(newUser)
                        currentUser = fl.get_user(username, True)
                        if currentUser is not None and currentUser.authorized != False:
                            setup_session(currentUser)
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
        currentUsersList, currentUserIds, currentUploads = get_current_web_users()
        currentUploadsCount = 0
        for userId in currentUploads.keys():
            currentUploadsCount += len(currentUploads[userId])
        logsFile = open(fl.logFile)
        logs = tail(logsFile, 50)
        attributes = fl.get_available_attributes_by_user(user)
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
        sMessages, fMessages, user, fl, systemFiles = ([], [], cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [])
        if fl.check_admin(user):
            systemFiles = self.file_interface.get_user_file_list(format="list", userId="system")
        userFiles = self.file_interface.get_user_file_list(format="list")
        attributeFilesDict = fl.get_attribute_shares_by_user(user, user.userId)
        sharedFiles = self.file_interface.get_files_shared_with_user_list(format="list")
        logoPath = fl.get_logo()
        response = ""
        if kwargs.has_key("format") and kwargs['format'] == "cli":
            groups = fl.get_user_groups(user, user.userId)
            groupShares = fl.get_private_group_shares_by_user(user, user.userId)
            groupFileShareDict = {}
            for groupShare in groupShares:
                if groupFileShareDict.has_key(str(groupShare.targetId)) == False:
                    groupFileShareDict[str(groupShare.targetId)] = []
                groupFileShareDict[str(groupShare.targetId)].append(groupShare.fileId)
            xml = str(Template(file=fl.get_template_file('files_xml.tmpl'), searchList=[locals(),globals()]))
            sMessages.append("Successfully got the xml of the files")
            response =  fl_response(sMessages, fMessages, "cli", data=xml)
        else:
            defaultExpiration = datetime.date.today() + (datetime.timedelta(days=fl.maxFileLifeDays))
            uploadTickets = fl.get_upload_tickets_by_user(user, user.userId)
            userShareableAttributes = fl.get_available_attributes_by_user(user)
            response = Template(file=fl.get_template_file('files.tmpl'), searchList=[locals(),globals()])
        return str(response)
        
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
    @cherrypy.tools.requires_login()
    def get_server_messages(self, format="json", **kwargs):
        sMessages, fMessages = [], []
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

def fl_response(sMessages, fMessages, format, data=None):
    if format=="json":
        global JSON_WRITE
        jsonDict = {'sMessages': sMessages, 'fMessages': fMessages}
        if data is not None: jsonDict['data'] = data
        return str(JSON_WRITE(jsonDict))
    elif format=="autocomplete":
        pass
    elif format=="cli":
        fl = cherrypy.thread_data.flDict['app']
        tpl = str(Template(file=fl.get_template_file('cli_response.tmpl'), searchList=[locals(),globals()]))
        return str(tpl)
    else:
        return "Successes: %s, Failures: %s" % (str(sMessages), str(fMessages))

def setup_session(currentUser):
    cherrypy.session['user'], cherrypy.session['original_user'], cherrypy.session['uploads'], cherrypy.session['sMessages'], cherrypy.session['fMessages'] = currentUser, currentUser, [], [], []

def get_current_web_users():
    sessionCache = {}
    currentUserIds, currentUsers, currentUploads = [], [], {}
    if cherrypy.config['tools.sessions.storage_type'] == "db":
        sessionCache = cherrypy.session.get_all_sessions()
    else:
        sessionCache = cherrypy.session.cache
    for key in sessionCache.keys():
        try:
            if sessionCache[key][0].has_key('user') and sessionCache[key][0]['user'] is not None and sessionCache[key][0]['user'].userId not in currentUserIds:
                currentUser = sessionCache[key][0]['user']
                currentUsers.append(currentUser)
                currentUserIds.append(currentUser.userId)
                for upload in sessionCache[key][0]['uploads']:
                    if currentUploads.has_key(currentUser.userId):
                        currentUploads[currentUser.userId].append(upload)
                    else:
                        currentUploads[currentUser.userId] = [upload,]
        except Exception, e:
            logging.error("[%s] [admin] [Unable to read user session: %s]" % (user.userId, str(e)))
    return currentUsers, currentUserIds, currentUploads

def strip_tags(value, message=False):
    """Return the given HTML with all tags and dangerous characters stripped."""
    if message:
        p = re.compile(r'<.*?>')
        return p.sub('',value)
    else:
        return re.sub(r'[^a-zA-Z0-9\.@_+:;=,\s\'/\\\[\]-]', '', value)

def tail( f, window=20 ):
    try:
        f.seek( 0, 2 )
        bytes= f.tell()
        size= window
        block= -1
        while size > 0 and bytes+block*1024  > 0:
            # If your OS is rude about small files, you need this check
            # If your OS does 'the right thing' then just f.seek( block*1024, 2 )
            # is sufficient
            if (bytes+block*1024 > 0):
                ##Seek back once more, if possible
                f.seek( block*1024, 2 )
            else:
                #Seek to the beginning
                f.seek(0, 0)
            data= f.read( 1024 )
            linesFound= data.count('\n')
            size -= linesFound
            block -= 1
        f.seek( block*1024, 2 )
        f.readline() # find a newline
        lastBlocks= list( f.readlines() )[-window:]
        return lastBlocks
    except IOError, ioe:
        try:
            f.seek(0)
            return list(f.readlines())
        except Exception, e:
            return ["Unable to read log file: %s" % str(e)]
    except Exception, e:
        return ["Unable to read log file: %s" % str(e)]

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
    file_object = open(tempFileName, "w")
    return file_object


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
        cherrypy.server.socket_timeout = 60
        engine.start()
    except:
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

            threadLessFL.clean_temp_files(cherrypy.active_temp_files)
            threadLessFL = None #This is so that config changes will be absorbed during the next maintenance cycle
            time.sleep(720) #12 minutes
    except KeyboardInterrupt, ki:
        engine.exit()
        sys.exit(1)
    except Exception, e:
        print "Exception: %s" % str(e)
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
