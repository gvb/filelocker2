# -*- coding: utf-8 -*-

import datetime
import MySQLdb
import logging
from DAO import DAO
import sys
from models import *

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

    def GetAllParameters(self):
        params = []
        sql = "SELECT * FROM config"
        results = self.execute(sql, None)
        if results is not None and len(results)>0:
            for row in results:
                param = ConfigParameter(name=row['config_parameter_name'], description=row['config_parameter_description'], type=row['config_parameter_type'], value=row['config_parameter_value'])
                params.append(param)
        return params

    def GetAllFiles(self):
        sql = "SELECT * FROM file WHERE file_expiration_datetime < now()"
        sql_args = None
        results = self.execute(sql, sql_args)
        allFiles = []
        for row in results:
            currentFile = File(name=row['file_name'], type=row['file_type'], notes=row['file_notes'], size=row['file_size'], date_uploaded=row['file_uploaded_datetime'], owner_id=row['file_owner_id'], date_expires=row['file_expiration_datetime'], passed_avscan=row['file_passed_avscan'], encryption_key=row['file_encryption_key'], id=row['file_id'], status=row['file_status'],  notify_on_download=row['file_notify_on_download'], upload_request_id=row['file_upload_ticket_id'])
            expiredFiles.append(currentFile)
        return allFiles

#Groups
    def GetAllGroups (self):
        sql = "SELECT * FROM groups"
        sql_args = []
        results = self.execute(sql,sql_args)
        allGroups = []
        for row in results:
            group = Group(id=row['group_id'], name=row['group_name'], owner_id=row['group_owner_id'], scope=row['group_scope'])
            sql_args = [groupId,]
            sql = "SELECT * FROM group_membership WHERE group_membership_group_id=%s"
            memberResults = self.execute(sql,sql_args)
            for memberRow in memberResults:
                groupMembers.append(User(id=memberRow['group_membership_user_id']))
            sql = "SELECT * FROM group_permission WHERE group_permission_group_id=%s"
            permissionResults = self.execute(sql,sql_args)
            for permissionRow in permissionResults:
                group.permissions.append(Permission(id=permissionRow['group_permission_permission_id']))
            allGroups.append(group)
        return allGroups

#Permissions
    def GetAllPermissions(self):
        sql = "SELECT * FROM permission"
        permissions = []
        results = self.execute(sql, None)
        for row in results:
            permissions.append(Permission(id=row['permission_id'], name=row['permission_name']))
        return permissions

#Private Shares
    def GetAllUserShares(self):
        files = self.getFilesByOwner(ownerId)
        sql = "SELECT * FROM private_share"
        privateShareList = []
        results = self.execute(sql, sql_args)
        for prShR in results:
            privateShareList.append(UserShare(file_id=prShR['private_share_file_id'], user_id=prShR['private_share_target_id']))
        return privateShareList

#Private Group Shares
    def GetAllGroupShares(self):
        sql = "SELECT * FROM private_group_share"
        privateGroupShareList = []
        results = self.execute(sql, sql_args)
        for row in results:
            privateGroupShareList.append(GroupShare(file_idrow['private_group_share_file_id'], group_id=row['private_group_share_target_id']))
        return privateGroupShareList

    def getHiddenSharesDictList(self):
        sql = "SELECT * FROM hidden_share"
        sql_args = []
        results = self.execute(sql, sql_args)
        hidden_shares = []
        for row in results:
            hidden_shares.append({'user_id': row['hidden_share_target_id'], 'file_id':row['hidden_share_file_id']})
        return hidden_shares

#Private Attribute Shares
    def GetAllAttributes(self):
        sql = "SELECT * FROM attribute"
        sql_args = None
        results = self.execute(sql, sql_args)
        attributes = []
        for row in results:
            attr = Attribute(row['attribute_id'], row['attribute_name'])
            attributes.append(attr)
        return attributes

    def GetAllAttributeShares(self):
        sql = "SELECT * FROM private_attribute_share"
        sql_args = []
        attributeShares = []
        results = self.execute(sql, sql_args)
        for row in results:
            attributeShares.append(AttributeShare(attribute_id=row["private_attribute_share_attribute_id"], file_id=row["private_attribute_share_file_id"]))
        return attributeShares

#Public Shares
    def GetAllPublicShares (self):
        sql = "SELECT * FROM public_share, file WHERE file.file_id = public_share.public_share_file_id"
        sql_args = []
        results = self.execute(sql, sql_args)
        publicShares = []
        for row in results:
            currentPubShare = PublicShare(id=row['public_share_id'], owner_id=row['file_owner_id'], date_expires=row['public_share_expiration'], password=row['public_share_password_hash'], reuse=row['public_share_type'])
            currentPubShare.files.append(File(id=row['public_share_file_id']))
            publicShares.append(currentPubShare)
        return publicShares

#User functions
    def GetAllUsers (self):
        users = []
        roleUserIds = []
        rSql = "SELECT * FROM permission WHERE permission_id LIKE '(role)%%'"
        sql_args = []
        rolesResults = self.execute(rSql, sql_args)
        for row in rolesResults:
            roleUserIds.append(row['permission_id'][6:])
        
        rolePermissions={}
        pSql = "SELECT * FROM user_permission WHERE user_permission_permission_id LIKE '(role)%%'"
        sql_args = []
        rolesPermResults = self.execute(pSql, sql_args)
        for row in rolesPermResults:
            if rolePermission.has_key(row["user_permission_user_id"])==False:
                rolePermissions[row["user_permission_user_id"]] = []
            rolePermissions[row["user_permission_user_id"]].append(row['user_permission_permission_id'][6:])

        userPermissions={}
        pSql = "SELECT * FROM user_permission WHERE user_permission_permission_id NOT LIKE '(role)%%'"
        sql_args = []
        permResults = self.execute(pSql, sql_args)
        for row in permResults:
            if userPermissions.has_key(row["user_permission_user_id"])==False:
                userPermissions[row["user_permission_user_id"]] = []
            userPermissions[row["user_permission_user_id"]].append(row['user_permission_permission_id'][6:])

        sql = "SELECT * FROM user"
        sql_args = []
        results = self.execute(sql, sql_args)
        currentUser = None
        for row in results:
            if row['user_id'] not in roleUserIds:
                currentUser = User(first_name=row['user_first_name'], last_name=row['user_last_name'], email=row['user_email'], quota=row['user_quota'], date_last_login=row['user_last_login_datetime'], date_tos_accept=row['user_tos_accept_datetime'], id=row['user_id'])
                if (rolePermissions.has_key(currentUser.id)):
                    for roleId in rolePermissions[currentUser.id]:
                        currentUser.roles.append(Role(id=roleId))
                if (userPermissions.has_key(currentUser.id)):
                    for permId in userPermissions[currentUser.id]:
                        currentUser.permissions.append(Permission(id=permId))
                users.append(currentUser)
        return users

    def GetRoles(self):
        rSql = "SELECT * FROM permission WHERE permission_id LIKE '(role)%%'"
        sql_args = []
        roles=[]
        rolesResults = self.execute(rSql, sql_args)
        for row in rolesResults:
            userId = row['permission_id'][6:]
            sql = "SELECT * FROM user WHERE user_id=%s"
            sql_args=[userId,]
            roleUserResults = self.execute(sql, sql_args)
            for userRow in roleUserResults:
                roleName = "%s %s" % (row['user_first_name'], row['user_last_name'])
                roles.append(Role(name=roleName, quota=int(row['user_quota']), email=row['user_email'], id=row['user_id']))

    def GetMessages(self):
        messages = []
        sql = "SELECT * FROM message"
        results = self.execute(sql, None)
        for row in results:
            messages.append(Message(id=row['message_id'], subject=row['message_subject'], date_sent=row['message_create_datetime'], owner_id=row['message_owner_id'], date_expires=row['message_expiration_datetime'], encryption_key=row['message_encryption_key']))
        return messages

    def GetReceivedMessages(self):
        messageRecipients = []
        sql = "SELECT * FROM message_recipient"
        results = self.execute(sql, None)
        for row in results:
            messageRecipients.append(ReceivedMessage(message_id=row['message_recipient_message_id'], recipient_id=row['message_recipient_user_id'], date_viewed=row['message_recipient_viewed_datetime']))
        return messageRecipients

#CLI Key Management
    def getCLIKeyList(self, userId):
        sql = "SELECT * FROM cli_key WHERE cli_key_user_id=%s"
        sql_args = [userId]
        CLIKeys = []
        results = self.execute(sql, sql_args)
        for row in results:
            newKey = CLIKey(row['cli_key_host_ipv4'], row['cli_key_host_ipv6'], row['cli_key_value'])
            CLIKeys.append(newKey)
        return CLIKeys


#Upload Tickets
    def GetUploadRequests(self):
        sql = "SELECT * FROM upload_ticket WHERE upload_ticket_owner_id=%s"
        sql_args = []
        ticketRows = self.execute(sql, sql_args)
        tickets = []
        for ticketRow in ticketRows:
            tickets.append(UploadRequest(owner_id=ticketRow['upload_ticket_owner_id'], max_size=ticketRow['upload_ticket_max_size'], date_expires=ticketRow['upload_ticket_expiration'], password=ticketRow['upload_ticket_password_hash'], scan_file=ticketRow['upload_ticket_scan_file'], type=ticketRow['upload_ticket_type'], id=ticketRow['upload_ticket_id']))
        return tickets

    def GetAllDeletedFiles(self):
        sql = "SELECT * FROM deletion_queue"
        sql_args=None
        results = self.execute(sql, sql_args)
        files = []
        for row in results:
            files.append(DeletedFile(file_name=row['deletion_queue_file_path'])
        return files

    def GetAuditLogs(self):
        relevantLogs, sql_args = [], []
        sql = "SELECT * FROM audit_log"
        results = self.execute(sql, sql_args)
        if results is not None and len(results) > 0:
            for row in results:
                newLog = ActionLog(row['audit_log_initiator_user_id'], row['audit_log_action'], row['audit_log_action_affected_user_id'], row['audit_log_message'], row['audit_log_datetime'], row['audit_log_id'])
                relevantLogs.append(newLog)
        return relevantLogs


    def execute(self, sql, sql_args, getId = False):
        """Executor function, takes arbitrary SQL and argument list, returns all results """
        import warnings
        warnings.simplefilter("ignore")
        try:
            results = None
            if self.cursor is None or self.db is None:
                self.cursor, self.db = (None, None)
                self.get_connection()
                logging.error("Connection was None, rebuilt...")
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


