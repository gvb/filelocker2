# -*- coding: utf-8 -*-

import sys
import subprocess
import shutil
import os
import logging
import datetime, time
import random
import re
try:
    from hashlib import md5
except ImportError, ie:
    from md5 import md5
from stat import ST_SIZE
import StringIO
import encryption
from dao.models.User import User
from dao.models.Permission import Permission
from dao.models.Group import Group
from dao.models.File import File
from dao.models.Attribute import Attribute
from dao.models.PublicShare import PublicShare
from dao.models.PrivateShare import PrivateShare
from dao.models.PrivateAttributeShare import PrivateAttributeShare
from dao.models.PrivateGroupShare import PrivateGroupShare
from dao.models.UploadTicket import UploadTicket
from dao.models.ActionLog import ActionLog
from dao.models.FLError import FLError
from dao.models.Parameter import Parameter
from dao import dao_creator
from mail import Mail
from directory import Directory
from CAS import CAS

__author__      = "Brett Davis"
__copyright__   = "Copyright 2011, Purdue University"
__credits__     = "Christopher Miller, Brett Davis"
__license__     = "Open Source License. See LICENSE.txt."
__version__     = "2.5"
__maintainer__  = "Brett Davis"
__email__       = "wbdavis@purdue.edu"
__status__      = "Production"

class Filelocker:
    """Filelocker application logic
    
    All functions will return whether the function executed succesfully and 
    an output message of what was done as a 2 value tuple.""" 
    
    def __init__(self, config):
        dbType = config['database']["dbtype"]
        dbHost = config['database']["dbhost"]
        dbUser = config['database']["dbuser"]
        dbPassword = config['database']["dbpassword"]
        dbName = config['database']["dbname"]
        self.rootURL = config["filelocker"]["rooturl"]
        self.rootPath = config["filelocker"]["rootpath"]
        self.vault = config["filelocker"]["vault"]
        self.logFile = config["global"]["log.error_file"]
        #logging.basicConfig(filename=self.logFile,format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG)
        self.isClusterMaster = True
        self.clusterMemberId = 0
        if config['filelocker'].has_key("clustermaster"): # This will allow you set up other front ends that don't run maintenance on the DB or FS
            self.isClusterMaster = config["filelocker"]["clustermaster"]
        if config['filelocker'].has_key("clustermemberid"): #Integer that will identify the temp files for each clustered instance of Filelocker for cleanup purposes
            self.clusterMemberId = config["filelocker"]["clustermemberid"]
        if config['filelocker'].has_key("loglevel"):
            self.logLevel = config["filelocker"]["loglevel"]
        self.templatePath = os.path.join(config["filelocker"]["rootpath"],"templates")
        self.clientPath = os.path.join(config["filelocker"]["rootpath"],"clients")
        self.db = dao_creator.get_dao(dbType, dbHost, dbUser, dbPassword, dbName)
        self.maxFileLifeDays = int(self.db.getParameter("max_file_life_days").value)
        self.maxFileUploadSize = int(self.db.getParameter("max_file_size").value)
        self.defaultQuotaMB = self.db.getParameter("default_quota").value
        self.deleteCommand = self.db.getParameter("delete_command").value
        self.deleteArguments = self.db.getParameter("delete_arguments").value
        self.orgName = self.db.getParameter("org_name").value
        self.orgURL = self.db.getParameter("org_url").value
        self.adminEmail = self.db.getParameter("admin_email").value
        self.antiVirusCommand = self.db.getParameter("antivirus_command").value
        self.fileCommand = self.db.getParameter("file_command").value
        self.authType = self.db.getParameter("auth_type").value
        self.banner = self.db.getParameter("banner").value
        self.maxUserInactivityDays = 90
        if self.db.getParameter("user_inactivity_expiration") is not None:
            self.maxUserInactivityDays = int(self.db.getParameter("user_inactivity_expiration").value)
        self.geotagging = False
        if self.db.getParameter("geotagging") is not None and self.db.getParameter("geotagging").value.lower() == "yes":
            self.geotagging = True
        if self.authType == "cas":
            self.CAS = CAS(self.db.getParameter("cas_url").value)     
        self.mailConfig = {}
        self.mailConfig['smtpSender'] = self.db.getParameter("smtp_sender").value
        self.mailConfig['smtpServer'] = self.db.getParameter("smtp_server").value
        self.mailConfig['smtpStartTLS'] = False
        if self.db.getParameter("smtp_start_tls").value.lower() == "yes":
            self.mailConfig['smtpStartTLS'] = True
        self.mailConfig['smtpPort'] = int(self.db.getParameter("smtp_port").value)
        self.mailConfig['smtpAuthRequired'] = False
        if self.db.getParameter("smtp_auth_required").value.lower() == "yes":
            self.mailConfig['smtpAuthRequired'] = True
        self.mailConfig['smtpUser'] = self.db.getParameter("smtp_user").value
        self.mailConfig['smtpPass'] = self.db.getParameter("smtp_pass").value
        self.mailConfig['smtpObscureLinks'] = False
        if self.db.getParameter("smtp_obscure_links") is not None:
            if self.db.getParameter("smtp_obscure_links").value.lower() == "yes":
                self.mailConfig['smtpObscureLinks'] = True
        self.directoryConfig = {}
        self.directoryConfig['directory_type'] = self.db.getParameter("directory_type").value
        self.directoryConfig['ldap_host'] = self.db.getParameter("ldap_host").value
        self.directoryConfig['ldap_bind_dn'] = self.db.getParameter("ldap_bind_dn").value
        self.directoryConfig['ldap_bind_user'] = self.db.getParameter("ldap_bind_user").value
        self.directoryConfig['ldap_bind_pass'] = self.db.getParameter("ldap_bind_pass").value
        self.directoryConfig['ldap_is_active_directory'] = self.db.getParameter("ldap_is_active_directory").value
        self.directoryConfig['ldap_domain_name'] = self.db.getParameter("ldap_domain_name").value
        self.directoryConfig['ldap_user_name_attr'] = self.db.getParameter("ldap_user_name_attr").value
        self.directoryConfig['ldap_last_name_attr'] = self.db.getParameter("ldap_last_name_attr").value
        self.directoryConfig['ldap_first_name_attr'] = self.db.getParameter("ldap_first_name_attr").value
        self.directoryConfig['ldap_displayname_attr'] = self.db.getParameter("ldap_displayname_attr").value
        self.directoryConfig['ldap_email_attr'] = self.db.getParameter("ldap_email_attr").value

        self.mail = Mail(self.mailConfig)
        self.localDirectory = self.db.localDirectory
        self.directory = None
        if self.directoryConfig['directory_type'] == "local":
            self.directory = self.localDirectory
        else:
            self.directory = Directory.directory_factory(self)
        if self.localDirectory is None:
            logging.critical("[system] [init] Local Directory is None!]")
        if self.directory is None:
            logging.critical("[system] [init] [Directory is None!]")
        
    def update_config(self, user, configParameterList):
        if self.check_admin(user):
            try:
                for configParameter in configParameterList:
                    logging.debug("[system] [updateConfig] [Running setParameter for param: %s]" % str(configParameter))
                    self.db.setParameter(configParameter)
            except Exception, e:
                raise FLError(False, ["Unable to update config parameters: %s" % str(e)])
        else:
            raise FLError(False, ["You do not have permission to update configuration parameters"])

    def get_config(self, user):
        if self.check_admin(user):
            try:
                return self.db.getAllParameters()
            except Exception, e:
                raise FLError(False, ["Unable to get config parameters: %s" % str(e)])
        else:
            raise FLError(False, ["You do not have permission to view configuration parameters"])
    
    def save_custom_template(self, user, templateName, templateText):
        if self.check_admin(user):
            try:
                filePath = os.path.join(self.vault, "custom", templateName)
                if os.path.exists(os.path.join(self.vault, "custom")) == False:
                    os.mkdir(os.path.join(self.vault, "custom"))
                templateFile = open(filePath, "w")
                templateFile.write(templateText)
                templateFile.close()
            except Exception, e:
                logging.error("Problem saving custom template: %s" % str(e))
                raise FLError(False, ["Unable to save template: %s" % str(e)])
        else:
            raise FLError(False, ["You must be an administrator to save custom templates."])
        
    def delete_custom_template(self, user, templateName):
        if self.check_admin(user):
            try:
                filePath = os.path.join(self.vault, "custom", templateName)
                if os.path.exists(filePath): #This causes no problems if the tempate doesn't already exist
                    os.remove(filePath)
            except Exception, e:
                logging.error("Problem deleting custom template: %s" % str(e))
                raise FLError(False, ["Unable to delete template: %s" % str(e)])
        else:
            raise FLError(False, ["You must be an administrator to save custom templates."])
    
    def check_permission(self, user, permissionId):
        try:
            if self.db.checkUserPrivilege(user.userId, permissionId) or self.check_admin(user):
                return True
            else: 
                return False
        except Exception, e:
            raise FLError(False, ['Unable to check permission: %s' % str(e)])
        
    def verify_CLIlogin(self, userId, hostIPv4, hostIPv6, CLIkey):
        try:
            return self.db.verifyCLILogin(userId, hostIPv4, hostIPv6, CLIkey)
        except Exception, e:
            raise FLError(False, ["Unable to verify CLI login: %s" % str(e)])
            return False

    def create_CLIkey(self, userId, hostIPv4, hostIPv6):
        CLIkey = str(os.urandom(32).encode('hex'))[0:32]
        try:
            self.db.createCLIKey(userId, hostIPv4, hostIPv6, CLIkey)
            return CLIkey
        except Exception, e:
            raise FLError(False, ["Unable to create CLI key: %s" % str(e)])
    
    def get_CLIkey(self, userId, hostIPv4, hostIPv6):
        try:
            cliKey = self.db.getCLIKey(userId, hostIPv4, hostIPv6)
            return cliKey
        except Exception, e:
            logging.error("Problem getting clikey: %s" % str(e))
            raise FLError(False, ["Unable to search for pre-existing CLI Key: %s" % str(e)]) 
        
    def get_CLIkey_list(self, userId):
        try:
            return self.db.getCLIKeyList(userId)
        except Exception, e:
            raise FLError(False, ["Unable to get CLI key list: %s" % str(e)])
        
    def delete_CLIkey(self, userId, hostIPv4=None, hostIPv6=None):
        try:
            self.db.deleteCLIKey(userId, hostIPv4, hostIPv6)
        except Exception, e:
            raise FLError(False, ["Unable to delete CLI key: %s" % str(e)])
        
    def install_user(self, user):
        try:
            if user is not None:
                if user.userQuota is None:
                    user.userQuota = self.defaultQuotaMB
                self.db.createUser(user)
                self.log_action(user.userId, "Install User", None, "User %s (%s) installed" % (user.userDisplayName, user.userId))
            else:
                raise FLError(False, ["User %s doesn't exist in directory" % userId])
        except FLError, fle:
            raise fle
        except Exception, e:
            logging.error("[system] [installUser] [Unable to install user: %s]" % str(e))
            raise FLError(False, ["Error installing user: %s." % str(e)])
        
    def sign_tos(self, user):
        try:
            user.userTosAcceptDatetime = datetime.datetime.now()
            self.update_user(user, user)
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Unable to sign the Terms of Service: %s" % str(e)])
    
    def create_attribute(self, user, attribute):
        try:
            if self.check_admin(user):
                self.db.createAttribute(attribute)
                self.db.createPermission(Permission("(attr)%s" % attribute.attributeId, "Owner: %s" % attribute.attributeName))
            else:
                raise FLError(False, ["You do not have permission to define attributes"])
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Unable to create new attribute: %s" % str(e)])  
    
    def delete_attribute(self, user, attributeId):
        try:
            if self.check_admin(user):
                self.db.deleteAttribute(attributeId)
                self.db.deletePrivateAttributeSharesByAttributeId(attributeId)
                self.db.deletePermission("(attr)%s" % attributeId)
            else:
                raise FLError(False, ["You do not have permission to delete this attribute"])
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Unable to delete this attribute: %s" % str(e)])  

    def update_user(self, user, updatedUserObject, password=None):
        try:
            if user.userId == updatedUserObject.userId or self.check_admin(user):
                if password is None:
                    self.db.updateUser(updatedUserObject)
                else:
                    self.db.updateUser(updatedUserObject, password)
            else:
                raise FLError(False, ["You do not have permission to edit user data"])
        except Exception, e:
            raise FLError(False, ["Unable to update user information: %s" % str(e)])
            
    def reset_password(self, user, userId, password):
        try:
            if user.userId == userId or self.check_admin(user):
                userObject = self.get_user(userId)
                self.db.updateUser(userObject, password)
            else:
                raise FLError(False, ["You do not have permission to reset the password for other users"])
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Unable to reset password: %s" % str(e)])
    
    def check_admin(self, user):
        return self.db.checkUserPrivilege(user.userId, "admin")
    
    def search_users(self, external=False, firstName=None, lastName=None, userId=None):
        try:
            foundUserIds = []
            results = []
            if external:
                externalDirectoryMatches = self.directory.get_user_matches(firstName, lastName, userId)
                for foundUser in externalDirectoryMatches:
                    if foundUser.userId not in foundUserIds:
                        foundUserIds.append(foundUser.userId)
                        results.append(foundUser)
            else:
                results.extend(self.localDirectory.get_user_matches(firstName, lastName, userId))
                for foundUser in results:
                    foundUserIds.append(foundUser.userId)
            return results
        except FLError, fle:
            raise fle
        except Exception, e:
            logging.error("[system] [searchUsers] [Error while searching user directory: %s]" % str(e))
            raise FLError(False, ["Error while searching for users: %s." % str(e)])
    
    def delete_user(self, user, userId):
        try:
            if self.check_admin(user):
                self.db.deleteUser(userId)
                self.log_action(user.userId, "Delete User", "system", "User %s deleted" % userId)
        except Exception, e:
            raise FLError(False, ["Unable to delete user:  %s" % str(e)])
            logging.error("[system] [deleteUser] [Error deleting user: %s]" % str(e))

    def get_user_quota_usage(self, user, userId):
        try:
            if user.userId == userId or self.db.checkUserPrivilege(user.userId, "admin"):
                quotaUsage = self.db.getCurrentQuotaUsage(userId)
                return int(quotaUsage)
            else:
                logging.warning("[%s] [getUserQuotaUsage] [Unauthorized attempt to check user quota by %s]" % (user.userId, user.userId))
                raise FLError(False, ["You are not allowed to check quota usage of other users."])
        except Exception, e:
            logging.error("[%s] [getUserQuotaUsage] [Failed to retrieve user quota usage: %s]" % (user.userId, str(e)))
            raise FLError(False, ["Unable to retrieve quota usage:%s" % str(e)])

    def get_user(self, userId, login=False):
        try:
            import warnings
            warnings.simplefilter("ignore")
            from dao.models.FilelockerPlugin import FilelockerPlugin
            from twisted.plugin import getPlugins, IPlugin
            import plugins
            user = self.db.getUser(userId)
            if user is not None:
                attributeList = []
                uP, gP = self.get_user_permissions(userId)
                for p in uP:
                    if p.permissionId.startswith("(attr)"):
                        attributeList.append(p.permissionId.split("(attr)")[1])
                for p in gP:
                    if p.permissionId.startswith("(attr)"):
                        attributeList.append(p.permissionId.split("(attr)")[1])
                if login:
                    for flPlugin in getPlugins(FilelockerPlugin, plugins):
                        attributeList.extend(flPlugin.get_user_attributes(user.userId, self)) #Send user object off to  plugin to get the list populated
                        if flPlugin.is_authorized(user.userId, self) == False: #Checks if any plugin is going to explicitly deny this user access to Filelocker
                            user.authorized = False
                    uniqueAttributeList = []
                    for attributeId in attributeList:
                        if attributeId not in uniqueAttributeList:
                            attr = self.db.getAttribute(attributeId)
                            if attr is not None:
                                user.userAttributes.append(attr)
                            uniqueAttributeList.append(attributeId)
            return user
        except Exception, e:
            logging.error("[system] [getUser] [Unable to get user: %s]" % str(e))
            raise FLError(False, ["Unable to get user: %s" % str(e)])
    
    def get_all_users(self, user, start=None, length=None):
        try:
            if self.check_admin(user):
                users = self.db.getAllUsers(start, length)
                for flUser in users:
                    if self.db.checkUserPrivilege(flUser.userId, "admin"):
                        flUser.isAdmin = True
                return users
            else:
                logging.warning("[%s] [getAllUsers] [Unauthorized attempt to get all users by %s]" % (user.userId, user.userId))
                raise FLError(False, ["You are not allowed to get all users."])
        except Exception, e:
            logging.error("[%s] [getAllUsers] [Unable to get all users: %s]" % (user.userId, str(e)))
            raise FLError(False, ["Unable to get all users: %s" % str(e)])

    def get_user_count(self, user):
        try:
            if self.check_admin(user):
                totalUserCount = self.db.getUserCount()
                return totalUserCount
            else:
                logging.warning("[%s] [getUserCount] [Unauthorized attempt to get total user count by %s]" % (user.userId, user.userId))
                raise FLError(False, ["You are not allowed to get the total user count."])
        except Exception, e:
            logging.error("[%s] [getUserCount] [Unable to get total user count: %s]" % (user.userId, str(e)))
            raise FLError(False, ["Unable to get total user count: %s" % str(e)])
        
    def get_file_count(self, user):
        try:
            if self.check_admin(user):
                totalFileCount = self.db.getFileCount()
                return totalFileCount
            else:
                logging.warning("[%s] [getFileCount] [Unauthorized attempt to get total file count by %s]" % (user.userId, user.userId))
                raise FLError(False, ["You are not allowed to get the total file count."])
        except Exception, e:
            logging.error("[%s] [getFileCount] [Unable to get total file count: %s]" % (user.userId, str(e)))
            raise FLError(False, ["Unable to get total file count: %s" % str(e)])
        
    def get_message_count(self, user):
        try:
            if self.check_admin(user):
                totalMessageCount = self.db.getMessageCount()
                return totalMessageCount
            else:
                logging.warning("[%s] [getMessageCount] [Unauthorized attempt to get total message count by %s]" % (user.userId, user.userId))
                raise FLError(False, ["You are not allowed to get the total message count."])
        except Exception, e:
            logging.error("[%s] [getMessageCount] [Unable to get total message count: %s]" % (user.userId, str(e)))
            raise FLError(False, ["Unable to get total message count: %s" % str(e)])

    def delete_public_share(self, user, fileId):
        try:
            publicShare = self.db.getPublicShareByFileId(fileId)
            publicShareFile = self.db.getFile(fileId)
            if user.userId == publicShare.ownerId or self.check_admin(user):
                self.db.deletePublicShare(publicShare.shareId)
                self.log_action(user.userId, "Delete Public Share", None, "Public share of file %s deleted" % publicShareFile.fileName)
            else:
                raise FLError(False, ["You do not have permission to delete this public share"])
        except Exception, e:
            raise FLError(False, ["Unable to load public share: %s" % str(e)])
    
    def get_public_share(self, shareId, password=None):
        try:
            publicShare = self.db.getPublicShare(shareId)
            if publicShare is not None:
                passwordHash = None
                if password is not None:
                    passwordHash = md5(password).hexdigest()
                if (publicShare.passwordHash != None and passwordHash == None):
                    raise FLError(False, ["You must enter a password to download this file."])
                if (publicShare.passwordHash == None and publicShare.shareType == "single") or publicShare.passwordHash == passwordHash:
                    return publicShare
                else:
                    raise FLError(False, ["Invalid password."])
            else:
                return None
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Unable to load public share: %s" % str(e)])
    
    def get_public_shares_by_user(self, user, userId):
        """Get a list of public shares for the supplied userId """
        try:
            if user.userId == userId or self.db.checkUserPrivilege(user.userId, "admin"):
                publicShares = self.db.getPublicSharesByOwner(userId)
                return publicShares
            else:
                raise FLError(False, ["You do not have permission to load information on these public shares"])
        except Exception, e:
            raise FLError(False, ["Unable to load public shares:%s " % str(e)])
    
    def public_share_file(self, user, fileId, password=None, expiration=None, shareType="single", notifyEmailList = []):
        """Share a file publicly
        
        This function will share a file with the public by creating a shareId 
        which can be appended to a URL and downloaded using a password"""
        try:
            flFile = self.db.getFile(fileId)
            if (user.userId == flFile.fileOwnerId or self.check_admin(user)):
                if expiration is None:
                    expiration = datetime.date.today() + datetime.timedelta(days=self.maxFileLifeDays)
                passwordHash = None
                if password is not None:
                    passwordHash = md5(password).hexdigest()
                ps = PublicShare(fileId, user.userId, expiration, passwordHash, shareType, None)
                shareId = self.db.createPublicShare(ps)
                for recipient in notifyEmailList:
                    if recipient is not None and recipient != "":
                        self.mail.notify(self.get_template_file('public_share_notification.tmpl'), {'sender':user.userEmail, 'recipient':recipient, 'fileName':flFile.fileName, 'ownerId':user.userId, 'ownerName': user.userDisplayName, 'shareId':shareId, 'filelockerURL':self.rootURL})
                logging.info("[%s] [createPublicShare] [User shared file %s (id: %s) publicly]" % (user.userId, flFile.fileName, flFile.fileId))
                self.log_action(user.userId, "Create Public Share", None, "File %s (%s) has been shared publicly" % (flFile.fileName, flFile.fileId))
                return shareId
            else:
                logging.warning("[%s] [createPublicShare] [User tried to share an unowned file: %s - %s]" % (user.userId, flFile.fileName, flFile.fileId))
                raise FLError(False, ["You cannot share this file because you do not own it"])
        except Exception, e:
            logging.error("[%s] [createPublicShare] [Failed to create public share: %s]" % (user.userId, str(e)))
            raise FLError(False, ["Failed to create public share: %s" % str(e)])
    
    def get_private_shares_by_user(self, user, userId):
        if user.userId == userId or self.db.checkUserPrivilege(user.userId, "admin"):
            try:
                privateShares = self.db.getPrivateSharesByOwner(userId)
                return privateShares
            except Exception, e:
                raise FLError(False, ["Could not load private shares: %s" % str(e)])
        else:
            raise FLError(False, ["You do not have permission to load this private share"])
    
    def get_private_group_shares_by_user(self, user, userId):
        if user.userId == userId or self.db.checkUserPrivilege(user.userId, "admin"):
            try:
                privateGroupShares = self.db.getPrivateGroupSharesByOwner(userId)
                return privateGroupShares
            except Exception, e:
                raise FLError(False, ["Could not load private group shares: %s" % str(e)])
        else:
            raise FLError(False, ["You do not have permission to load this private share"])
    
    def get_attribute_shares_by_user(self, user, userId):
        if user.userId == userId or self.check_admin(user):
            try:
                attributeShareDictionary = {}
                for attribute in user.userAttributes:
                    attributeShareDictionary[attribute.attributeName] = self.db.getSharedFilesByAttribute(attribute.attributeId)
                for attribute in self.get_available_attributes_by_user(user):
                    if attributeShareDictionary.has_key(attribute.attributeName) == False: #This will allow users who are admins of attributes but not members to see shares with that attribute
                        attributeShareDictionary[attribute.attributeName] = self.db.getSharedFilesByAttribute(attribute.attributeId)
                return attributeShareDictionary
            except Exception, e:
                raise FLError(False, ["Could not load attribute shares: %s" % str(e)])
        else:
            raise FLError(False, ["You do not have permission to load attribute shares for this user"])
    
    def get_attribute(self, attributeId): #Anybody can do an attribute lookup
        try:
            return self.db.getAttribute(attributeId)
        except Exception, e:
            raise FLError(False, ["Could not get attribute: %s" % str(e)])
            
    def get_available_attributes_by_user(self, user): 
        """
        This function gets the attributes that a user has permission to share with.
        
        Examples of this would be a teacher for a class being able to share with all users
        who have the class as an attribute"""
        try:
            attributeList = []
            allAttributes = self.db.getAllAttributes()
            if self.check_admin(user):
                attributeList = allAttributes
            else:
                for attribute in allAttributes:
                    if self.db.checkUserPrivilege(user.userId, "(attr)%s" % attribute.attributeId):
                        attributeList.append(attribute)
            return attributeList
        except Exception, e:
            raise FLError(False, ["Unable to get available attributes by user: %s" % str(e)])
        
    def hide_private_share(self, user, fileId):
        try:
            if fileId.isdigit():
                self.db.hidePrivateShare(fileId, user.userId)
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Unable to hide private share: %s" % str(e)])
        
    def unhide_all_private_shares(self, user):
        try:
            self.db.unhideAllPrivateShares(user.userId)
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Unable to unhide all private shares: %s" % str(e)])
        
    def is_share_hidden(self, user, fileId):
        try:
            return self.db.isShareHidden(fileId, user.userId)
        except Exception, e:
            raise FLError(False, ["Unable to determine if share is hidden: %s" % str(e)])
    
    def delete_all_shares(self, user, fileId):
        try:
            flFile = self.db.getFile(fileId)
            if user.userId == flFile.fileOwnerId or self.db.checkUserPrivilege(user.userId, "admin"):
                self.db.removeSharesByFileId(fileId)
            else:
                raise FLError(False, ["You do not have permission to delete shares for this file"])
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Error removing shares for file %s: " % (str(e))])
    
    def delete_private_share(self, user, fileId, userId):
        try:
            flFile = self.db.getFile(fileId)
            if user.userId == flFile.fileOwnerId or self.db.checkUserPrivilege(user.userId, "admin"):
                self.db.deletePrivateShare(fileId, userId)
                self.log_action(user.userId, "Delete Private Share", None, "Stopped sharing file %s with %s" % (flFile.fileName, userId))
            else:
                raise FLError(False, ["You do not have permission to delete this private share"])
        except Exception, e:
            raise FLError(False, ["Could not load private share: %s" % str(e)])
        
    def delete_private_group_share(self, user, fileId, groupId):
        try:
            flFile = self.db.getFile(fileId)
            shareGroup = self.db.getGroup(groupId) 
            if (user.userId == flFile.fileOwnerId and shareGroup.ownerId) or self.db.checkUserPrivilege(user.userId, "admin"):
                self.db.deletePrivateGroupShare(fileId, groupId)
                self.log_action(user.userId, "Delete Private Group Share", None, "Stopped sharing file %s with group %s" % (flFile.fileName, shareGroup.groupName))
            else:
                raise FLError(False, ["You do not have permission to delete this private group share"])
        except Exception, e:
            raise FLError(False, ["Could not load private group share: %s" % str(e)])
    
    def delete_private_attribute_share(self, user, fileId, attributeId):
        if self.check_admin(user) or self.db.checkUserPrivilege(user.userId, "(attr)%s" % attributeId):
            try:
                self.db.deletePrivateAttributeShare(fileId, attributeId)
            except Exception, e:
                logging.error("[%s] [deletePrivateAttributeShare] [Unable to delete private attribute share: %s]" % (user.userId, str(e)))
                return FLError(False, ["Unable to delete private attribute share: %s" % str(e)])
        else:
            return FLError(False, ["You must be an administrator to delete private attribute shares"])
        
    def get_files_shared_with_user(self, user, userId):
        if user.userId == userId or self.db.checkUserPrivilege(user.userId, "admin"):
            try:
                return self.db.getFilesSharedWithUser(userId)
            except Exception, e:
                raise FLError(False, ["Unable to get shared file information: %s" % str(e)])
        else:
            raise FLError(False, ["You do not have permission to view the files shared with this user"])
    
    def get_files_shared_by_attribute(self, user, attributeId):
        auth = False
        for attribute in user.userAttributes:
            if attributeId == attribute.attributeId:
                auth = True
                break
        if auth or self.check_admin(user):
            try:
                return self.db.getSharedFilesByAttribute(attributeId)
            except:
                logging.error("[%s] [getFilesSharedByAttribute] [Unable to get files shared with users having attribute %s: %s]" % (user.userId, attributeId, str(e)))
        else:
            raise FLError(False, ["You do not have permission to get files shared with %s" % str(e)])
        
    def private_attribute_share_file(self, user, fileId, attribute):
        if self.check_admin(user) or self.db.checkUserPrivilege(user.userId, "(attr)%s" % attribute):
            try:
                paShare = PrivateAttributeShare(fileId, attribute)
                self.db.createPrivateAttributeShare(paShare)
            except:
                logging.error("[%s] [privateAttributeShareFile] [Unable to share files with users having attribute %s: %s]" % (user.userId, attribute, str(e)))
                raise FLError(False, ["Unable share file with users having attribute %s: %s" % (attribute, str(e))])
        else:
            raise FLError(False, ["You do not have permission to share a file based on user attributes"])
        
    
    def private_share_files_user(self, user, fileIds, targetId, notifyOnShare=False):
        fMessages, sMessages, successFiles = ([],[],[])
        try:
            targetUser = self.get_user(targetId)
            if targetUser is None:
                targetUser = self.directory.lookup_user(targetId)
            if targetUser is None:
                targetUser = self.localDirectory.lookup_user(targetId)
            if targetUser is None:
                raise FLError(False, ["The user %s could not be found in Filelocker or the public directory" % targetId] )
            elif targetId == user.userId:
                raise FLError(False, ["You cannot share files with yourself"])
            else:
                for fileId in fileIds:
                    try:
                        flFile = self.db.getFile(fileId)
                        if flFile is None:
                            fMessages.append("File with file ID '%s' does not exist" % fileId)
                        if flFile is not None and (flFile.fileOwnerId == user.userId or self.check_admin(user)):
                            ps = PrivateShare(fileId, user.userId, targetId)
                            self.db.createPrivateShare(ps)
                            self.log_action(user.userId, "Create Private Share", None, "File %s shared with user %s" % (flFile.fileName, targetId))
                            successFiles.append(flFile.fileName)
                            sMessages.append("Successfully shared file %s with user %s" % (flFile.fileName, targetId))
                    except Exception, e:
                        fMessages.append("Unable to share file with fileId %s: %s" % (fileId, str(e)))
                if len(successFiles)>0  and notifyOnShare:
                    try:
                        if targetUser.userEmail is not None and targetUser.userEmail != "":
                            self.mail.notify(self.get_template_file('share_notification.tmpl'),{'sender':user.userEmail,'recipient':targetUser.userEmail, 'ownerId':user.userId, 'ownerName':user.userDisplayName, 'files':successFiles, 'filelockerURL':self.rootURL})
                            self.log_action(user.userId, "Sent Email", None, "%s has been notified via email that you have shared a file with him or her." % (targetUser.userEmail))
                        else:
                            fMessages.append("%s (%s) has no email address set and will not receive notification of the share." % (targetUser.userDisplayName, targetUser.userId))
                    except Exception, e:
                        fMessage = "Unable to send email notification to %s: %s. This has not impacted the file being shared with the user, but you may need to notify the user manually that a file has been shared with him or her." % (targetUser.userEmail, str(e))
                        fMessages.append(fMessage)
                        self.log_action(user.userId, "Failure to Send Email", None, fMessage)
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Problem during sharing: %s" % str(e)])
        if len(fMessages) > 0:
            if len(sMessages) > 0:
                raise FLError(True, fMessages, sMessages)
            else:
                raise FLError(False, fMessages, sMessages)
            
    def private_share_files_group(self, user, fileIds, groupId, notifyOnShare=False):
        fMessages, sMessages, successFiles = ([],[],[])
        try:
            targetGroup = self.get_group(user, groupId)
            if targetGroup.ownerId != user.userId and self.check_admin(user)==False:
                raise FLError(False, ["You cannot share with a group (Group ID: %s) that you have not created" % str(groupId)])
            for fileId in fileIds:
                try:
                    flFile = self.db.getFile(fileId)
                    if flFile is None:
                        fMessages.append("File with file ID '%s' does not exist" % fileId)
                    if flFile is not None and (flFile.fileOwnerId == user.userId or self.check_admin(user)):
                        pgs = PrivateGroupShare(fileId, user.userId, groupId)
                        self.db.createPrivateGroupShare(pgs)
                        successFiles.append(flFile.fileName)
                        self.log_action(user.userId, "Create Private Group Share", None, "File %s shared with group %s (ID:%s)" % (flFile.fileName, targetGroup.groupName, targetGroup.groupId))
                        sMessages.append("Successfully shared file %s with group %s" % (flFile.fileName, targetGroup.groupName))
                except Exception, e:
                    fMessages.append("Unable to share file with fileId %s: %s" % (fileId, str(e)))
            if len(successFiles)>0 and notifyOnShare:
                failedEmails = []
                for groupMember in targetGroup.groupMembers:
                    try:
                        emailAddress = None
                        if groupMember.userEmail is None:
                            dirUser = self.directory.lookup_user(groupMember.userId)
                            if dirUser is not None and (dirUser.userEmail is not None and dirUser.userEmail != ""):
                                emailAddress = dirUser.userEmail
                        else:
                            emailAddress = groupMember.userEmail
                        if emailAddress is not None and emailAddress != "":
                            self.mail.notify(self.get_template_file('share_notification.tmpl'),{'sender':user.userEmail,'recipient':emailAddress, 'ownerId':user.userId, 'ownerName':user.userDisplayName, 'files':successFiles, 'filelockerURL':self.rootURL})
                        else:
                            failedEmails.append("%s (%s) does not have an email address listed" % (groupMember.userDisplayname, groupMember.userId))
                    except Exception, e:
                        failedEmails.append("%s (%s)" % (groupMember.userDisplayName, groupMember.userId))
                        fMessages.append("Unable to notify group member %s of share" % (groupMember.userDisplayName, str(e)))
                if len(failedEmails) >0:
                    self.log_action(user.userId, "Failure to Send Email", None, "The following group members could not be notified of the share via email: %s" % (",".join(failedEmails)))
                else:
                    self.log_action(user.userId, "Sent Email", None, "All users of group %s have been notified of the file share via email" % targetGroup.groupName)
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Problem during sharing: %s" % str(e)])
        if len(fMessages) > 0:
            if len(sMessages) > 0:
                raise FLError(True, fMessages, sMessages)
            else:
                raise FLError(False, fMessages, sMessages)
                
    def private_share_files(self, user, fileIds, targetIds=[], groupIds=[], notify=True, notifyOnDownload=True):
        """Share a file privately
        
        This function will share a file privately with a specific user or group"""
        flError = FLError(False, [], [])
        try:
            shareFiles = []
            for fileId in fileIds:
                flFile = self.db.getFile(fileId)
                if user.userId == flFile.fileOwnerId or self.db.checkUserPrivilege(user.userId, "admin"):
                    shareFiles.append(flFile)
                else:
                    flError.failureMessages.append("You do not own file with ID: %s, you may not share it" % fileId)
            notificationDictionary = {} #Will prevent duplicates if users are explicitly shared with and in a group using the dict keys for addresses
            for targetId in targetIds:
                try:
                    targetUser = self.db.getUser(targetId)
                    successFiles = []
                    for shareFile in shareFiles:
                        try:
                            ps = PrivateShare(shareFile.fileId, user.userId, target)
                            self.db.createPrivateShare(ps)
                            successFiles.append(shareFile.fileName)
                            self.log_action(user.userId, "Create Private Share", None, "File %s shared with user %s" % (shareFile.fileName, userId))
                            flError.successMessages.append("Successfully shared file %s with user %s" % (shareFile.fileName, targetUser.userDisplayName))
                            flError.partialSuccess = True
                        except Exception, e:
                            flError.failureMessages.append("Failed to share %s with user %s: %s. " % (shareFile.fileName, target, str(e)))
                            logging.error("[%s] [createPrivateShare] [Failed to privately share %s with user %s: %s]" % (user.userId, shareFile.fileName, target, str(e)))
                    notificationDictionary[targetUser.userEmail] = successFiles
                except Exception, e:
                    flError.failureMessages.append("Failed to load user info for %s: %s" % (str(targetId), str(e)))
            for groupId in groupIds:
                try:
                    group = self.db.getGroup(groupId)
                    successGroupFiles = []
                    if group.ownerId == user.userId or groupScope == "public":
                        for shareFile in shareFiles:
                            privateGroupShare = PrivateGroupShare(shareFile.fileId, user.userId, group.groupId)
                            self.db.createPrivateGroupShare(privateGroupShare)
                            successGroupFiles.append(shareFile.fileName)
                            self.log_action(user.userId, "Create Private Group Share", None, "File %s shared with group %s" % (shareFile.fileName, group.groupName))
                            flError.successMessages.append("Successfully shared file %s with group %s" % (shareFile.fileName, group.groupName))
                            flError.partialSuccess = True
                        for member in group.groupMembers:
                            if member.userEmail is not None and member.userEmail != "":
                                notificationDictionary[member.userEmail] = successGroupFiles
                            else:
                                if notify:
                                    flError.failureMessages.append("%s (%s) does not have an email address set and was not able to notified." % (member.userDisplayName, member.userId))
                    else:
                        flError.failureMessages.append("You do not have permission to share files with group %s" % groupId)
                except Exception, e:
                    flError.failureMessages.append("Failed to share %s with group %s: %s. " % (shareFile.fileName, group.groupName, str(e)))
                    logging.error("[%s] [createPrivateShare] [Failed to privately share %s with group %s: %s]" % (user.userId, shareFile.fileName, group.groupName, str(e)))
            if notify:
                for notificationTarget in notificationDictionary:
                    self.mail.notify(self.get_template_file('share_notification.tmpl'),{'sender':user.userEmail,'recipient':notificationTarget, 'ownerId':user.userId, 'ownerName':user.userDisplayName, 'files':notificationDictionary[notificationTarget], 'filelockerURL':self.rootURL})
            if len(flError.failureMessages) > 0: #We created this error to keep tabs on things, only raise if there were problems
                raise flError
        except FLError, fle:
            raise fle
        except Exception, e:
            logging.error("[%s] [createPrivateShare] General error while trying to share file(s) privately: %s" % (user.userId, str(e)))
            raise FLError(False, ["Couldn't privately share files: %s" % str(e)])

    def get_upload_ticket(self, user, ticketId, password=None):
        try:
            uploadTicket = self.db.getUploadTicket(ticketId)
            if user is not None:
                if user.userId == uploadTicket.ownerId or self.db.checkUserPrivilege(user.userId, "admin"):
                    return uploadTicket
                else:
                    raise FLError(False, ["You are not authorized to load this upload ticket"])
            elif uploadTicket.ticketType == "multi" and password is not None:
                if uploadTicket.check_password(password):
                    return uploadTicket
                else:
                    raise FLError(False, ["You must enter the correct password to access this upload request."])
            elif uploadTicket.ticketType == "single":
                return uploadTicket
            else:
                raise FLError(False, ["You must supply either a user or a password to load an upload ticket"])
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Unable to get upload request: %s" % str(e)])
    
    def get_upload_ticket_by_password(self, ticketId, password):
        try:
            uploadTicket = self.db.getUploadTicket(ticketId)
            if uploadTicket is None:
                raise FLError(False, ["Invalid Upload Request ID"])
            if uploadTicket.check_password(password):
                return uploadTicket
            else:
                raise FLError(False, ["You must enter the correct password to access this upload request."])
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Unable to get upload request: %s" % str(e)])
        
    def generate_upload_ticket(self, user, password, maxFileSize, expiration, scanFile=True, ticketType="single", emailAddresses=None, personalMessage=None):
        try:
            passwordHash = None
            if ticketType == "multi" and (password == None or password ==""):
                raise FLError(False, ["You cannot have a blank password for multi-use public uploads"])
            elif password is not None:
                passwordHash = md5(password).hexdigest()
            newTicket = UploadTicket(user.userId, maxFileSize, expiration, passwordHash, scanFile, ticketType)
            newTicket.ticketId = self.db.createUploadTicket(newTicket) #returns ticketId
            fMessages = []
            sMessages = []
            for recipient in emailAddresses:
                try:
                    if recipient is not None and recipient !="":
                        self.mail.notify(self.get_template_file('upload_request_notification.tmpl'), {'sender': user.userEmail, 'recipient': recipient, 'ownerId': user.userId, 'ownerName': user.userDisplayName, 'ticketId': newTicket.ticketId, 'ticketType': newTicket.ticketType, 'personalMessage': personalMessage, 'filelockerURL': self.rootURL})
                        sMessages.append("%s was notified that you requested a file upload")
                except Exception, e:
                    fMessages.append("A problem occurred while sending an email notification to %s. This person probably did not recieve the message" % recipient)
                    logging.error("[%s] [generateUploadTicket] [Unable to send notification email to %s: %s]" % (user.userId, recipient, str(e)))
            if len(fMessages) == 0:
                self.log_action(user.userId, "Create Upload Request", None, "Upload request %s generated for %s use." % (newTicket.ticketId, newTicket.ticketType))
            else:
                self.log_action(user.userId, "Create Upload Request", None, "Upload request %s generated for %s use, however problems occurred during email notification: %s" % (newTicket.ticketId, newTicket.ticketType, str(fMessages)))
                raise FLError(True, fMessages, sMessages)
            return newTicket.ticketId
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Unable to create upload request: %s" % str(e)])
    
    def delete_upload_ticket(self, user, ticketId):
        try:
            uploadTicket = self.db.getUploadTicket(ticketId)
            if uploadTicket.ownerId == user.userId or self.db.checkUserPrivilege(user.userId, "admin"):
                self.db.deleteUploadTicket(ticketId)
                self.log_action(user.userId, "Delete Upload Request", None, "Upload request %s deleted" % ticketId)
            else:
                raise FLError(False, ["You do not have permission to delete this upload request"])
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Unable to delete upload request: %s" % str(e)])
    
    def get_upload_tickets_by_user(self, user, userId):
        if user.userId == userId or self.db.checkUserPrivilege(user.userId, "admin"):
            try:
                uploadTickets = self.db.getUploadTicketsByUser(userId)
                return uploadTickets
            except Exception, e:
                raise FLError(False, ["Unable to get upload tickets: %s" % str(e)])
        else:
            raise FLError(False, ["You do not have permission to load this upload ticket"])
       
    def duplicate_and_take_file(self, user, fileId):
        try:
            flFile = self.get_file(user, fileId)
            if (self.db.getCurrentQuotaUsage(user.userId) + flFile.fileSizeBytes) >= (user.userQuota*1024*1024):
                logging.warning("[%s] [duplicateAndTakeFile] [User has insufficient quota space remaining to check in file: %s]" % (user.userId, flFile.fileName))
                raise FLError(False, ["You may not copy this file because doing so would exceed your quota"])
            flFile.fileOwnerId = user.userId
            newFileId = self.db.createFile(flFile)
            shutil.copy(os.path.join(self.vault,str(flFile.fileId)), os.path.join(self.vault,str(newFileId)))
        except FLError, fle:
            raise fle
        except Exception, e:
            logging.error("[%s] [duplicateAndTakeFile] [Unable to duplicate and take file: %s]" % (user.userId, str(e)))
            raise FLError(False, ["Unable to copy file to local repository: %s" % str(e)])
    
    #Messaging    
    def send_message(self, user, message):
        fMessages, sMessages = [], []
        try:
            self.create_encrypted_message_file(message)
            logging.error("Message %s created" % message.messageSubject)
            for recipientId in message.messageRecipients:
                try:
                    targetUser = self.get_user(recipientId)
                    if targetUser is None:
                        targetUser = self.directory.lookup_user(recipientId)
                    if targetUser is None:
                        targetUser = self.localDirectory.lookup_user(recipientId)
                    if targetUser is None:
                        raise FLError(False, ["The user %s could not be found in the directory. If this user is not listed in the directory, he or she will have to log into Filelocker before receving messages." % recipientId] )
                    self.db.createMessageRecipient(message.messageId, recipientId, None)
                except FLError, fle:
                    fMessages.extend(fle.failureMessages)
                    sMessages.extend(fle.successMessages)
            if len(fMessages) > 0:
                raise FLError(True, fMessages)
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Unable to create message: %s" % str(e)])
    
    def get_sent_messages(self, user, userId, messageIdList=None):
        try:
            messages = []
            if user.userId == userId or self.check_admin(user):
                if messageIdList is None or len(messageIdList) == 0:
                    messages = self.db.getSentMessages(userId)
                else:
                    allMessages = self.db.getSentMessages(userId)
                    for message in allMessages:
                        if message.messageId in messageIdList:
                            messages.append(message)
                for message in messages:
                    try:
                        message.messageBody = self.get_message_body(message)
                    except FLError, fle:
                        message.messageBody = "Error: Could not read the body of this message. "
                        message.messageBody += ". ".join(fle.failureMessages)
                    message.messageRecipients = self.db.getMessageRecipients(message.messageId)
                return messages
            else:
                raise FLError(False, ["You do not have permission to view messages that other users have sent"])
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Unable to get sent messages: %s" % str(e)])
    
    def get_received_messages(self, user, userId, messageIdList=None):
        try:
            messages = []
            if user.userId == userId or self.check_admin(user):
                if messageIdList is None or len(messageIdList) == 0:
                    messages = self.db.getReceivedMessages(userId)
                else:
                    allMessages = self.db.getReceivedMessages(userId)
                    for message in allMessages:
                        if message.messageId in messageIdList:
                            messages.append(message)
                for message in messages:
                    try:
                        message.messageBody = self.get_message_body(message)
                    except FLError, fle:
                        message.messageBody = "Error: Could not read the body of this message. "
                        message.messageBody += ". ".join(fle.failureMessages)
                return messages
            else:
                raise FLError(False, ["You do not have permission to view messages that other users have received"])
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Unable to get received messages: %s" % str(e)])
        
    def get_new_message_count(self, user):
        try:
            return self.db.getNewMessageCount(user.userId)
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Unable to get new message count: %s" % str(e)])
    
    def read_message(self, user, messageId):
        try:
            messageIdList = []
            allMessages = self.db.getReceivedMessages(user.userId)
            for message in allMessages:
                messageIdList.append(str(message.messageId))
            if messageId not in messageIdList:
                raise FLError(False, ["You cannot mark a message as read if you have not received a message with that ID"])
            else:
                if self.db.isMessageRead(messageId, user.userId):
                    self.db.recipientReadMessage(messageId, user.userId, datetime.datetime.now())
                else:
                    self.db.recipientReadMessage(messageId, user.userId, datetime.datetime.now())
                    message = self.db.getMessage(messageId)
                    #Two logs makes this more intuitive for recipients and senders
                    self.log_action(user.userId, "Read Message (You)", None, "You read message with subject \"%s\"" % (message.messageSubject))
                    self.log_action(message.messageOwnerId, "Read Message (Recipient)", None, "Message recipient %s read message with subject \"%s\"" % (user.userId, message.messageSubject))
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Unable to mark received messages as read: %s" % str(e)])
    
    def delete_message(self, user, messageId):
        try:
            message = self.db.getMessage(messageId)
            if user.userId == message.messageOwnerId or self.check_admin(user):
                self.db.deleteMessage(messageId)
                self.queue_for_deletion("m%s" % messageId)
            elif len(self.db.getReceivedMessages(user.userId, [messageId])) > 0: #This is a message the the user has received, just delete the recipient entry
                self.db.deleteMessageRecipient(messageId, user.userId)
            else:
                raise FLError(False, ["You do not have permission to delete this message"])
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Unable to delete message: %s" % str(e)])
    
    def delete_received_message(self, user, messageId):
        try:
            messages = self.db.getReceivedMessages(user.userId)
            foundMessage = False
            for message in messages:
                if messageId == message.messageId:
                    foundMessage = True
                    self.db.deleteReceivedMessage(user.userId, messageId)
                    break
            if foundMessage==False:
                raise FLError(False, ["You do not have permission to delete messages that you haven't received"])
        except Exception, e:
            raise FLError(False, ["Unable to delete received message: %s" % str(e)])
    
    def get_message_body(self, message):
        messageBody = ""
        try:
            path = os.path.join(self.vault,"m"+str(message.messageId))
            bodyfile = open(path, 'rb')
            salt = bodyfile.read(16)
            decrypter = encryption.new_decrypter(message.messageEncryptionKey, salt)
            endOfFile = False
            readData = bodyfile.read(1024 * 8)
            data = decrypter.decrypt(readData)
            #If the data is less than one block long, just process it and send it out
            if len(data) < (1024*8):
                padding = int(str(data[-1:]),16) 
                #A 0 represents that the file had a multiple of 16 bytes, and 16 bytes of padding were added
                if padding==0: 
                    padding=16
                endOfFile = True
                messageBody += data[:len(data)-padding]
            else:
                #For multiblock files
                while True:
                    if endOfFile:
                        break
                    next_data = decrypter.decrypt(dFile.read(1024*8))
                    if (next_data is not None and next_data != "") and not len(next_data)<(1024*8):
                        yData = data
                        data = next_data
                        messageBody += yData
                    #This prevents padding going across block boundaries by aggregating the last two blocks and processing
                    #as a whole if the next block is less than a full block (signifying end of file)
                    else:
                        data = data + next_data
                        padding = int(str(data[-1:]),16) 
                        #A 0 represents that the file had a multiple of 16 bytes, and 16 bytes of padding were added
                        if padding==0: 
                            padding=16
                        endOfFile = True
                        messageBody += data[:len(data)-padding]
            return messageBody
        except Exception, e:
            raise FLError(False, ["Unable to read message body: %s" % str(e)])
            
    def create_encrypted_message_file(self, message):
        try:
            message.messageEncryptionKey = encryption.generatePassword()
            message.messageId = self.db.createMessage(message)
            f = open(os.path.join(self.vault,"m"+str(message.messageId)), "wb")
            encrypter, salt = encryption.new_encrypter(message.messageEncryptionKey)
            padding, endOfFile = (0, False)
            newFile = StringIO.StringIO(message.messageBody)
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
        except IOError, ioe:
            logging.critical("[%s] [createEncryptedMessageFile] [There was an IOError while checking in new file: %s]" % (message.messageOwnerId,str(ioe)))
            raise FLError(False, ["There was an IO error while uploading: %s. The administrator has been notified of this error." % str(ioe)])
        except Exception, e:
            logging.critical("[%s] [createEncryptedMessageFile] [There was an Error while checking in new file: %s]" % (message.messageOwnerId,str(e)))
            raise FLError(False, ["There was an error while uploading: %s. The administrator has been notified of this error." % str(e)])
    #End Messaging section
    def check_in_requested_file(self, uploadTicket, flFile, ip=None, dnsName=None, identifier=None):
        user = self.get_user(uploadTicket.ownerId)
        details = ""
        try:
            self.check_in_file(user, flFile)
            if identifier is not None:
                details += " Uploader claimed to be %s." % identifier
            if uploadTicket.ticketType == "single":
                self.delete_upload_ticket(user, uploadTicket.ticketId)
                details +=" Single use upload request has expired."
            self.log_action(user.userId, "Upload Requested File", None, "File %s uploaded from IP: %s (%s) %s" % (flFile.fileName, ip, dnsName, details))
        except FLError, fle:
            raise fle

    def check_in_file(self, user, filePath, flFile, mustPassAvScan=True):
        tempFileName = filePath.split(os.path.sep)[-1]
        
        #Virus scanning if requested
        if mustPassAvScan:
            avCommandList = self.antiVirusCommand.split(" ")
            avCommandList.append(os.path.join(self.vault, tempFileName))
            try:
                p = subprocess.Popen(avCommandList, stdout=subprocess.PIPE)
                output = p.communicate()[0]
                if(p.returncode != 0):
                    logging.warning("[%s] [checkInFile] [File %s did not pass requested virus scan, return code: %s, output: %s]" % (user.userId, flFile.fileName, p.returncode, output))
                    self.queue_for_deletion(tempFileName)
                    raise FLError(False, ["File %s did not pass the requested virus scan." % flFile.fileName])
                else:
                    flFile.filePassedAvScan = True
            except OSError, oe:
                #logging.critical("[%s] [checkInFile] [AVSCAN execution failed: %s]", (user.userId, str(oe)))
                raise FLError(False, ["System was unable to complete the virus scan on %s(%s): %s." % (flFile.fileName, filePath, str(oe))])
            except FLError, fle:
                raise fle
        else: flFile.filePassedAvScan = False
        #Determine file size and check against quota
        try:
            flFile.fileSizeBytes =  os.stat(filePath)[ST_SIZE]
        except Exception, e:
            flFile.fileSizeBytes = 0
            logging.critical("[%s] [checkInFile] [Unable to get file size: %s]" % (user.userId, str(e)))
            raise FLError(False, ["Could not check in file, unable to determine file size: %s" % str(e)])
        
        if (self.db.getCurrentQuotaUsage(user.userId) + flFile.fileSizeBytes) >= (user.userQuota*1024*1024):
            logging.warning("[%s] [checkInFile] [User has insufficient quota space remaining to check in file: %s]" % (user.userId, flFile.fileName))
            raise FLError(False, ["You may not upload this file as doing so would exceed your quota"])

        #determine file type
        flFile.fileType = "Unknown"
        try:
            fileres = os.popen("%s %s" % (self.fileCommand, filePath), "r")
            data = fileres.read().strip()
            fileres.close()
            if data.find(";") >= 0:
                (ftype, lo) = data.split(";")
                del(lo)
                flFile.fileType = ftype.strip()
            else:
                flFile.fileType = data.strip()
        except Exception, e:
            logging.error("[%s] [checkInFile] [Unable to determine file type: %s]" % (user.userId, str(e)))
  
        try:
            #Logic is a little strange here - if the user supplied an encryptionKey, then don't save it with the file
            encryptionKey = None
            #if flFile.fileEncryptionKey is None or flFile.fileEncryptionKey == "":
            flFile.fileEncryptionKey = encryption.generatePassword()
            encryptionKey = flFile.fileEncryptionKey
            #else:
                #encryptionKey = flFile.fileEncryptionKey
                #flFile.fileEncryptionKey = None
            flFile.fileId = self.db.createFile(flFile)
            newFile = open(filePath, "rb")
            f = open(os.path.join(self.vault, str(flFile.fileId)), "wb")
            encrypter, salt = encryption.new_encrypter(encryptionKey)
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
            flFile.fileStatus = "Checked In"
            self.db.updateFile(flFile)
            self.log_action(user.userId, "Check In File", None, "File %s (%s) checked in to Filelocker" % (flFile.fileName, flFile.fileId))
            logging.info("[%s] [checkInFile] [User checked in a new file %s]" % (user.userId, flFile.fileName))
            return flFile
        except IOError, ioe:
            logging.critical("[%s] [checkInFile] [There was an IOError while checking in new file: %s]" % (user.userId,str(ioe)))
            raise FLError(False, ["There was an IO error while uploading: %s. The administrator has been notified of this error." % str(ioe)])
        except Exception, e:
            logging.critical("[%s] [checkInFile] [There was an Error while checking in new file: %s]" % (user.userId,str(e)))
            raise FLError(False, ["There was an error while uploading: %s. The administrator has been notified of this error." % str(e)])
        
    def update_file(self, user, flFile):
        try:
            dbFileCopy = self.db.getFile(flFile.fileId)
            if dbFileCopy.fileOwnerId == user.userId or self.db.checkUserPrivilege(user.userId, "admin"):
                self.db.updateFile(flFile)
            else:
                raise FLError(False, ["You do not have permission to update this file"])
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Unable to update file: %s" % str(e)])

    def delete_file(self, user, fileId):
        try:
            flFile = self.db.getFile(fileId)
            if flFile.fileOwnerId == user.userId or self.db.checkUserPrivilege(user.userId, "admin"):
                self.db.removeSharesByFileId(fileId)
                self.db.deleteFile(fileId)
                self.db.unhideByFileId(fileId)
                self.queue_for_deletion(str(fileId))
                self.log_action(user.userId, "Delete File", None, "File %s (%s) deleted" % (flFile.fileName, flFile.fileId))
            else:
                logging.warning("[%s] [deleteFile] [Unauthorized user tried to delete file]" % (user.userId))
                raise FLError(False, ["You do not have permission to delete this file"])
        except FLError, fle:
            raise fle
        except Exception, e:
            logging.error("[%s] [deleteFile] [Unable to delete file: %s]" % (user.userId, str(e)))
            raise FLError(False, ["Unable to delete file: %s" % str(e)])
        
    def get_files_by_user(self, user, userId):
        if user.userId == userId or self.db.checkUserPrivilege(user.userId, "admin"):
            try:
                fileList = self.db.getFilesByOwner(userId)
                return fileList
            except Exception, e:
                raise FLError(False, ["Unable to load file list for user: %s:%s" % (userId, str(e))])
        else:
            raise FLError(False, ["You do not have permission to load these files"])
    
    def get_files_by_upload_ticket(self, uploadTicket):
        try:
            fileList = self.db.getFilesByUploadTicket(uploadTicket.ticketId)
            return fileList
        except Exception, e:
            raise FLError(False, ["Error loading file list by upload ticket: %s" % str(e)])
        
    def get_file(self, user, fileId):
        try:
            flFile = self.db.getFile(fileId)
            if flFile is None:
                logging.error("[%s] [getFile] [Unable to load file with ID: %s]" % (user.userId, str(fileId)))
                raise FLError(False, ["This file (ID: %s) does not exist or is unable to be loaded" % fileId])
            if flFile.fileOwnerId == user.userId: 
                return flFile
            else: # this is separate because it requires additional SQL calls to determine and should be avoided if possible
                sharedFilesList = self.db.getFilesSharedWithUser(user.userId)
                sharedFileIdList = []
                for sharedFile in sharedFilesList:
                    sharedFileIdList.append(sharedFile.fileId)
                for attribute in user.userAttributes:
                    flFiles = self.db.getSharedFilesByAttribute(attribute.attributeId)
                    for flFile in flFiles:
                        sharedFileIdList.append(flFile.fileId)
                if flFile.fileId in sharedFileIdList or self.db.checkUserPrivilege(user.userId, "admin"):
                    return flFile
                else:
                    raise FLError(False, ["You do not have access to this file"])
        except FLError, fle:
            raise fle
        except Exception, e:
            logging.error("[%s] [getFile] [Unable to get file: %s]" % (user.userId, str(e)))
            raise FLError(False, ["Error getting file: %s" % str(e)])
    
    def file_download_complete(self, user, fileId, publicShareId=None):
        try:
            flFile = self.get_file(user, fileId)
            if user.userId != flFile.fileOwnerId and flFile.fileNotifyOnDownload:
                try:
                    owner = self.get_user(flFile.fileOwnerId)
                    if owner.userEmail is not None and owner.userEmail != "":
                        self.mail.notify(self.get_template_file('download_notification.tmpl'),{'sender': None, 'recipient': owner.userEmail, 'fileName': flFile.fileName, 'downloadUserId': user.userId, 'downloadUserName': user.userDisplayName})
                except Exception, e:
                    logging.error("[%s] [fileDownloadComplete] [Unable to notify user %s of download completion: %s]" % (user.userId, owner.userId, str(e)))
            
            if publicShareId is not None:
                publicShare = self.db.getPublicShare(publicShareId)
                self.log_action(flFile.fileOwnerId, "Download File", user.userId, "File %s downloaded via Public Share. [File ID: %s]" % (flFile.fileName, flFile.fileId))
                if flFile.fileNotifyOnDownload:
                    try:
                        owner = self.get_user(flFile.fileOwnerId)
                        if owner.userEmail is not None and owner.userEmail != "":
                            self.mail.notify(self.get_template_file('public_download_notification.tmpl'),{'sender': None, 'recipient': owner.userEmail, 'fileName': flFile.fileName})
                    except Exception, e:
                        logging.error("[%s] [fileDownloadComplete] [Unable to notify user %s of download completion: %s]" % (user.userId, owner.userId, str(e)))
                if publicShare.shareType == "single":
                    self.db.deletePublicShare(publicShareId)
                    self.log_action("system", "Delete Public Share", flFile.fileOwnerId, "File %s downloaded via single use public share. File is no longer publicly shared. [File ID: %s]" % (flFile.fileName, flFile.fileId))
            else:
                self.log_action(user.userId, "Download File", flFile.fileOwnerId, "File %s downloaded by user %s. [File ID: %s]" % (flFile.fileName, user.userId, flFile.fileId))
        except Exception, e:
            logging.error("[%s] [fileDownloadComplete] [Unable to finish download completion: %s]" % (user.userId, str(e)))
    
    def create_user(self, user, newUser, password=None):
        """Create a new user in the system 
        
        This function sets up a new user. Must be admin to create a new user"""

        if self.check_admin(user):
            try:
                self.db.createUser(newUser, password)
                favoritesGroup = Group("private", newUser.userId, "Favorites")
                self.db.createGroup(favoritesGroup)
                logging.info("[%s] [createUser] [Admin creation of user %s" % (user.userId, newUser.userId))
                self.log_action(user.userId, "Create User", "system", "Administrator %s created user %s" % (user.userId, newUser.userId))
            except Exception, e:
                raise FLError(False, ["Unable to create new user: %s" % str(e)])
                logging.error("[%s] [createUser] [Creation of new user %s failed by %s failed: %s]" % (user.userId, newUser.userId, user.userId, str(e)))
        else:
            logging.warning("[%s] [createUser] [Unauthorized user %s attempted to create a user %s]" % (user.userId, user.userId, newUser.userId))
            raise FLError(False, ["You are not authorized to create new users."])
    
    def make_role(self, user, roleUserId):
        try:
            if self.check_admin(user):
                roleUser = self.get_user(roleUserId)
                self.db.createPermission(Permission("(role)%s" % roleUserId, "Role: %s" % roleUser.userDisplayName))
            else:
                raise FLError(False, ["You do not have permission to create a role from a user account."])
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Unable to make user account into a role: %s" % str(e)])
    
    def delete_role(self, user, roleUserId):
        try:
            if self.check_admin(user):
                self.db.deletePermission("(role)%s" % roleUserId)
            else:
                raise FLError(False, ["You do not have permission to delete a role."])
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Unable to make user account into a role: %s" % str(e)])
    
    def get_user_roles(self, user):
        try:
            roleUsers = []
            allPermissions = self.db.getAllPermissions()
            for permission in allPermissions:
                if permission.permissionId.startswith("(role)") and self.db.checkUserPrivilege(user.userId, permission.permissionId):
                    roleUserId = permission.permissionId.split("(role)")[1]
                    roleUser = self.db.getUser(roleUserId)
                    roleUsers.append(roleUser)
            return roleUsers
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Unable to make user roles: %s" % str(e)])
        
    def create_group(self, user, groupName, groupUserIds, scope=None):
        flError = FLError(False, [], [])
        if scope is not None and scope !="private" and self.db.checkUserPrivilege(user.userId, "admin")==False:
            raise FLError(False, ["You do not have permission to create groups outside of the private scope"])
        elif groupName != "favorites" and groupName != "recent":
            if scope is None:
                scope = "private" #public, private, reserved
            try:
                groupUsers = []
                for groupUserId in groupUserIds:
                    try:
                        groupUser = self.db.getUser(groupUserId)
                        groupUsers.append(groupUser)
                        flError.partialSuccess = True
                        flError.successMessages.append("User %s successfully added to group %s" % (groupUser.userDisplayName, groupName))
                    except Exception, e:
                        flError.failureMessages.append("Unable to add user %s to group %s: %s" % (groupUserId, groupName, str(e)))
                #Clean out any text matching '(group)' in a group name
                groupName = groupName.replace("(group)", "")
                newGroup = Group(scope, user.userId, groupName, groupUsers)
                self.db.createGroup(newGroup)
                logging.info("[%s] [createGroup] [User created group named %s]" % (user.userId, groupName))
                self.log_action(user.userId, "Create Group", None, "Group %s created" % groupName)
                if len(flError.failureMessages) > 0:
                    raise flError
            except Exception, e:
                raise FLError(False, ["Unable to create group: %s" % str(e)])
    
    def update_group(self, user, groupId, userIds, groupName, groupScope):
        try:
            mGroup = self.db.getGroup(groupId)
            if mGroup.ownerId == user.userId or self.db.checkUserPrivilege(user.userId, "admin"):
                if groupName is not None:
                    mGroup.groupName = groupName.replace("(group)", "")
                mGroupUsers = []
                for user in mGroup.groupMembers:
                    gUser = self.db.getUser(user.userId)
                    if gUser is None:
                        gUser = self.directory.lookup_user(user.userId)
                    mGroupUsers.append(gUser)
                mGroup.groupMembers = mGroupUsers
                self.db.updateGroup(mGroup)
                self.log_action(user.userId, "Update Group", None, "Group %s updated" % mGroup.groupName)
            else:
                raise FLError(False, ["You do not have permission to modify this group."])
        except Exception, e:
            raise FLError(False, ["Unable to update group: %s" % str(e)])
        
    def remove_user_from_group(self, user, userId, groupId):
        try:
            group = self.get_group(user, groupId)
            if group.ownerId == user.userId or self.db.checkUserPrivilege(user.userId, "admin"):
                self.db.removeUserFromGroup(userId, groupId)
            else:
                raise FLError(False, ["You do not have permission to view or modify this group"])
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Unable to remove %s from group %s: %s" % (userId, groupId, str(e))])
        
    def add_user_to_group(self, user, userId, groupId):
        try:
            group = self.get_group(user, groupId)
            if group.ownerId == user.userId or self.db.checkUserPrivilege(user.userId, "admin"):
                if group.ownerId != userId:
                    self.db.addUserToGroup(userId, groupId)
                else:
                    raise FLError(False, ["You can not add yourself to a group"])
            else:
                raise FLError(False, ["You do not have permission to view or modify this group"])
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Unable to add %s to group %s: %s" % (userId, groupId, str(e))])

    def get_user_groups(self, user, userId):
        if userId == user.userId or self.check_admin(user):
            try:
                groups = self.db.getGroupsByUserId(userId)
                for group in groups:
                    groupMembers = []
                    for member in group.groupMembers:
                        if member.userFirstName is None and member.userLastName is None:
                            groupMembers.append(self.directory.lookup_user(member.userId))
                        else:
                            groupMembers.append(member)
                    group.groupMembers = groupMembers
                return groups
            except Exception, e:
                raise FLError(False, ["Unable to load groups: %s" % str(e)])
        else:
            raise FLError(False, ["Unable to get groups: %s" % str(e)])
    
    def get_group(self, user, groupId):
        try:
            group = self.db.getGroup(groupId)
            if group is not None and (group.ownerId == user.userId or self.db.checkUserPrivilege(user.userId, "admin")):
                groupMembers = []
                for member in group.groupMembers:
                    if member.userFirstName is None and member.userLastName is None:
                        groupMembers.append(self.directory.lookup_user(member.userId))
                    else:
                        groupMembers.append(member)
                group.groupMembers = groupMembers
                return group
            else:
                raise FLError(False, ["You do not have permission to view or modify this group"])
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Unable to load group %s: %s" % (groupId, str(e))])

    def get_all_groups(self, user):
        pass

    def delete_group(self, user, groupId):
        delGroup = self.db.getGroup(groupId)
        if delGroup.ownerId == user.userId or self.db.checkUserPrivilege(user.userId, "admin"):
            try:
                self.db.deleteGroup(groupId)
                self.log_action(user.userId, "Delete Group", None, "Group %s deleted" % delGroup.groupName)
                return delGroup.groupName
            except Exception, e:
                raise FLError(False, ["Unable to delete group: %s " % str(e)])
        else:
            raise FLError(False, ['You do not have permission to delete this group'])

    def grant_user_permission(self, user, userId, permissionId):
        if self.check_admin(user):
            if self.db.getPermission(permissionId) is not None:
                try:
                    self.db.grantUserPermission(userId, permissionId)
                except Exception, e:
                    raise FLError(False, ["Error creating granting permission: %s" % str(e)])
            else:
                raise FLError(False, ["This permission does not exist and cannot be granted"])
        else:
            raise FLError(False, ['You do not have authority to grant this permission'])
    
    def revoke_user_permission(self, user, userId, permissionId):
        if self.check_admin(user):
            try: #Don't check for existence, just in case a user has a permission that didn't get deleted when the permission itself was purged
                if user.userId == userId and permissionId == "admin":
                    raise FLError(False, ["You cannot revoke administrative privileges from your own account."])
                else:
                    self.db.revokeUserPermission(userId, permissionId)
            except FLError, fle:
                raise fle
            except Exception, e:
                raise FLError(False, ["Error revoking permission: %s" % str(e)])
        else:
            raise FLError(False, ['You do not have authority to revoke this permission'])
    
    def get_user_permissions(self, userId):
        try:
            userPermissions, groupPermissions = self.db.getPermissionsByUser(userId)
            return userPermissions, groupPermissions
        except Exception, e:
            raise FLError(False, ["Unable to get permissions for user: %s" % str(e)])
    
    def get_all_permissions(self, user):
        if self.check_admin(user):
            try:
                return self.db.getAllPermissions()
            except Exception, e:
                raise FLError(False, ["There was a problem getting available permissions: %s" % str(e)])
        else:
            raise FLError(False, ["You do not have permission to get all available permissions."])

    def record_login(self, user, ip=None, interface="Web"):
        try:
            loginTime = datetime.datetime.now()
            lUser = user.get_copy()
            lUser.userLastLogin = loginTime
            self.db.updateUser(lUser)
            self.log_action(lUser.userId, "Login", None, "User %s logged in successfully from IP %s via %s" % (lUser.userId, str(ip), interface))
        except Exception, e:
            logging.error("[system] [recordLogin] [Unable to record login for user %s: %s]" % (user.userId, str(e)))
        
    def log_action(self, user, action, affectedUser, message):
        logTime = datetime.datetime.now()
        logEntry = ActionLog(user, action, affectedUser, message, logTime)
        self.db.logAction(logEntry)

    def get_audit_log(self, user, userId=None, startDate=None, endDate=None, action=None):
        if user.userId == userId or self.check_admin(user):
            try:
                if endDate is not None:
                    endDate = endDate + datetime.timedelta(days=1)
                matchingLogs = self.db.getAuditLogs(userId, startDate, endDate, action)
                return matchingLogs
            except Exception, e:
                raise FLError(False, ["Unable to get audit logs: %s" % str(e)])
        else:
            raise FLError(False, ["You do not have permission to access the audit logs for this user"])
    
    def get_download_statistics(self, user, fileId, startDate=None, endDate=None):
        try:
            flFile = self.get_file(user, fileId)
            if flFile.fileOwnerId == user.userId or self.check_admin(user):
                if endDate is not None:
                    endDate = endDate + datetime.timedelta(days=1)
                stats = self.db.getDownloadStatistics(fileId, startDate, endDate)
                return stats
            else:
                raise FLError(False, ["You do not have permission to view download statistics for this file"])
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Unable to get download statistics for file %s: %s" % (fileId, str(e))])
        
    def get_hourly_statistics(self, user):
        try:
            if self.check_admin(user):
                hourlyStats, downloadHourlyStats, uploadHourlyStats = {}, {}, {}
                downloads = self.db.getHourlyDownloadStatistics()
                uploads = self.db.getHourlyUploadStatistics()
                for hourlyStat in downloads:
                    downloadHourlyStats[hourlyStat["hour"]] = hourlyStat["percentage_of_downloads"]
                for hourlyStat in uploads:
                    uploadHourlyStats[hourlyStat["hour"]] = hourlyStat["percentage_of_uploads"]
                hourlyStats["downloads"] = downloadHourlyStats
                hourlyStats["uploads"] = uploadHourlyStats
                return hourlyStats
            else:
                logging.warning("[%s] [getHourlyStatistics] [Unauthorized attempt to view hourly statistics by %s]" % (user.userId, user.userId))
                raise FLError(False, ["You do not have permission to view hourly statistics"])
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Unable to get hourly statistics: %s" % str(e)])
        
    def get_daily_statistics(self, user):
        try:
            if self.check_admin(user):
                dailyStats, downloadDailyStats, uploadDailyStats = {}, {}, {}
                downloads = self.db.getDailyDownloadStatistics()
                uploads = self.db.getDailyUploadStatistics()
                for dailyStat in downloads:
                    downloadDailyStats[dailyStat["date"]] = dailyStat["total"]
                for dailyStat in uploads:
                    uploadDailyStats[dailyStat["date"]] = dailyStat["total"]
                dailyStats["downloads"] = downloadDailyStats
                dailyStats["uploads"] = uploadDailyStats
                return dailyStats
            else:
                logging.warning("[%s] [getDailyStatistics] [Unauthorized attempt to view daily statistics by %s]" % (user.userId, user.userId))
                raise FLError(False, ["You do not have permission to view daily statistics"])
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Unable to get daily statistics: %s" % str(e)])
    
    def get_monthly_statistics(self, user):
        try:
            if self.check_admin(user):
                monthlyStats, downloadMonthlyStats, uploadMonthlyStats = {}, {}, {}
                downloads = self.db.getMonthlyDownloadStatistics()
                uploads = self.db.getMonthlyUploadStatistics()
                for monthlyStat in downloads:
                    downloadMonthlyStats[monthlyStat["month"]] = monthlyStat["total"]
                for monthlyStat in uploads:
                    uploadMonthlyStats[monthlyStat["month"]] = monthlyStat["total"]
                monthlyStats["downloads"] = downloadMonthlyStats
                monthlyStats["uploads"] = uploadMonthlyStats
                return monthlyStats
            else:
                logging.warning("[%s] [getMonthlyStatistics] [Unauthorized attempt to view monthly statistics by %s]" % (user.userId, user.userId))
                raise FLError(False, ["You do not have permission to view monthly statistics"])
        except FLError, fle:
            raise fle
        except Exception, e:
            raise FLError(False, ["Unable to get monthly statistics: %s" % str(e)])
    
    def get_audit_log_action_names(self, user, userId):
        if user.userId == userId or self.check_admin(user):
            try:
                actionNames = self.db.getAuditActions(userId)
                return actionNames
            except Exception, e:
                raise FLError(False, ["Unable to get audit log action names: %s" % str(e)])
        else:
            raise FLError(False, ["You do not have permission to access the audit logs for this user"])

    def get_template_file(self, fileName):
        filePath = None
        if fileName.endswith(".css"):
            if os.path.exists(os.path.join(self.vault,"custom", "css",fileName)):
                filePath = os.path.join(self.vault,"custom", "css",fileName)
        elif os.path.exists(os.path.join(self.vault,"custom",fileName)):
            filePath = os.path.join(self.vault,"custom",fileName)
        else:
            filePath = os.path.join(self.templatePath, fileName)
        return filePath
    
    def get_logo(self):
        filePath = None
        if os.path.exists(os.path.join(self.vault,"custom","logo.gif")):
            filePath = os.path.join(self.vault,"custom","logo.gif")
        else:
            filePath = os.path.join(self.rootURL, "static","images","logos","logo.gif")
        return filePath

    def check_expirations(self):
        expiredFiles = self.db.getExpiredFiles()
        for flFile in expiredFiles:
            try:
                self.db.removeSharesByFileId(flFile.fileId)
                self.db.deleteFile(flFile.fileId)
                self.queue_for_deletion(str(flFile.fileId))
                self.log_action("system", "Delete File", flFile.fileOwnerId, "File %s (ID:%s) has expired and has been purged by the system." % (flFile.fileName, flFile.fileId))
            except Exception, e:
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


if __name__ == '__main__':
    from ConfigParser import ConfigParser
    from optparse import OptionParser
    config = ConfigParser()
    p = OptionParser()
    
    p.add_option('-c', '--config', action="append", dest='configfile',
                 help="specify config file")
    p.add_option('-d', action="store_true", dest='daemonize',
                 help="run the server as a daemon")
    p.add_option('-p', '--pidfile', dest='pidfile', default=None,
                 help="store the process id in the given file")
    p.add_option('-a','--action', dest='action', default="cleanup", help="action to perform (cleanup, make_admin)")
    options, args = p.parse_args()
    config_dict = {}
    configFile = os.path.join("..","conf","filelocker.conf")
    if options.configfile is not None:
        configFile = options.configfile
    config.read(configFile)
    fl = Filelocker(config._sections)

    if options.action:
        if options.action == "cleanup":
            fl.process_deletion_queue()
            fl.clean_temp_files()
        elif options.action == "make_admin":
            username = input("What user should be promoted to admin?")
            
    
