# -*- coding: utf-8 -*-

import datetime
import MySQLdb
import logging
from DAO import DAO
import sys
from models.User import User
from models.File import File
from models.UploadTicket import UploadTicket
from models.PrivateShare import PrivateShare
from models.PrivateGroupShare import PrivateGroupShare
from models.PrivateAttributeShare import PrivateAttributeShare
from models.PublicShare import PublicShare
from models.Parameter import Parameter
from models.Group import Group
from models.Message import Message
from models.ActionLog import ActionLog
from models.FLError import FLError
from models.Attribute import Attribute
from models.Permission import Permission
from models.CLIKey import CLIKey
try:
    from hashlib import md5
except ImportError, ie:
    from md5 import md5

class MySQLDAO(DAO):
    connection = None
    dbHost = None
    dbUser = None
    dbPassword = None
    dbName = None
    db = None
    cursor = None
    def __init__(self, dbHost, dbUser, dbPassword, dbName):
        self.dbHost = dbHost
        self.dbUser = dbUser
        self.dbPassword = dbPassword
        self.dbName = dbName
        self.get_connection()
        self.localDirectory = LocalDirectory(self)
    
    def get_connection(self):
        self.db = MySQLdb.connect(self.dbHost, self.dbUser, self.dbPassword, self.dbName)
        self.cursor = self.db.cursor(cursorclass=MySQLdb.cursors.DictCursor)
    
    def get_db(self):
        return MySQLdb.connect(self.dbHost, self.dbUser, self.dbPassword, self.dbName)
        
    def getParameter(self, parameterName):
        param = None
        sql = "SELECT * FROM config WHERE config_parameter_name=%s"
        sql_args = [parameterName,]
        result = self.execute(sql, sql_args)
        if result is not None and len(result)>0:
            param = Parameter(result[0]['config_parameter_name'], result[0]['config_parameter_description'], result[0]['config_parameter_type'], result[0]['config_parameter_value'])
        return param
        
    def getAllParameters(self):
        params = []
        sql = "SELECT * FROM config"
        results = self.execute(sql, None)
        if results is not None and len(results)>0:
            for row in results:
                param = Parameter(row['config_parameter_name'], row['config_parameter_description'], row['config_parameter_type'], row['config_parameter_value'])
                params.append(param)
        return params
        
    def setParameter(self, param):
        sql = "UPDATE config SET config_parameter_value=%s WHERE config_parameter_name=%s"
        sql_args = [param.value, param.parameterName]
        self.execute(sql, sql_args)
        
#Files
    def createFile (self, flFile):
        sql = "INSERT INTO file (file_name, file_type, file_notes, file_size, file_uploaded_datetime, file_owner_id, file_expiration_datetime, file_passed_avscan, file_encryption_key, file_status, file_location, file_notify_on_download, file_upload_ticket_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        sql_args = [flFile.fileName, flFile.fileType, flFile.fileNotes, flFile.fileSizeBytes, flFile.fileUploadedDatetime, flFile.fileOwnerId, flFile.fileExpirationDatetime, flFile.filePassedAvScan, flFile.fileEncryptionKey, flFile.fileStatus, flFile.fileLocation, flFile.fileNotifyOnDownload, flFile.fileUploadTicketId]
        results, fileId = self.execute(sql, sql_args, True)
        return fileId

    def getFile (self, fileId):
        sql = "SELECT * FROM file WHERE file_id=%s"
        sql_args = [int(fileId),]
        results = self.execute(sql,sql_args)
        currentFile = None
        if results is not None and len(results)>0:
            fileR = results[0]
            currentFile = File(fileR['file_name'], fileR['file_type'], fileR['file_notes'], fileR['file_size'], fileR['file_uploaded_datetime'], fileR['file_owner_id'], fileR['file_expiration_datetime'], fileR['file_passed_avscan'], fileR['file_encryption_key'], fileR['file_id'], fileR['file_status'], fileR['file_location'], fileR['file_notify_on_download'], fileR['file_upload_ticket_id'])
        return currentFile
    
    def getExpiredFiles(self):
        sql = "SELECT * FROM file WHERE file_expiration_datetime < now()"
        sql_args = None
        results = self.execute(sql, sql_args)
        expiredFiles = []
        for row in results:
            currentFile = File(row['file_name'], row['file_type'], row['file_notes'], row['file_size'], row['file_uploaded_datetime'], row['file_owner_id'], row['file_expiration_datetime'], row['file_passed_avscan'], row['file_encryption_key'], row['file_id'], row['file_status'], row['file_location'], row['file_notify_on_download'], row['file_upload_ticket_id'])
            expiredFiles.append(currentFile)
        return expiredFiles
    
    def getFilesByOwner(self, ownerId):
        sql = "SELECT * FROM file WHERE file_owner_id=%s"
        sql_args = [ownerId,]
        results = self.execute(sql, sql_args)
        fileList = []
        for fileR in results:
            currentFile = File(fileR['file_name'], fileR['file_type'], fileR['file_notes'], fileR['file_size'], fileR['file_uploaded_datetime'], fileR['file_owner_id'], fileR['file_expiration_datetime'], fileR['file_passed_avscan'], fileR['file_encryption_key'], fileR['file_id'], fileR['file_status'], fileR['file_location'], fileR['file_notify_on_download'], fileR['file_upload_ticket_id'])
            fileList.append(currentFile)
        return fileList
    
    def getFilesByUploadTicket(self, ticketId):
        sql = "SELECT * FROM file WHERE file_upload_ticket_id=%s"
        sql_args = [ticketId,]
        results = self.execute(sql, sql_args)
        fileList = []
        for fileR in results:
            currentFile = File(fileR['file_name'], fileR['file_type'], fileR['file_notes'], fileR['file_size'], fileR['file_uploaded_datetime'], fileR['file_owner_id'], fileR['file_expiration_datetime'], fileR['file_passed_avscan'], fileR['file_encryption_key'], fileR['file_id'], fileR['file_status'], fileR['file_location'], fileR['file_notify_on_download'], fileR['file_upload_ticket_id'])
            fileList.append(currentFile)
        return fileList
        
    def updateFile (self, flFile):
        sql = "UPDATE file SET file_name=%s, file_type=%s, file_notes=%s, file_size=%s, file_uploaded_datetime=%s, file_owner_id=%s, file_expiration_datetime=%s, file_passed_avscan=%s, file_encryption_key=%s, file_status=%s, file_location=%s, file_notify_on_download=%s, file_upload_ticket_id=%s WHERE file_id=%s"
        sql_args = [flFile.fileName, flFile.fileType, flFile.fileNotes, flFile.fileSizeBytes, flFile.fileUploadedDatetime, flFile.fileOwnerId, flFile.fileExpirationDatetime, flFile.filePassedAvScan, flFile.fileEncryptionKey, flFile.fileStatus, flFile.fileLocation, flFile.fileNotifyOnDownload, flFile.fileUploadTicketId, flFile.fileId]
        self.execute(sql, sql_args)
        return True

    def deleteFile (self, fileId):
        sql = "DELETE FROM file WHERE file_id=%s"
        sql_args = [fileId]
        self.execute(sql, sql_args)
        return True
#Groups
    def createGroup (self, newGroup):
        sql = "INSERT INTO groups (group_name, group_scope, group_owner_id) VALUES (%s, %s, %s)"
        sql_args = [newGroup.groupName, newGroup.groupScope, newGroup.ownerId]
        results, groupId = self.execute(sql, sql_args, True)
        for groupMember in newGroup.groupMembers:
            sql = "INSERT INTO group_membership VALUES(%s, %s)"
            sql_args = [groupId, groupMember.userId]
            self.execute(sql, sql_args)
        return groupId

    def getGroup (self, groupId):
        sql = "SELECT * FROM groups WHERE group_id=%s"
        sql_args = [groupId,]
        results = self.execute(sql,sql_args)
        currentGroup = None
        if results is not None and len(results)>0:
            groupR = results[0]
            sql = "SELECT * FROM group_membership WHERE group_membership_group_id=%s"
            memberResults = self.execute(sql,sql_args)
            groupMembers = []
            for memberRow in memberResults:
                groupMember = self.getUser(memberRow['group_membership_user_id'])
                if groupMember is None:
                    groupMember = User(None,None, None, None, None, None, memberRow['group_membership_user_id'])
                groupMembers.append(groupMember)
            currentGroup = Group(groupR['group_scope'], groupR['group_owner_id'], groupR['group_name'], groupMembers, groupR['group_id'])
        return currentGroup

    def getGroupsByUserId(self, userId):
        sql = "SELECT group_id FROM groups WHERE group_owner_id=%s"
        sql_args = [userId,]
        groupRows = self.execute(sql, sql_args)
        groupList = []
        for groupRow in groupRows:
            group = self.getGroup(groupRow['group_id']) #We do this because we already have code to populate group members in getGroup
            groupList.append(group)
        return groupList
        
    def updateGroup(self, group):
        #clear group membership
        sql = "DELETE FROM group_membership WHERE group_membership_group_id=%s"
        sql_args = [group.groupId]
        self.execute(sql, sql_args)
        #Now add the correct members back in
        sql = "INSERT INTO group_membership (group_membership_group_id, group_membership_user_id) VALUES(%s, %s)"
        for groupMember in group.groupMembers:
            sql_args=[group.groupId, groupMember.userId]
            self.execute(sql, sql_args)
        #Update group name and scope
        sql = "UPDATE groups SET group_name=%s, group_scope=%s WHERE group_id=%s"
        sql_args = [group.groupName, group.groupScope, group.groupId]
        self.execute(sql, sql_args)
        return True

    def deleteGroup (self, groupId):
        sql = "DELETE FROM groups WHERE group_id=%s"
        sql_args = [groupId]
        self.execute(sql, sql_args)
        return True
        
    def removeUserFromGroup(self, userId, groupId):
        sql = "DELETE FROM group_membership WHERE group_membership_user_id=%s AND group_membership_group_id=%s"
        sql_args = [userId, groupId]
        self.execute(sql, sql_args)
        return True
        
    def addUserToGroup(self, userId, groupId):
        sql = "INSERT INTO group_membership VALUES (%s, %s)"
        sql_args = [groupId, userId]
        try:
            self.execute(sql, sql_args)
        except MySQLdb.IntegrityError, ie:
            pass 
        except Exception, e:
            raise e
        return True

#Permissions
    def createPermission (self, permission):
        sql = "INSERT INTO permission VALUES (%s, %s)"
        sql_args = [permission.permissionId, permission.permissionName]
        try:
            self.execute(sql, sql_args)
        except MySQLdb.IntegrityError, ie:
            pass # basically, if the permission already exists, just ignore. TODO maybe update the name instead?
        return True

    def getPermission (self, permissionId):
        sql = "SELECT * FROM permission WHERE permission_id=%s"
        sql_args = [permissionId]
        results = self.execute(sql,sql_args)
        currentPermission = None
        for row in results:
            currentPermission = Permission(row['permission_id'], row['permission_name'])
        return currentPermission
    
    def getAllPermissions(self):
        sql = "SELECT * FROM permission"
        permissions = []
        results = self.execute(sql, None)
        for row in results:
            permissions.append(Permission(row['permission_id'], row['permission_name']))
        return permissions
    
    def getPermissionsByUser(self, userId): #returns a tuple -> userPermissions, groupPermissions
        sql = "SELECT * FROM user_permission, permission WHERE user_permission_user_id=%s AND user_permission_permission_id = permission_id"
        sql_args = [userId]
        userPermissionsList = []
        groupPermissionsList = []
        results = self.execute(sql, sql_args)
        for row in results:
            userPermissionsList.append(Permission(row['user_permission_permission_id'], row['permission_name'], "user"))
        sql = "SELECT * FROM group_permission, group_membership, groups WHERE group_permission_group_id = group_membership_group_id AND groups.group_id = group_membership_group_id AND group_membership_user_id=%s"
        results = self.execute(sql, sql_args)
        for row in results:
            permission = self.getPermission(row['group_permission_permission_id'])
            permission.inheritedFrom = row['group_name']
            groupPermissionsList.append(permission)
        return userPermissionsList, groupPermissionsList

    def updatePermission (self, permission):
        sql = "UPDATE permission SET permission_name=%s WHERE permission_id=%s"
        sql_args = [permission.permissionName, permission.permissionId]
        self.execute(sql, sql_args)
        return True

    def deletePermission (self, permissionId):
        sql = "DELETE FROM permission WHERE permission_id=%s"
        sql_args = [permissionId]
        self.execute(sql, sql_args)
        return True
    
    def grantUserPermission(self, userId, permissionId):
        sql = "INSERT INTO user_permission (user_permission_permission_id, user_permission_user_id) VALUES(%s, %s)"
        sql_args = [permissionId, userId]
        self.execute(sql, sql_args)
        
    def revokeUserPermission(self, userId, permissionId):
        sql = "DELETE FROM user_permission WHERE user_permission_permission_id = %s AND user_permission_user_id=%s"
        sql_args = [permissionId, userId]
        self.execute(sql, sql_args)
        
    def grantGroupPermission(self, groupId, permissionId):
        sql = "INSERT INTO group_permission (group_permission_permission_id, group_permission_group_id) VALUES(%s, %s)"
        sql_args = [permissionId, userId]
        self.execute(sql, sql_args)
    
    def revokeGroupPermission(self, groupId, permissionId):
        sql = "DELETE FROM group_permission WHERE group_permission_permission_id = %s AND group_permission_permission_id=%s"
        sql_args = [permissionId, groupId]
        self.execute(sql, sql_args)

#Private Shares
    def createPrivateShare(self, privateShare):
        sql = "INSERT INTO private_share VALUES (%s, %s)"
        sql_args = [privateShare.fileId, privateShare.targetId]
        #The reason this doesn't return an ID is because it requires and extra query and is not presently necessary in any context
        try:
            self.execute(sql, sql_args)
        except MySQLdb.IntegrityError, ie:
            pass
        return True

    def getPrivateSharesByOwner(self, ownerId, dictionary=False):
        files = self.getFilesByOwner(ownerId)
        sql = "SELECT * FROM private_share, file WHERE private_share_file_id=%s AND private_share_file_id=file_id AND file_owner_id=%s"
        if dictionary:
            shareDictionary = {}
            for flFile in files:
                shareDictionary[flFile.fileId] = []
                sql_args = [flFile.fileId,ownerId]
                results = self.execute(sql, sql_args)
                for row in results:
                    shareDictionary[flFile.fileId].append(row['private_share_target_id'])
            return shareDictionary
        else:
            privateShareList = []
            for flFile in files:
                sql_args = [flFile.fileId,ownerId]
                shares = []
                results = self.execute(sql, sql_args)
                for prShR in results:
                    privateShare = PrivateShare(prShR['private_share_file_id'], ownerId, prShR['private_share_target_id'])
                    shares.append(privateShare)
                privateShareList.extend(shares)
            return privateShareList

    def deletePrivateShare(self, fileId, targetId):
        sql = "DELETE FROM private_share WHERE private_share_file_id=%s AND private_share_target_id=%s"
        sql_args = [fileId, targetId]
        self.execute(sql, sql_args)
        return True
        
    def hidePrivateShare(self, fileId, targetId):
        sql = "INSERT INTO hidden_share VALUES (%s,%s)"
        sql_args = [targetId, fileId]
        try:
            self.execute(sql, sql_args)
        except MySQLdb.IntegrityError, ie:
            raise FLError(False, ["This share is already hidden"])
        return True
        
    def unhideAllPrivateShares(self, targetId):
        sql = "DELETE FROM hidden_share WHERE hidden_share_target_id=%s"
        sql_args = [targetId]
        self.execute(sql, sql_args)
        return True
    
    def unhideByFileId(self, fileId):
        sql = "DELETE FROM hidden_share WHERE hidden_share_file_id=%s"
        sql_args = [fileId]
        self.execute(sql, sql_args)
        return True
    
    def isShareHidden(self, fileId, targetId):
        sql = "SELECT * FROM hidden_share WHERE hidden_share_target_id=%s AND hidden_share_file_id=%s"
        sql_args = [targetId, fileId]
        results = self.execute(sql, sql_args)
        if len(results) > 0:
            return True
        return False
        
#Private Group Shares
    def createPrivateGroupShare(self, privateGroupShare):
        sql = "INSERT INTO private_group_share VALUES (%s, %s)"
        sql_args = [privateGroupShare.fileId, privateGroupShare.targetId]
        #The reason this doesn't return an ID is because it requires an extra query and is not presently necessary in any context
        try:
            self.execute(sql, sql_args)
        except MySQLdb.IntegrityError, ie:
            pass
        return True

    def getPrivateGroupSharesByOwner(self, ownerId, dictionary=False):
        files = self.getFilesByOwner(ownerId)
        sql = "SELECT * FROM private_group_share, groups WHERE private_group_share_file_id=%s AND private_group_share_target_id=group_id"
        if dictionary:
            groupShareDictionary = {}
            for flFile in files:
                groupShareDictionary[flFile.fileId] = []
                sql_args = [flFile.fileId,]
                results = self.execute(sql, sql_args)
                for row in results:
                    groupShareDictionary[flFile.fileId].append(row['private_group_share_target_id'])
            return groupShareDictionary
        else:
            privateGroupShareList = []
            for flFile in files:
                sql_args = [flFile.fileId,]
                shares = []
                results = self.execute(sql, sql_args)
                for prShR in results:
                    privateShare = PrivateGroupShare(prShR['private_group_share_file_id'], ownerId, prShR['private_group_share_target_id'])
                    privateShare.targetName = prShR['group_name']
                    shares.append(privateShare)
                privateGroupShareList.extend(shares)
            return privateGroupShareList

    def deletePrivateGroupShare (self, fileId, targetId):
        sql = "DELETE FROM private_group_share WHERE private_group_share_file_id=%s AND private_group_share_target_id=%s"
        sql_args = [fileId, targetId]
        self.execute(sql, sql_args)
        return True
    

#Private Attribute Shares
    def createAttribute(self, attribute):
        sql = "INSERT INTO attribute VALUES(%s, %s)"
        sql_args = [attribute.attributeId, attribute.attributeName]
        try:
            self.execute(sql, sql_args)
        except MySQLdb.IntegrityError, ie:
            raise FLError(False, ["An attribute with this ID already exists"])
        
    def deleteAttribute(self, attributeId):
        sql = "DELETE FROM attribute WHERE attribute_id = %s"
        sql_args = [attributeId,]
        self.execute(sql, sql_args)
    
    def updateAttribute(self, attribute):
        sql = "UPDATE attribute SET attribute_name = %s WHERE attribute_id =%s"
        sql_args = [attribute.attributeName, attribute.attributeId]
        self.execute(sql, sql_args)
        
    def getAttribute(self, attributeId):
        sql = "SELECT * FROM attribute WHERE attribute_id = %s"
        sql_args = [attributeId,]
        results = self.execute(sql, sql_args)
        attr = None
        for row in results:
            attr = Attribute(row['attribute_id'], row['attribute_name'])
        return attr
     
    def getAllAttributes(self):
        sql = "SELECT * FROM attribute"
        sql_args = None
        results = self.execute(sql, sql_args)
        attributes = []
        for row in results:
            attr = Attribute(row['attribute_id'], row['attribute_name'])
            attributes.append(attr)
        return attributes
    
    def createPrivateAttributeShare(self, privateAttributeShare):
        sql = "INSERT INTO private_attribute_share (private_attribute_share_file_id, private_attribute_share_attribute_id) VALUES (%s, %s)"
        sql_args = [privateAttributeShare.fileId, privateAttributeShare.attribute]
        #The reason this doesn't return an ID is because it requires and extra query and is not presently necessary in any context
        try:
            self.execute(sql, sql_args)
        except MySQLdb.IntegrityError, ie:
            pass #The share already exists, ignore
        except Exception, e:
            raise e
        return True
    
    def getSharedFilesByAttribute(self, attributeId):
        sql = "SELECT * FROM private_attribute_share, file WHERE private_attribute_share_attribute_id=%s AND file.file_id = private_attribute_share_file_id"
        sql_args = [attributeId,]
        fileList = []
        results = self.execute(sql, sql_args)
        for row in results:
            fileList.append(File(row['file_name'], row['file_type'], row['file_notes'], row['file_size'], row['file_uploaded_datetime'], row['file_owner_id'], row['file_expiration_datetime'], row['file_passed_avscan'], row['file_encryption_key'], row['file_id'], row['file_status'], row['file_location'], row['file_notify_on_download'], row['file_upload_ticket_id']))
        return fileList
        
    def deletePrivateAttributeShare (self, fileId, attributeId):
        sql = "DELETE FROM private_attribute_share WHERE private_attribute_share_file_id=%s and private_attribute_share_attribute_id=%s"
        sql_args = [fileId, attributeId]
        self.execute(sql, sql_args)
        return True
    
    def deletePrivateAttributeSharesByAttributeId(self, attributeId):
        sql = "DELETE FROM private_attribute_share WHERE private_attribute_share_attribute_id=%s"
        sql_args = [attributeId]
        self.execute(sql, sql_args)
        return True
        
#Public Shares
    def createPublicShare (self, publicShare):
        try:
            sql = "INSERT INTO public_share (public_share_file_id, public_share_expiration, public_share_password_hash, public_share_id, public_share_type)  VALUES(%s, %s, %s, %s, %s)"
            publicShare.shareId = publicShare.generateShareId()
            sql_args = [publicShare.fileId, publicShare.expirationDateTime, publicShare.passwordHash, publicShare.shareId, publicShare.shareType]
            self.execute(sql, sql_args)
        except MySQLdb.IntegrityError, ie:
            idList = []
            sql2 = "SELECT public_share_id FROM public_share"
            idRows = self.execute(sql2, None)
            for idRow in idRows:
                idList.append(idRow['public_share_id'])
            while publicShare.shareId in idList:
                publicShare.shareId = publicShare.generateShareId()
            self.execute(sql, sql_args)
        return publicShare.shareId

    def getPublicShare (self, publicShareId):
        sql = "SELECT * FROM public_share WHERE public_share_id=%s"
        sql_args = [publicShareId,]
        results = self.execute(sql, sql_args)
        currentPubShare = None
        for row in results:
            flFile = self.getFile(row['public_share_file_id'])
            currentPubShare = PublicShare(row['public_share_file_id'], flFile.fileOwnerId, row['public_share_expiration'], row['public_share_password_hash'], row['public_share_type'], row['public_share_id'])
        return currentPubShare
    
    def getPublicShareByFileId(self, fileId):
        sql = "SELECT * FROM public_share WHERE public_share_file_id=%s"
        sql_args = [fileId,]
        results = self.execute(sql, sql_args)
        currentPubShare = None
        for row in results:
            flFile = self.getFile(row['public_share_file_id'])
            currentPubShare = PublicShare(row['public_share_file_id'], flFile.fileOwnerId, row['public_share_expiration'], row['public_share_password_hash'], row['public_share_type'], row['public_share_id'])
        return currentPubShare
        
    def getExpiredPublicShares(self):
        sql = "SELECT * FROM public_share WHERE public_share_expiration < now()"
        sql_args = None
        results = self.execute(sql, sql_args)
        expiredPublicShares = []
        for row in results:
            flFile = self.getFile(row['public_share_file_id'])
            ownerId = None
            if flFile is not None:
                ownerId = flFile.fileOwnerId
            currentPubShare = PublicShare(row['public_share_file_id'], ownerId, row['public_share_expiration'], row['public_share_password_hash'], row['public_share_type'], row['public_share_id'])
            expiredPublicShares.append(currentPubShare)
        return expiredPublicShares
        
    def getPublicShare(self, shareId):
        sql = "SELECT * FROM public_share, file WHERE public_share_file_id=file_id AND public_share_id=%s"
        sql_args = [shareId,]
        results = self.execute(sql, sql_args)
        publicShare = None
        for row in results:
            flFile = self.getFile(row['public_share_file_id'])
            publicShare = PublicShare(row['public_share_file_id'], flFile.fileOwnerId, row['public_share_expiration'], row['public_share_password_hash'], row['public_share_type'], row['public_share_id'])
        return publicShare
        
    def getPublicSharesByOwner(self, ownerId):
        sql = "SELECT * FROM public_share, file WHERE public_share_file_id=file_id AND file_owner_id=%s"
        sql_args = [ownerId,]
        results = self.execute(sql, sql_args)
        publicShares = []
        for pbShR in results:
            publicShare = PublicShare(pbShR['public_share_file_id'], ownerId, pbShR['public_share_expiration'], pbShR['public_share_password_hash'], pbShR['public_share_type'], pbShR['public_share_id'])
            publicShares.append(publicShare)
        return publicShares
        
    def updatePublicShare (self, publicShare):
        sql = "UPDATE public_share SET public_share_file_id=%s, public_share_expiration=%s, public_share_password_hash=%s WHERE public_share_id=%s"
        sql_args = [publicShare.fileId, publicShare.expirationDatetime, publicShare.passwordHash, publicShare.shareId]
        self.execute(sql, sql_args)
        return True

    def deletePublicShare (self, publicShareId):
        sql = "DELETE FROM public_share WHERE public_share_id=%s"
        sql_args = [publicShareId]
        self.execute(sql, sql_args)
        return True

#User functions
    def createUser (self, user, password=None):
        sql = "INSERT INTO user (user_first_name, user_last_name, user_id, user_quota, user_last_login_datetime, user_tos_accept_datetime, user_email) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        sql_args = [user.userFirstName, user.userLastName, user.userId, user.userQuota, user.userLastLogin, user.userTosAcceptDatetime, user.userEmail]
        try:
            self.execute(sql, sql_args)
        except MySQLdb.IntegrityError, ie:
            logging.warning("User already exists. No need to create.")
        if password is not None:
            self.updateUser(user, password)

    def getUser (self, userId):
        sql = "SELECT * FROM user WHERE user_id=%s"
        sql_args = [userId]
        results = self.execute(sql, sql_args)
        currentUser = None
        for row in results:
            currentUser = User(row['user_first_name'].title(), row['user_last_name'].title(), row['user_email'], row['user_quota'], row['user_last_login_datetime'], row['user_tos_accept_datetime'], row['user_id'])
            rSql = "SELECT * FROM permission WHERE permission_id=%s"
            sql_args = ["(role)%s" % currentUser.userId]
            rolesResults = self.execute(rSql, sql_args)
            for roleRow in rolesResults:
                currentUser.isRole = True
                break
        return currentUser
    
    def getExpiredUsers(self, expirationDays):
        sql = "SELECT * FROM user WHERE user_last_login_datetime < NOW() - INTERVAL %s DAY"
        results = self.execute(sql, expirationDays)
        expiredUsers = []
        for row in results:
            if self.checkUserPrivilege(row['user_id'], "expiration_exempt") == False and self.checkUserPrivilege(row['user_id'], "admin") == False: #Don't purge users who are expiration exempt - they may have files they distribute
                expiredUsers.append(User(row['user_first_name'].title(), row['user_last_name'].title(), row['user_email'], row['user_quota'], row['user_last_login_datetime'], row['user_tos_accept_datetime'], row['user_id']))
        return expiredUsers
        
    def updateUser (self, user, password=None):
        passwordHash = None
        if password is not None:
            m = md5()
            m.update(password)
            passwordHash = m.hexdigest()
        sql = "UPDATE user SET user_quota=%s, user_email=%s, user_first_name=%s, user_last_name=%s, user_last_login_datetime=%s, user_tos_accept_datetime=%s"
        sql_args = [user.userQuota, user.userEmail, user.userFirstName, user.userLastName, user.userLastLogin, user.userTosAcceptDatetime]
        if passwordHash is not None:
            sql += ", user_password_hash=%s"
            sql_args.append(passwordHash)
        sql+=" WHERE user_id=%s"
        sql_args.append(user.userId)
        self.execute(sql, sql_args)
        return True

    def deleteUser (self, userId):
        sql_args=[userId]
        sql = "DELETE FROM upload_ticket WHERE upload_ticket_owner_id=%s"
        self.execute(sql, sql_args)
        sql = "SELECT file_id FROM file WHERE file_owner_id=%s"
        results = self.execute(sql, sql_args)
        #For each file that the user owns, delete associated shares
        for row in results:
            fileId = row['file_id']
            sql = "DELETE FROM public_share WHERE public_share_file_id=%s"
            self.execute(sql, [fileId,])
            sql = "DELETE FROM private_share WHERE private_share_file_id=%s"
            self.execute(sql, [fileId,])
            sql = "DELETE FROM private_group_share WHERE private_group_share_file_id=%s"
            self.execute(sql, [fileId,])
        sql = "DELETE FROM file WHERE file_owner_id = %s"
        self.execute(sql, [userId,])
        sql = "SELECT group_id FROM groups WHERE group_owner_id=%s"
        #The group purging intentionally allows this user to remain a member of other users' groups
        results = self.execute(sql, sql_args)
        for row in results:
            groupId = row['group_id']
            sql = "DELETE FROM groups WHERE group_id=%s"
            sql_args=[groupId,]
            self.execute(sql, sql_args)
            sql = "DELETE FROM group_membership WHERE group_membership_group_id=%s"
            self.execute(sql, sql_args) 
        #Let Filelocker.py handle the file deletion since that will need secure delete
        #Delete roles associated with the user
        sql = "DELETE FROM permission WHERE permission_id=%s"
        sql_args=["(role)%s" % userId]
        self.execute(sql, sql_args)
        sql = "DELETE FROM user_permission WHERE user_permission_permission_id=%s"
        self.execute(sql, sql_args)
        sql = "DELETE FROM group_permission WHERE group_permission_permission_id=%s"
        self.execute(sql, sql_args)
        #Delete any other permissions granted to the user
        sql_args = [userId]
        sql = "DELETE FROM user_permission WHERE user_permission_user_id=%s"
        self.execute(sql, sql_args)
        #Delete the actual user account
        sql = "DELETE FROM user WHERE user_id=%s"
        self.execute(sql, sql_args)
        return True
    
    def getAllUsers(self, start=None, length=None):
        sql = "SELECT * FROM user ORDER BY user_id"
        sql_args = None
        if start is not None and length is not None:
            sql += " LIMIT %s, %s"
            sql_args = [start, length]
        psql = "SELECT * FROM permission"
        qsql = "SELECT sum(file_size) as quotausage, file_owner_id FROM file GROUP BY file_owner_id"
        perms = []
        quotas = {}
        results = self.execute(psql, None)
        for row in results:
            perms.append(row['permission_id'])
        results = self.execute(qsql, None)
        for row in results:
            quotas[row['file_owner_id']] = row['quotausage']
        results = self.execute(sql, sql_args)
        users = []
        for row in results:
            quotaUsageMB = 0
            if quotas.has_key(row['user_id']):
                quotaUsageMB = float(quotas[row['user_id']]) / 1024 / 1024
            newUser = User(row['user_first_name'], row['user_last_name'], row['user_email'], row['user_quota'], row['user_last_login_datetime'], row['user_tos_accept_datetime'], row['user_id'], quotaUsageMB)
            if "(role)%s" % row['user_id'] in perms:
                newUser.isRole = True
            users.append(newUser)
        return users

    def getUserCount(self):
        sql = "SELECT COUNT(*) AS total_user_count FROM user"
        results = self.execute(sql, None)
        for row in results:
            totalUserCount = row['total_user_count']
        return totalUserCount
        
    def getFileCount(self):
        sql = "SELECT COUNT(*) AS total_file_count FROM file"
        results = self.execute(sql, None)
        for row in results:
            totalFileCount = row['total_file_count']
        return totalFileCount
        
    def getMessageCount(self):
        sql = "SELECT COUNT(*) AS total_message_count FROM message"
        results = self.execute(sql, None)
        for row in results:
            totalMessageCount = row['total_message_count']
        return totalMessageCount
        
#CLI Key Management
    def verifyCLILogin(self, userId, hostIPv4, hostIPv6, CLIKey):
        logging.error("Verifying: user %s hostIpv4 %s hostIPv6 %s cliKey %s" % (userId, hostIPv4, hostIPv6, CLIKey))
        sql = "SELECT * FROM cli_key WHERE cli_key_user_id=%s AND cli_key_host_ipv4=%s AND cli_key_host_ipv6=%s AND cli_key_value=%s"
        sql1_args = [userId, "", "", CLIKey] #Try generic non-ip restricted CLI key first
        sql2_args = [userId, hostIPv4, hostIPv6, CLIKey] #If no results, try one that has to match the IP
        results = self.execute(sql, sql1_args)
        if(len(results) > 0):
            return True
        else:
            results = self.execute(sql, sql2_args)
            if len(results) >0:
                return True
            else:
                return False
        
    def createCLIKey(self, userId, hostIPv4, hostIPv6, CLIKey):
        sql = "SELECT * FROM cli_key WHERE cli_key_user_id=%s AND cli_key_host_ipv4=%s AND cli_key_host_ipv6=%s"
        sql_args = [userId, hostIPv4, hostIPv6]
        results = self.execute(sql, sql_args)
        if (len(results) > 0):
            exists = True
        else:
            exists = False
        sql = "INSERT INTO cli_key (cli_key_user_id, cli_key_host_ipv4, cli_key_host_ipv6, cli_key_value) VALUES (%s, %s, %s, %s)"
        sql_args = [userId, hostIPv4, hostIPv6, CLIKey]
        if not exists:
            self.execute(sql, sql_args)
        else: #This user/host combination exists. Delete and regenerate.
            self.deleteCLIKey(userId, hostIPv4, hostIPv6)
            self.createCLIKey(userId, hostIPv4, hostIPv6, CLIKey)
    
    def getCLIKey(self, userId, hostIPv4, hostIPv6):
        sql = "SELECT * FROM cli_key WHERE cli_key_user_id=%s AND cli_key_host_ipv4=%s AND cli_key_host_ipv6=%s"
        sql_args = [userId, hostIPv4, hostIPv6]
        results = self.execute(sql, sql_args)
        cliKey = None
        for row in results:
            cliKey = row['cli_key_value']
        return cliKey
            
    def getCLIKeyList(self, userId):
        sql = "SELECT * FROM cli_key WHERE cli_key_user_id=%s"
        sql_args = [userId]
        CLIKeys = []
        results = self.execute(sql, sql_args)
        for row in results:
            newKey = CLIKey(row['cli_key_host_ipv4'], row['cli_key_host_ipv6'], row['cli_key_value'])
            CLIKeys.append(newKey)
        return CLIKeys
            
    def deleteCLIKey(self, userId, hostIPv4, hostIPv6):
        sql = "DELETE FROM cli_key WHERE cli_key_user_id=%s and cli_key_host_ipv4=%s and cli_key_host_ipv6=%s"
        sql_args = [userId, hostIPv4, hostIPv6]
        self.execute(sql, sql_args)

#Upload Tickets
    def createUploadTicket(self, newTicket):
        try:
            sql = "INSERT INTO upload_ticket (upload_ticket_owner_id, upload_ticket_max_size, upload_ticket_expiration, upload_ticket_password_hash, upload_ticket_scan_file, upload_ticket_type, upload_ticket_id) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            newTicket.ticketId = newTicket.generateTicketId()
            sql_args = [newTicket.ownerId, newTicket.maxFileSize, newTicket.expiration, newTicket.passwordHash, newTicket.scanFile, newTicket.ticketType, newTicket.ticketId]
            self.execute(sql, sql_args)
        except MySQLdb.IntegrityError, ie:
            idList = []
            sql2 = "SELECT upload_ticket_id FROM upload_ticket"
            idRows = self.execute(sql2, None)
            for idRow in idRows:
                idList.append(idRow['upload_ticket_id'])
            while newTicket.ticketId in idList:
                newTicket.ticketId = newTicket.generateTicketId()
            self.execute(sql, sql_args)
        return newTicket.ticketId
        
    def getUploadTicket(self, ticketId):
        sql = "SELECT * FROM upload_ticket WHERE upload_ticket_id=%s" 
        sql_args = [ticketId,]
        results = self.execute(sql, sql_args)
        uploadTicket = None
        for row in results:
            uploadTicket = UploadTicket(row['upload_ticket_owner_id'], row['upload_ticket_max_size'], row['upload_ticket_expiration'], row['upload_ticket_password_hash'], row['upload_ticket_scan_file'], row['upload_ticket_type'], row['upload_ticket_id'])
        return uploadTicket
        
    def getExpiredUploadTickets(self):
        sql = "SELECT * FROM upload_ticket WHERE upload_ticket_expiration < now()"
        sql_args = None
        results = self.execute(sql, sql_args)
        expiredUploadTickets = []
        for row in results:
            uploadTicket = UploadTicket(row['upload_ticket_owner_id'], row['upload_ticket_max_size'], row['upload_ticket_expiration'], row['upload_ticket_password_hash'], row['upload_ticket_scan_file'], row['upload_ticket_type'], row['upload_ticket_id'])
            expiredUploadTickets.append(uploadTicket)
        return expiredUploadTickets
        
    def getUploadTicketsByUser(self, userId):
        sql = "SELECT * FROM upload_ticket WHERE upload_ticket_owner_id=%s" 
        sql_args = [userId,]
        ticketRows = self.execute(sql, sql_args)
        tickets = []
        for ticketRow in ticketRows:
            uploadTicket = UploadTicket(ticketRow['upload_ticket_owner_id'], ticketRow['upload_ticket_max_size'], ticketRow['upload_ticket_expiration'], ticketRow['upload_ticket_password_hash'], ticketRow['upload_ticket_scan_file'], ticketRow['upload_ticket_type'], ticketRow['upload_ticket_id'])
            tickets.append(uploadTicket)
        return tickets
        
    def deleteUploadTicket(self, ticketId):
        sql = "DELETE FROM upload_ticket WHERE upload_ticket_id = %s"
        sql_args = [ticketId,]
        self.execute(sql, sql_args)
        return True
        
    #CRUD functions for messaging
    def createMessage(self, message):
        sql = "INSERT INTO message (message_subject, message_create_datetime, message_owner_id, message_expiration_datetime, message_encryption_key) VALUES(%s, %s, %s, %s, %s)"
        sql_args = [message.messageSubject, message.messageCreateDatetime, message.messageOwnerId, message.messageExpirationDatetime, message.messageEncryptionKey]
        results, messageId = self.execute(sql, sql_args, True)
        return messageId
        
    def getNewMessageCount(self, userId):
        sql = "SELECT COUNT(*) AS new_message_count FROM message_recipient WHERE message_recipient_viewed_datetime IS NULL AND message_recipient_user_id = %s"
        sql_args = [userId]
        results = self.execute(sql, sql_args)
        for row in results:
            newMessageCount = row['new_message_count']
        return newMessageCount
    
    def getMessage(self, messageId):
        sql = "SELECT * FROM message WHERE message_id = %s" 
        sql_args = [messageId]
        results = self.execute(sql, sql_args)
        message = None
        for row in results:
            message = Message(row['message_subject'], None, row['message_create_datetime'], row['message_owner_id'], row['message_expiration_datetime'], None, row['message_encryption_key'], row['message_id'])
        return message
        
    def getExpiredMessages(self):
        sql = "SELECT * FROM message WHERE message_expiration_datetime < now()"
        sql_args = None
        results = self.execute(sql, sql_args)
        expiredMessages = []
        for row in results:
            eMsg = Message(row['message_subject'], None, row['message_create_datetime'], row['message_owner_id'], row['message_expiration_datetime'], None, row['message_encryption_key'], row['message_id'])
            expiredMessages.append(eMsg)
        return expiredMessages
        
    def getReceivedMessages(self, recipientId, messageIdList = None):
        sql = "SELECT * FROM message, message_recipient WHERE message_recipient_user_id=%s AND message_recipient_message_id=message_id ORDER BY message_create_datetime"
        sql_args = [recipientId]
        results = self.execute(sql, sql_args)
        receivedMessages = []
        for row in results:
            rMsg = Message(row['message_subject'], None, row['message_create_datetime'], row['message_owner_id'], row['message_expiration_datetime'], None, row['message_encryption_key'], row['message_id'])
            rMsg.messageViewedDatetime = row['message_recipient_viewed_datetime']
            receivedMessages.append(rMsg)
        return receivedMessages
        
    def getSentMessages(self, ownerId, messageIdList = None):
        sql = "SELECT * FROM message, message_recipient WHERE message_owner_id=%s AND message_recipient_message_id=message_id ORDER BY message_create_datetime"
        sql_args = [ownerId]
        results = self.execute(sql, sql_args)
        sentMessages = []
        for row in results:
            sMsg = Message(row['message_subject'], None, row['message_create_datetime'], row['message_owner_id'], row['message_expiration_datetime'], None, row['message_encryption_key'], row['message_id'])
            sentMessages.append(sMsg)
        return sentMessages
        
    def isMessageRead(self, messageId, userId):
        sql = "SELECT message_recipient_viewed_datetime FROM message_recipient WHERE message_recipient_message_id=%s AND message_recipient_user_id=%s"
        sql_args = [messageId, userId]
        results = self.execute(sql, sql_args)
        if results[0]['message_recipient_viewed_datetime'] is not None:
            return True
        return False
    
    def getMessageRecipients(self, messageId):
        sql = "SELECT * FROM message_recipient WHERE message_recipient_message_id=%s"
        sql_args = [messageId]
        recipients = []
        results = self.execute(sql, sql_args)
        for row in results:
            recipients.append(row['message_recipient_user_id'])
        return recipients
    
    def deleteMessage(self, messageId):
        sql1 = "DELETE FROM message WHERE message_id = %s"
        sql2 = "DELETE FROM message_recipient WHERE message_recipient_message_id = %s"
        sql_args = [messageId]
        self.execute(sql1, sql_args)
        self.execute(sql2, sql_args)
        return True
        
    def createMessageRecipient(self, messageId, recipientId, viewedDatetime):
        sql = "INSERT INTO message_recipient VALUES (%s, %s, %s)" 
        sql_args = [messageId, recipientId, viewedDatetime]
        try:
            self.execute(sql, sql_args)
        except MySQLdb.IntegrityError, ie:
            pass #They've already sent this user that message.
        return True
    
    def recipientReadMessage(self, messageId, recipientId, viewedDatetime):
        sql = "UPDATE message_recipient SET message_recipient_viewed_datetime = %s WHERE message_recipient_message_id = %s AND message_recipient_user_id=%s"
        sql_args = [viewedDatetime, messageId, recipientId]
        self.execute(sql, sql_args)
        return True
        
    def deleteMessageRecipient(self, messageId, recipientId):
        sql = "DELETE FROM message_recipient WHERE message_recipient_message_id = %s AND message_recipient_user_id = %s"
        sql_args = [messageId, recipientId]
        self.execute(sql, sql_args)
        return True
    
    #These are helper functions outside of the basic CRUD functions
    def removeSharesByFileId(self, fileId):
        sql = "DELETE FROM public_share WHERE public_share_file_id=%s"
        sql_args=[fileId,]
        self.execute(sql, sql_args)
        sql = "DELETE FROM private_share WHERE private_share_file_id=%s" 
        self.execute(sql, sql_args)
        sql = "DELETE FROM private_group_share WHERE private_group_share_file_id=%s" 
        self.execute(sql, sql_args)
        return True
        
    def checkUserPrivilege(self, userId, permissionId):
        """ Checks if a user has a permission_id
        
        This function should search through all permissions a user has, be it
        from group membership or individual permissions"""
        hasPermission = False
        sql = """SELECT count(up.user_permission_user_id) as hasPermission
                FROM user_permission up 
                WHERE (up.user_permission_user_id = %s 
                AND up.user_permission_permission_id = %s) 
                OR up.user_permission_user_id IN (SELECT group_membership_user_id FROM group_permission g, group_membership m 
                WHERE g.group_permission_group_id = m.group_membership_group_id 
                AND m.group_membership_user_id = %s 
                AND g.group_permission_permission_id = %s)"""
        sql_args = [userId, permissionId, userId, permissionId]
        results = self.execute(sql, sql_args)
        
        if int(results[0]['hasPermission']) > 0:
            hasPermission = True
        return hasPermission
        
    def getCurrentQuotaUsage(self, userId):
        sql = "SELECT sum(file_size) as quotaUsage FROM file WHERE file_owner_id=%s"
        sql_args = [userId]
        results = self.execute(sql, sql_args) 
        currentUsageBytes = results[0]['quotaUsage']
        if currentUsageBytes is None:
            currentUsageBytes = 0
        return currentUsageBytes
    
    def getFilesSharedWithUser(self, userId):
        sql = "SELECT private_share_file_id FROM private_share WHERE private_share_target_id=%s"
        sql_args = [userId,]
        fileIds = []
        results = self.execute(sql, sql_args)
        for row in results:
            fileIds.append(row['private_share_file_id'])
        sql = "SELECT * FROM private_group_share, group_membership WHERE group_membership_user_id = %s AND group_membership_group_id = private_group_share_target_id"
        results = self.execute(sql, sql_args)
        for row in results:
            if row['private_group_share_file_id'] not in fileIds:
                fileIds.append(row['private_group_share_file_id'])
        sharedFiles = []
        for fileId in fileIds:
            sharedFiles.append(self.getFile(fileId))
        return sharedFiles
        
    def queueForDeletion(self, filePath):
        sql = "INSERT INTO deletion_queue VALUES(%s)"
        sql_args = [filePath,]
        try:
            self.execute(sql, sql_args)
        except MySQLdb.IntegrityError, ie:
            pass 
        except Exception, e:
            raise e
    
    def deQueueForDeletion(self, filePath):
        sql = "DELETE FROM deletion_queue WHERE deletion_queue_file_path = %s"
        sql_args = [filePath,]
        self.execute(sql, sql_args)
    
    def getFilesQueuedForDeletion(self):
        sql = "SELECT * FROM deletion_queue"
        sql_args=None
        results = self.execute(sql, sql_args)
        filePaths = []
        for row in results:
            filePaths.append(row['deletion_queue_file_path'])
        return filePaths
    
    def logAction(self, actionLog):
        sql = "INSERT INTO audit_log (audit_log_initiator_user_id, audit_log_action, audit_log_action_affected_user_id, audit_log_message, audit_log_datetime) VALUES(%s, %s, %s, %s, %s)"
        sql_args = [actionLog.initiatorUserId, actionLog.action, actionLog.affectedUserId, actionLog.message, actionLog.actionDatetime]
        self.execute(sql, sql_args)
    
    def getAuditActions(self, userId):
        sql = "SELECT DISTINCT audit_log_action FROM audit_log WHERE audit_log_initiator_user_id=%s OR audit_log_action_affected_user_id=%s"
        sql_args = [userId,userId]
        actionList = []
        results = self.execute(sql, sql_args)
        for row in results:
            actionList.append(row['audit_log_action'])
        return actionList
    
    def getAuditLogs(self, userId=None, startDate=None, endDate=None, action=None):
        relevantLogs, sql_args = [], []
        sql = "SELECT * FROM audit_log"
        if userId is not None or startDate is not None or endDate is not None or action is not None:
            sql += " WHERE"
        if userId is not None:
            sql += " (audit_log_initiator_user_id=%s OR audit_log_action_affected_user_id=%s)"
            sql_args=[userId, userId]
        if startDate is not None:
            if userId is not None:
                sql += " AND"
            sql += " audit_log_datetime >= %s"
            sql_args.append(startDate)
        if endDate is not None:
            if userId is not None or startDate is not None:
                sql += " AND"
            sql += " audit_log_datetime <= %s"
            sql_args.append(endDate)
        if action is not None and action != "all":
            if userId is not None or startDate is not None or endDate is not None:
                sql += " AND"
            if action =="all_minus_login":
                sql += " audit_log_action <> %s"
                sql_args.append("Login")
            else:
                sql += " audit_log_action = %s"
                sql_args.append(action)
        sql += " ORDER BY audit_log_datetime"
        results = self.execute(sql, sql_args)
        if results is not None and len(results) > 0:
            for row in results:
                newLog = ActionLog(row['audit_log_initiator_user_id'], row['audit_log_action'], row['audit_log_action_affected_user_id'], row['audit_log_message'], row['audit_log_datetime'], row['audit_log_id'])
                relevantLogs.append(newLog)
        return relevantLogs
    
    def getDownloadStatistics(self, fileId, startDate=None, endDate=None):
        totalDownloadSql = "SELECT DATE(audit_log_datetime) AS 'day', count(*) AS 'Downloads' FROM audit_log WHERE audit_log_action = 'Download File' AND audit_log_message LIKE '%%[File ID: %s]'"
        uniqueDownloadSql = "SELECT audit_log_datetime AS 'day', count(*) AS 'Unique User Downloads' FROM (SELECT DISTINCT audit_log_initiator_user_id, DATE(audit_log_datetime) AS audit_log_datetime FROM audit_log WHERE audit_log_action = 'Download File' AND audit_log_message LIKE '%%[File ID: %s]') AS t1"
        fileIdInt = int(fileId)
        sql_args = [fileIdInt]
        if startDate is not None:
            totalDownloadSql += " AND audit_log_datetime >= %s"
            uniqueDownloadSql += " WHERE audit_log_datetime >= %s"
            sql_args.append(startDate)
        if endDate is not None:
            totalDownloadSql += " AND audit_log_datetime <= %s"
            if startDate is not None:
                uniqueDownloadSql += " AND"
            else:
                uniqueDownloadSql += " WHERE"
            uniqueDownloadSql += " audit_log_datetime <= %s"
            sql_args.append(endDate)
        totalDownloadSql +=" GROUP BY DATE(audit_log_datetime) ORDER BY audit_log_datetime"
        uniqueDownloadSql +=" GROUP BY DATE(audit_log_datetime) ORDER BY audit_log_datetime"
        results = self.execute(totalDownloadSql, sql_args)
        totalDownloadStats = []
        for row in results:
            stat = (str(row['day']), row['Downloads'])
            totalDownloadStats.append(stat)
        uniqueDownloadStats = []
        results = self.execute(uniqueDownloadSql, sql_args)
        for row in results:
            stat = (str(row['day']), row['Unique User Downloads'])
            uniqueDownloadStats.append(stat)
        return {"total":totalDownloadStats, "unique":uniqueDownloadStats}
        
    def getHourlyDownloadStatistics(self):
        sql = """SELECT hour, ROUND(hourly_total*100/ (
                SELECT COUNT(*) AS total_downloads
                FROM audit_log
                WHERE audit_log_action = "Download File"
                AND DATE(audit_log_datetime) >= CURDATE() - INTERVAL 30 DAY 
            )) AS percentage_of_total_downloads
            FROM (
                SELECT HOUR(audit_log_datetime) AS hour, COUNT(*) AS hourly_total
                FROM audit_log
                WHERE audit_log_action = "Download File"
                AND DATE(audit_log_datetime) >= CURDATE() - INTERVAL 30 DAY
                GROUP BY HOUR(audit_log_datetime)
            ) AS totals_by_hour
            GROUP BY hour
            ORDER BY hour"""
        statList = []
        results = self.execute(sql, [])
        for row in results:
            statList.append({"hour": str(row['hour']), "percentage_of_downloads": str(row['percentage_of_total_downloads'])})
        return statList
        
    def getHourlyUploadStatistics(self):
        sql = """SELECT hour, ROUND(hourly_total*100/ (
                SELECT COUNT(*) AS total_uploads
                FROM audit_log
                WHERE audit_log_action = "Check In File"
                AND DATE(audit_log_datetime) >= CURDATE() - INTERVAL 30 DAY 
            )) AS percentage_of_total_uploads
            FROM (
                SELECT HOUR(audit_log_datetime) AS hour, COUNT(*) AS hourly_total
                FROM audit_log
                WHERE audit_log_action = "Check In File"
                AND DATE(audit_log_datetime) >= CURDATE() - INTERVAL 30 DAY
                GROUP BY HOUR(audit_log_datetime)
            ) AS totals_by_hour
            GROUP BY hour
            ORDER BY hour"""
        statList = []
        results = self.execute(sql, [])
        for row in results:
            statList.append({"hour": str(row['hour']), "percentage_of_uploads": str(row['percentage_of_total_uploads'])})
        return statList
        
    def getDailyDownloadStatistics(self):
        sql = "SELECT MONTH(audit_log_datetime) AS month, DAY(audit_log_datetime) AS day, COUNT(*) AS daily_total FROM audit_log WHERE audit_log_action = 'Download File' AND DATE(audit_log_datetime) >= CURDATE() - INTERVAL 30 DAY GROUP BY DAY(audit_log_datetime) ORDER BY DAY(audit_log_datetime)"
        statList = []
        results = self.execute(sql, [])
        for row in results:
            statList.append({"date": "%s/%s" % (str(row['month']), str(row['day'])), "total": str(row['daily_total'])})
        return statList
        
    def getDailyUploadStatistics(self):
        sql = "SELECT MONTH(audit_log_datetime) AS month, DAY(audit_log_datetime) AS day, COUNT(*) AS daily_total FROM audit_log WHERE audit_log_action = 'Check In File' AND DATE(audit_log_datetime) >= CURDATE() - INTERVAL 30 DAY GROUP BY DAY(audit_log_datetime) ORDER BY DAY(audit_log_datetime)"
        statList = []
        results = self.execute(sql, [])
        for row in results:
            statList.append({"date": "%s/%s" % (str(row['month']), str(row['day'])), "total": str(row['daily_total'])})
        return statList
        
    def getMonthlyDownloadStatistics(self):
        sql = "SELECT MONTH(audit_log_datetime) AS month, COUNT(*) AS monthly_total FROM audit_log WHERE audit_log_action = 'Download File' AND DATE(audit_log_datetime) >= CURDATE() - INTERVAL 1 YEAR GROUP BY MONTH(audit_log_datetime) ORDER BY MONTH(audit_log_datetime)"
        statList = []
        results = self.execute(sql, [])
        for row in results:
            statList.append({"month": str(row['month']), "total": str(row['monthly_total'])})
        return statList
        
    def getMonthlyUploadStatistics(self):
        sql = "SELECT MONTH(audit_log_datetime) AS month, COUNT(*) AS monthly_total FROM audit_log WHERE audit_log_action = 'Check In File' AND DATE(audit_log_datetime) >= CURDATE() - INTERVAL 1 YEAR GROUP BY MONTH(audit_log_datetime) ORDER BY MONTH(audit_log_datetime)"
        statList = []
        results = self.execute(sql, [])
        for row in results:
            statList.append({"month": str(row['month']), "total": str(row['monthly_total'])})
        return statList
    
    def updateDB(self, FLVersion, dbSessions=False):
        #Get DB version
        dbUpdates = []
        DBVersion = self.getParameter("db_version")
        if DBVersion is None:
            DBVersion = "2.0"
        else:
            DBVersion = DBVersion.value
        majorRevision = int(DBVersion.split(".")[1])
        
        if dbSessions:
            dbUpdates.append("""
            CREATE TABLE IF NOT EXISTS `session` (
            `id` varchar(40) NOT NULL,
            `data` text DEFAULT NULL,
            `expiration_time` DATETIME DEFAULT NULL,
            PRIMARY KEY (`id`) ) ENGINE=InnoDB
            """)
        else:
            dbUpdates.append("""
            DROP TABLE IF EXISTS `session`
            """)

        dbUpdates.extend(["""
            DROP TABLE IF EXISTS tip
            """, """
            CREATE TABLE IF NOT EXISTS `hidden_share` (
            `hidden_share_target_id` varchar(30) NOT NULL,
            `hidden_share_file_id` mediumint(9) NOT NULL,
            PRIMARY KEY  (`hidden_share_target_id`,`hidden_share_file_id`)
            ) ""","""
            DROP TABLE IF EXISTS hidden
            """, """
            ALTER TABLE file MODIFY file_size BIGINT UNSIGNED DEFAULT NULL
            """, """
            CREATE TABLE IF NOT EXISTS `cli_key` (
            `cli_key_user_id` varchar(30) NOT NULL,
            `cli_key_host_ipv4` varchar(15) NOT NULL,
            `cli_key_host_ipv6` varchar(39) NOT NULL,
            `cli_key_value` varchar(32) NOT NULL,
            PRIMARY KEY  (`cli_key_user_id`,`cli_key_host_ipv4`,`cli_key_host_ipv6`) 
            )""", """
            INSERT IGNORE INTO config VALUES("smtp_obscure_links", "Would you like for links in emails to obscured by adding spaces between periods and stripping off http:// and https://?","boolean", "Yes")
            """, """
            INSERT IGNORE INTO config VALUES("user_inactivity_expiration", "Max number of days of inactivity permitted on a user account before the account is deleted from the system.", "number", "90")
            """, """
            INSERT IGNORE INTO config VALUES("geotagging", "Should users be allowed to geotag Filelocker uploads?", "boolean", "No")
            """, """
            INSERT IGNORE INTO config VALUES("db_version", "Running version of the Filelocker Database", "text", "%s")
            """ % FLVersion, """
            INSERT IGNORE INTO config VALUES("ldap_bind_user", "Account to use when binding to LDAP for searching (anonymous if blank)?", "text", "")
            """, """
            INSERT IGNORE INTO config VALUES("ldap_bind_pass", "Password to use when binding to LDAP for searching (anonymous if blank)?", "text", "")
            """, """
            INSERT IGNORE INTO config VALUES("ldap_is_active_directory", "Is this LDAP server and Active Directory server?", "boolean", "No")
            """, """
            INSERT IGNORE INTO config VALUES("ldap_domain_name", "Active Directory will not authenticate a bind unless you use the FQDN", "text", "")
            ""","""
            UPDATE config SET config_parameter_value = "%s" WHERE config_parameter_name = "db_version"
            """ % FLVersion, """
            UPDATE audit_log SET audit_log_action = "%s" WHERE audit_log_action = "%s"
            """ % ("Check In File", "File Checked In"), """
            UPDATE audit_log SET audit_log_action = "%s" WHERE audit_log_action = "%s"
            """ % ("Download File", "File Downloaded"), """
            UPDATE audit_log SET audit_log_action = "%s" WHERE audit_log_action = "%s"
            """ % ("Create Public Share", "Public Share File"), """
            UPDATE audit_log SET audit_log_action = "%s" WHERE audit_log_action = "%s"
            """ % ("Sent Email", "Email Sent"), """
            UPDATE audit_log SET audit_log_action = "%s" WHERE audit_log_action = "%s"
            """ % ("Failure to Send Email", "Email Send Failure"), """
            UPDATE audit_log SET audit_log_action = "%s" WHERE audit_log_action = "%s"
            """ % ("Create Private Group Share", "Private Group Share Files"), """
            UPDATE audit_log SET audit_log_action = "%s" WHERE audit_log_action = "%s"
            """ % ("Create Private Share", "Private Share File"), """
            UPDATE audit_log SET audit_log_action = "%s" WHERE audit_log_action = "%s"
            """ % ("Create Upload Request", "Generate Upload Request"), """
            UPDATE audit_log SET audit_log_action = "%s" WHERE audit_log_action = "%s"
            """ % ("Read Message (You)", "You Read a Message"), """
            UPDATE audit_log SET audit_log_action = "%s" WHERE audit_log_action = "%s"
            """ % ("Read Message (Recipient)", "Recipient Read a Message"), """
            UPDATE audit_log SET audit_log_action = "%s" WHERE audit_log_action = "%s"
            """ % ("Upload Requested File", "Requested File Uploaded")])
        for sql in dbUpdates:
            try:
                self.execute(sql, None)
            except Exception, e:
                logging.error("Could not update database: %s" % str(e))

    def execute(self, sql, sql_args, getId = False):
        """Executor function, takes arbitrary SQL and argument list, returns all results """
        import warnings
        warnings.simplefilter("ignore")
        try:
            results = None
            try:
                self.cursor.execute(sql, sql_args)
            except MySQLdb.IntegrityError, ie:
                raise ie
            except MySQLdb.OperationalError, oe: #Thread in pool dead maybe, reconnect
                self.cursor, self.db = (None, None)
                self.get_connection()
                self.cursor.execute(sql, sql_args)
            results = self.cursor.fetchall()
            resultId = None
            if getId:
                sql = "SELECT LAST_INSERT_ID() as ID"
                self.cursor.execute(sql, None)
                resultId = self.cursor.fetchone()['ID']
            if getId:
                return results, resultId
            else:
                return results
        except MySQLdb.IntegrityError, ie:
            raise ie
        except Exception, e:
            logging.error("Unable to run SQL query: %s" % str(e))
            raise FLError(False, ["Unable to run SQL query: %s" % str(e)])

class LocalDirectory(object):
    connection = None
    def __init__(self, dao):
        self.dao = dao
        
    def lookup_user(self, userId):
        sql = "SELECT * FROM user WHERE user_id=%s"
        sql_args = [userId,]
        results = self.dao.execute(sql, sql_args)
        for row in results:
            foundUser = User(row['user_first_name'], row['user_last_name'], row['user_email'], row['user_quota'], row['user_last_login_datetime'], row['user_tos_accept_datetime'], row['user_id'])
            return foundUser
        else:
            return None
        
    #This function will do a search on the local MySQL directory getting all matches for a combination of first names and last names 
    def get_user_matches(self, firstName=None, lastName=None, userId=None):
        sql_queries, sql_args = [], None
        if userId is not None:
            sql_queries.append("SELECT * FROM user WHERE INSTR(user_id, %s)")
            sql_args = [userId]
        elif firstName is not None and lastName is not None:
            firstName += "%"
            lastName += "%"
            sql_queries.append("SELECT * FROM user WHERE user_last_name LIKE %s AND user_first_name LIKE %s")
            sql_args = [lastName, firstName]
        elif firstName is None and lastName is not None:
            lastName += "%"
            sql_queries.append("SELECT * FROM user WHERE user_first_name LIKE %s")
            sql_queries.append("SELECT * FROM user WHERE user_last_name LIKE %s")
            sql_args = [lastName]
        elif firstName is not None and lastName is None:
            firstName += "%"
            sql_queries.append("SELECT * FROM user WHERE user_first_name LIKE %s")
            sql_args = [firstName]
        results = []
        for sql in sql_queries:
            results.extend(self.dao.execute(sql, sql_args))
        userResults = []
        for userRow in results:
            foundUser = User(userRow['user_first_name'], userRow['user_last_name'], userRow['user_email'], None, None, None, userRow['user_id'])
            userResults.append(foundUser)
        return userResults
        
    def authenticate(self, userId, password):
        m = md5()
        m.update(password)
        passwordHash = m.hexdigest()
        sql = "SELECT * FROM user WHERE user_id=%s AND user_password_hash=%s"
        sql_args = [userId, passwordHash]
        results = self.dao.execute(sql, sql_args)
        if len(results) > 0:
            return True
        else:
            return False

import cherrypy
from cherrypy.lib.sessions import Session
try:
    import cPickle as pickle
except ImportError:
    import pickle
    
class DbSession(Session):
    """ Implementation of the MySQL backend for sessions. It assumes
        a table like this:

            CREATE TABLE session (
                id VARCHAR(40) NOT NULL,
                data TEXT DEFAULT NULL,
                expiration_time DATETIME DEFAULT NULL,
                PRIMARY KEY (`id`)
            )
    
    You must provide your own get_db function.
    """
    def __init__(self, id=None, **kwargs):
        self.db = self.get_db()
        self.cursor = self.db.cursor()
        Session.__init__(self, id, **kwargs)
        
    def setup(cls, **kwargs):
        """Set up the storage system for MySQL-based sessions.
        
        This should only be called once per process; this will be done
        automatically when using sessions.init (as the built-in Tool does).
        """
        for k, v in kwargs.iteritems():
            setattr(cls, k, v)
    setup = classmethod(setup)
    
    def get_db(self):
        return cherrypy.thread_data.db #This requires that a db connection already be setup and thread pooled.
        
    def rebuild_connection(self):
        cherrypy.thread_data.db = cherrypy.thread_data.fl.db.get_db()
        self.db = cherrypy.thread_data.db
        self.cursor = self.db.cursor()
        
    def __del__(self):
        pass
    
    def _exists(self):
        # Select session data from table
        rows = self.execute('SELECT data, expiration_time FROM session WHERE id=%s', (self.id,))
        return bool(rows)

    def get_all_sessions(self): #Build a dictionary like the "cache" dict in RamSession
        cache = {}
        rows = self.execute('SELECT id, data, expiration_time FROM session')
        for row in rows:
            data = pickle.loads(row[1])
            cache[str(row[0])] = (data, row[2])
        return cache

    def _load(self):
        # Select session data from table
        rows = self.execute('SELECT data, expiration_time FROM session '
                            'WHERE id=%s', (self.id,))
        if not rows:
            return None
        
        pickled_data, expiration_time = rows[0]
        data = pickle.loads(pickled_data)
        return data, expiration_time
    
    def _save(self, expiration_time):
        pickled_data = pickle.dumps(self._data)
        self.execute('INSERT INTO session (id, data, expiration_time) VALUES(%s, %s, %s) ' 
                            'ON DUPLICATE KEY UPDATE data=%s, expiration_time = %s',
                            (self.id, pickled_data, expiration_time, pickled_data, expiration_time))
    
    def _delete(self):
        self.execute('DELETE FROM session WHERE id=%s', (self.id,))
   
    def acquire_lock(self):
        """Acquire an exclusive lock on the currently-loaded session data."""
        # MySQL doesn't have row level locking for the MyISAM style db
        self.locked = True
        self.execute('SELECT id FROM session WHERE id=%s LOCK IN SHARE MODE',
                            (self.id,))
    
    def release_lock(self):
        """Release the lock on the currently-loaded session data."""
        # We just close the cursor and that will remove the lock
        #   introduced by the "for update" clause
        #self.cursor.close()
        self.db.commit()
    
    def clean_up(self):
        """Clean up expired sessions."""
        self.execute('DELETE FROM session WHERE expiration_time < now()')

    def execute(self, sql, sql_args=None):
        try:
            self.cursor.execute(sql, sql_args)
        except MySQLdb.OperationalError, oe: #Thread in pool dead maybe, reconnect
            self.rebuild_connection()
            self.cursor.execute(sql, sql_args)
        self.db.commit()
        return self.cursor.fetchall()
            
INIT_TABLE_DELETE_SQL = ["DROP TABLE IF EXISTS `session`","DROP TABLE IF EXISTS `config`","DROP TABLE IF EXISTS `attribute`", "DROP TABLE IF EXISTS `user`", "DROP TABLE IF EXISTS `deletion_queue`", "DROP TABLE IF EXISTS `group_membership`", "DROP TABLE IF EXISTS `group_permission`", 
"DROP TABLE IF EXISTS `groups`", "DROP TABLE IF EXISTS `permission`", "DROP TABLE IF EXISTS `file`","DROP TABLE IF EXISTS `hidden_share`","DROP TABLE IF EXISTS `private_group_share`","DROP TABLE IF EXISTS `private_share`",
"DROP TABLE IF EXISTS `private_attribute_share`","DROP TABLE IF EXISTS `public_share`","DROP TABLE IF EXISTS `upload_ticket`","DROP TABLE IF EXISTS `user_permission`","DROP TABLE IF EXISTS `audit_log`","DROP TABLE IF EXISTS `cli_key`","DROP TABLE IF EXISTS `message`", "DROP TABLE IF EXISTS `message_recipient`" ]

INIT_TABLE_CREATE_SQL = [ """
CREATE TABLE `config` (
  `config_parameter_name` varchar(30) NOT NULL,
  `config_parameter_description` text NOT NULL,
  `config_parameter_type` enum('boolean', 'number', 'text') NOT NULL,
  `config_parameter_value` text default NULL,
  PRIMARY KEY (`config_parameter_name`)
)
""", """
CREATE TABLE `user` (
  `user_id` varchar(30) NOT NULL,
  `user_quota` int(15) default NULL,
  `user_last_login_datetime` datetime default NULL,
  `user_tos_accept_datetime` datetime default NULL,
  `user_email` varchar(320) default 'directory',
  `user_first_name` varchar(100) NOT NULL,
  `user_last_name` varchar(100) NOT NULL,
  `user_password_hash` varchar(64) default NULL,
  PRIMARY KEY  (`user_id`)
)""",  """
CREATE TABLE `deletion_queue` (
  `deletion_queue_file_path` varchar(255) NOT NULL,
  PRIMARY KEY  (`deletion_queue_file_path`)
)""",  """
CREATE TABLE `group_membership` (
  `group_membership_group_id` mediumint(9) NOT NULL,
  `group_membership_user_id` varchar(30) NOT NULL,
  PRIMARY KEY  (`group_membership_group_id`,`group_membership_user_id`),
  KEY `group_membership` (`group_membership_user_id`)
) """,  """
CREATE TABLE `group_permission` (
  `group_permission_permission_id` varchar(25) NOT NULL,
  `group_permission_group_id` mediumint(9) NOT NULL,
  PRIMARY KEY  (`group_permission_permission_id`,`group_permission_group_id`),
  KEY `group_permission` (`group_permission_group_id`)
)""", """
CREATE TABLE `groups` (
  `group_id` mediumint(9) NOT NULL auto_increment,
  `group_name` varchar(255) NOT NULL,
  `group_owner_id` varchar(30) NOT NULL,
  `group_scope` enum('public','private','reserved') default 'private',
  PRIMARY KEY  (`group_id`)
)""",  """
CREATE TABLE `permission` (
  `permission_id` varchar(25) NOT NULL,
  `permission_name` text NOT NULL,
  PRIMARY KEY  (`permission_id`)
)""",   """
CREATE TABLE `file` (
  `file_id` mediumint(9) NOT NULL auto_increment,
  `file_name` varchar(255) default NULL,
  `file_type` text,
  `file_size` bigint unsigned default NULL,
  `file_notes` varchar(255) default NULL,
  `file_uploaded_datetime` datetime default NULL,
  `file_owner_id` varchar(30) default NULL,
  `file_expiration_datetime` datetime default NULL,
  `file_passed_avscan` tinyint(1) default 0,
  `file_encryption_key` varchar(64) default NULL,
  `file_status` text,
  `file_location` enum("local", "remote") default "remote",
  `file_notify_on_download` tinyint(1) default 0,
  `file_upload_ticket_id` varchar(64) default NULL,
  PRIMARY KEY  (`file_id`)
)""", """
CREATE TABLE `hidden_share` (
  `hidden_share_target_id` varchar(30) NOT NULL,
  `hidden_share_file_id` mediumint(9) NOT NULL,
  PRIMARY KEY  (`hidden_share_target_id`,`hidden_share_file_id`)
)""", """
CREATE TABLE `private_group_share` (
  `private_group_share_file_id` mediumint(9) NOT NULL,
  `private_group_share_target_id` varchar(30) NOT NULL,
  PRIMARY KEY  (`private_group_share_file_id`,`private_group_share_target_id`)
)""",  """
CREATE TABLE `private_share` (
  `private_share_file_id` mediumint(9) NOT NULL,
  `private_share_target_id` varchar(30) NOT NULL,
  PRIMARY KEY  (`private_share_file_id`,`private_share_target_id`)
)""",  """
CREATE TABLE `private_attribute_share` (
  `private_attribute_share_file_id` mediumint(9) NOT NULL,
  `private_attribute_share_attribute_id` varchar(50) NOT NULL,
  PRIMARY KEY  (`private_attribute_share_file_id`,`private_attribute_share_attribute_id`)
)""","""
CREATE TABLE `attribute` (
  `attribute_id` varchar(50) NOT NULL,
  `attribute_name` text NOT NULL,
  PRIMARY KEY  (`attribute_id`)
)""",  """
CREATE TABLE `public_share` (
  `public_share_id` varchar(64) NOT NULL,
  `public_share_file_id` mediumint(9) NOT NULL,
  `public_share_expiration` datetime NOT NULL,
  `public_share_password_hash` varchar(64) default NULL,
  `public_share_type` enum('single', 'multi') default 'single',
  PRIMARY KEY  (`public_share_id`),
  KEY `public_share_file_id` (`public_share_file_id`)
)""",  """
CREATE TABLE `upload_ticket` (
  `upload_ticket_id` varchar(64) NOT NULL,
  `upload_ticket_owner_id` varchar(30) NOT NULL,
  `upload_ticket_max_size` int(255) default NULL,
  `upload_ticket_expiration` datetime NOT NULL,
  `upload_ticket_password_hash` varchar(64) default NULL,
  `upload_ticket_type` enum('single', 'multi') default 'single',
  `upload_ticket_scan_file` tinyint(1) default 1,
  PRIMARY KEY  (`upload_ticket_id`)
)""",  """
CREATE TABLE `user_permission` (
  `user_permission_permission_id` varchar(25) NOT NULL,
  `user_permission_user_id` varchar(30) NOT NULL,
  PRIMARY KEY  (`user_permission_permission_id`,`user_permission_user_id`),
  KEY `user_permission` (`user_permission_user_id`)
) """,  """
CREATE TABLE `audit_log` (
  `audit_log_id` mediumint(9) NOT NULL auto_increment,
  `audit_log_initiator_user_id` varchar(30) NOT NULL,
  `audit_log_action` varchar(255) NOT NULL,
  `audit_log_action_affected_user_id` varchar(30) default NULL,
  `audit_log_message` text NOT NULL,
  `audit_log_datetime` datetime NOT NULL,
  PRIMARY KEY  (`audit_log_id`) ) """,  """
CREATE TABLE `cli_key` (
  `cli_key_user_id` varchar(30) NOT NULL,
  `cli_key_host_ipv4` varchar(15) NOT NULL,
  `cli_key_host_ipv6` varchar(39) NOT NULL,
  `cli_key_value` varchar(32) NOT NULL,
  PRIMARY KEY  (`cli_key_user_id`,`cli_key_host_ipv4`,`cli_key_host_ipv6`) )""", """
CREATE TABLE `message` (
  `message_id` mediumint(9) NOT NULL auto_increment,
  `message_subject` text default null,
  `message_create_datetime` datetime NOT NULL,
  `message_owner_id` varchar(30) NOT NULL,
  `message_expiration_datetime` datetime default NULL,
  `message_encryption_key` varchar(64) default NULL,
  PRIMARY KEY (`message_id`) )""", """
CREATE TABLE `message_recipient` (
  `message_recipient_message_id` mediumint(9) NOT NULL,
  `message_recipient_user_id` varchar(30) NOT NULL,
  `message_recipient_viewed_datetime` datetime default NULL,
  PRIMARY KEY (`message_recipient_message_id`, `message_recipient_user_id`) )
""", """
CREATE TABLE `session` ( 
  `id` varchar(40) NOT NULL,
  `data` text DEFAULT NULL,
  `expiration_time` DATETIME DEFAULT NULL,
  PRIMARY KEY (`id`) ) ENGINE=InnoDB
"""]
  
INIT_DATA_SQL = ["INSERT INTO config VALUES(\"db_version\", \"Running version of the Filelocker Database\", \"text\", \"2.4\")",
"INSERT INTO config VALUES(\"org_name\", \"Name of your organization.\", \"text\", \"My Company\")",
"INSERT INTO config VALUES(\"org_url\", \"Home page of your organization.\", \"text\", \"http://www.mycompany.com\")",
"INSERT INTO config VALUES(\"admin_email\", \"Public email address of the Filelocker Administrator.\", \"text\", \"admin@mycompany.com\")",
"INSERT INTO config VALUES(\"max_file_life_days\", \"Max number of days a file can exist on the system. After this time, the file will be securely erased along with any shares it was associated with.\", \"number\", \"7\")",
"INSERT INTO config VALUES(\"user_inactivity_expiration\", \"Max number of days of inactivity permitted on a user account before the account is deleted from the system.\", \"number\", \"90\")",
"INSERT INTO config VALUES(\"delete_command\", \"Command used by the operating system that Filelocker is installed on to securely erase a file. This does not include arguments to the command (e.g. 'rm' not 'rm -p')\", \"text\", \"rm\")",
"INSERT INTO config VALUES(\"delete_arguments\", \"Any parameters needed by the delete command (in an additive fashion, such as -P, -fP, -fPq, etc)\", \"text\", \"-f\")",
"INSERT INTO config VALUES(\"antivirus_command\", \"Command to execute a virus scan of a file on the operating system on which Filelocker is installed.\", \"text\", \"clamscan\")",
"INSERT INTO config VALUES(\"file_command\", \"Command which returns information about a file's type. On most *nix systems, this will be the 'file -b' command\", \"text\", \"file -b\")",
"INSERT INTO config VALUES(\"max_file_size\", \"Maximum size (in Megabytes) for a single file on the system. Individual user quotas will ultimately override this if a user has less space available than this value.(DVD: 4812, CD: 700)\",\"number\", \"4812\")",
"INSERT INTO config VALUES(\"default_quota\", \"Default quota (in Megabytes) assigned to each user. This can be changed by an administrator\",\"number\", \"750\")",
"INSERT INTO config VALUES(\"smtp_sender\", \"This is the email address that Filelocker will send email notifications as.\",\"text\", \"filelocker@mycompany.com\")",
"INSERT INTO config VALUES(\"smtp_server\", \"The server that Filelocker will use to send mail\",\"text\", \"\")",
"INSERT INTO config VALUES(\"smtp_start_tls\", \"Should Filelocker use StartTLS when connection the SMTP server?\",\"boolean\", \"No\")",
"INSERT INTO config VALUES(\"smtp_port\", \"SMTP Port\",\"number\", \"25\")",
"INSERT INTO config VALUES(\"smtp_auth_required\", \"Does this SMTP server require authentication?\",\"boolean\", \"No\")",
"INSERT INTO config VALUES(\"smtp_user\", \"If SMTP server requires authentication, what username should be used to connect (leave blank if no auth required)?\",\"text\", \"\")",
"INSERT INTO config VALUES(\"smtp_pass\", \"If SMTP server requires authentication, what password should be used (leave blank if no auth required)?\",\"text\", \"\")",
"INSERT INTO config VALUES(\"smtp_obscure_links\", \"Would you like for links in emails to obscured by adding spaces between periods and stripping off http:// and https://?\",\"boolean\", \"Yes\")",
"INSERT INTO config VALUES(\"auth_type\", \"Authentication mechanism Filelocker should use (e.g. LDAP, CAS, Local)\",\"text\", \"local\")",
"INSERT INTO config VALUES(\"directory_type\", \"Type of directory to use (e.g. local, ldap)\",\"text\", \"local\")",
"INSERT INTO config VALUES(\"cas_url\", \"URL of CAS server\",\"text\", \"\")",
"INSERT INTO config VALUES(\"ldap_host\", \"URI of LDAP directory\",\"text\", \"\")",
"INSERT INTO config VALUES(\"ldap_bind_dn\", \"LDAP Bind DN (e.g. ou=ped,dc=purdue,dc=edu)\",\"text\", \"\")",
"INSERT INTO config VALUES(\"ldap_bind_user\", \"Account to use when binding to LDAP for searching (anonymous if blank)?\", \"text\", \"\")",
"INSERT INTO config VALUES(\"ldap_bind_pass\", \"Password to use when binding to LDAP for searching (anonymous if blank)?\", \"text\", \"\")",
"INSERT INTO config VALUES(\"ldap_is_active_directory\", \"Is this LDAP server and Active Directory server?\", \"boolean\", \"No\")",
"INSERT INTO config VALUES(\"ldap_domain_name\", \"Active Directory will not authenticate a bind unless you use the FQDN\", \"text\", \"\")",
"INSERT INTO config VALUES(\"ldap_user_name_attr\", \"LDAP username attribute\",\"text\", \"uid\")",
"INSERT INTO config VALUES(\"ldap_last_name_attr\", \"LDAP last name attribute\",\"text\", \"sn\")",
"INSERT INTO config VALUES(\"ldap_first_name_attr\", \"LDAP first name attribute\",\"text\", \"givenName\")",
"INSERT INTO config VALUES(\"ldap_displayname_attr\", \"LDAP display name attribute, if one is to be used\",\"text\", \"displayName\")",
"INSERT INTO config VALUES(\"ldap_email_attr\", \"LDAP email address attribute\",\"text\", \"mail\")",
"INSERT INTO config VALUES(\"banner\", \"Message displayed to all users upon login\", \"text\", \"\")",
"INSERT INTO config VALUES(\"geotagging\", \"Should users be allowed to geotag Filelocker uploads?\", \"boolean\", \"No\")",
"INSERT INTO permission VALUES(\"admin\", \"Administrators\")",
"INSERT INTO permission VALUES(\"expiration_exempt\", \"No file expiration\")"]
