# -*- coding: utf-8 -*-
import os
import re
import datetime
import MySQLdb
import logging
from Cheetah.Template import Template
import sys
from xml.dom.minidom import parse, parseString
from Models import *
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import *
from lib.SQLAlchemyTool import configure_session_for_app, session, _engines

def create_admin_user(dburi, password):
    adminUser = User(id="admin", first_name="Administrator", quota=1024, date_tos_accept=datetime.datetime.now())
    adminUser.set_password(password)
    engine = create_engine(dburi, echo=True)
    #Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    adminPermission = session.query(Permission).filter(Permission.id == "admin").one()
    adminUser.permissions.append(adminPermission)
    oldAdmin = session.query(User).filter(User.id=="admin").scalar()
    if oldAdmin is not None:
        session.delete(oldAdmin)
    session.add(adminUser)
    session.add(testUser1)
    session.add(testUser2)
    session.commit()
    print "Password after set: %s" % str(adminUser.password)

def export_db(exportFile):
    pass
    
def import_db(importFile, dburi):
    dom = parse(importFile)
    engine = create_engine(dburi, echo=True)
    Session = sessionmaker(bind=engine)
    session = Session()

    #Users
    for node in dom.getElementsByTagName("users"):
        for usernode in node.getElementsByTagName("user"):
            u = User(id=usernode.getAttribute("id"), first_name=usernode.getAttribute("first_name"),\
            last_name=usernode.getAttribute("last_name"), quota=int(usernode.getAttribute("quota")),\
            email=usernode.getAttribute("email"), date_last_login=usernode.getAttribute("date_last_login"),\
            date_tos_accept=usernode.getAttribute("date_tos_accept"), password=usernode.getAttribute("password"))
            session.add(u)
            session.commit()
            for permnode in usernode.getElementsByTagName("user_permission"):
                perm = session.query(Permission).filter(Permission.id==permnode.getAttribute("id")).one()
                u.permissions.append(perm)
            session.commit()

    #Groups
    for node in dom.getElementsByTagName("groups"):
        for groupnode in node.getElementsByTagName("group"):
            g = Group(id=groupnode.getAttribute("id"), name=groupnode.getAttribute("name"))
            session.add(g)
            for permnode in groupnode.getElementsByTagName("group_permission"):
                perm = session.query(Permission).filter(Permission.id==permnode.getAttribute("id")).one()
                g.permissions.append(perm)
            for membernode in groupnode.getElementsByTagName("group_member"):
                try:
                    m = session.query(User).filter(User.id == membernode.getAttribute("id")).one()
                    g.members.append(m)
                except Exception, e:
                    print "Couldn't find user %s to add to group %s(%s)" % (membernode.getAttribute("id"), g.name, g.id)
            session.commit()


    #Roles
    for node in dom.getElementsByTagName("roles"):
        for rolenode in node.getElementsByTagName("role"):
            r = Role(id=rolenode.getAttribute("id"), name=rolenode.getAttribute("name"),\
                    email=rolenode.getAttribute("email"), quota=int(rolenode.getAttribute("quota")))
            session.add(r)
            for permnode in rolenode.getElementsByTagName("role_permission"):
                perm = session.query(Permission).filter(Permission.id==permnode.getAttribute("id")).one()
                r.permissions.append(perm)
            for membernode in rolenode.getElementsByTagName("role_member"):
                m = session.query(User).getElementsByTagName("id").one()
                r.members.append(m)
            session.commit()
    
    #Files
    for node in dom.getElementsByTagName("files"):
        for filenode in node.getElementsByTagName("file"):
            f = File(id=filenode.getAttribute("id"), name=filenode.getAttribute("name"),\
                    type=filenode.getAttribute("type"), size=long(filenode.getAttribute("size")),\
                    notes=filenode.getAttribute("notes"), date_uploaded=filenode.getAttribute("date_uploaded"),\
                    owner_id=filenode.getAttribute("owner_id") if filenode.getAttribute("owner_id") != "" else None,\
                    role_owner_id=filenode.getAttribute("role_owner_id") if filenode.getAttribute("role_owner_id") != "" else None,\
                    date_expires=filenode.getAttribute("date_expires"), passed_avscan=filenode.getAttribute("passed_avscan"),\
                    encryption_key=filenode.getAttribute("encryption_key"), status=filenode.getAttribute("status"),\
                    notify_on_download=False if filenode.getAttribute("notify_on_download")=="0" else True,\
                    md5=filenode.getAttribute("md5"), upload_request_id=filenode.getAttribute("upload_request_id") if filenode.getAttribute("upload_request_id") != "" else None )
            session.add(f) 
        session.commit()
    
    #Upload Requests
    for node in dom.getElementsByTagName("upload_requests"):
        for requestnode in node.getElementsByTagName("upload_request"):
            u = UploadRequest(id=requestnode.getAttribute("id"), owner_id=requestnode.getAttribute("owner_id"), \
                            max_file_size=requestnode.getAttribute("max_file_size"), scan_file=requestnode.getAttribute("scan_file"), \
                            date_expires=requestnode.getAttribute("date_expires"), password=requestnode.getAttribute("password"),\
                            type=requestnode.getAttribute("type"))
            session.add(u)
        session.commit()
        
    #Messages
    for node in dom.getElementsByTagName("messages"):
        for messagenode in node.getElementsByTagName("message"):
            m = Message(id=messagenode.getAttribute("id"), subject=messagenode.getAttribute("subject"),\
                    date_sent=messagenode.getAttribute("date_sent"), owner_id=messagenode.getAttribute("owner_id"),\
                    date_expires=messagenode.getAttribute("date_expires"), encryption_key=messagenode.getAttribute("encryption_key"))
            session.add(m)
        session.commit()
        
    #Message Shares (Sent Messages)
    for node in dom.getElementsByTagName("message_shares"):
        for msnode in node.getElementsByTagName("message_share"):
            try:
                m = session.query(Message).filter(Message.id == msnode.getAttribute("message_id")).one()
                ms = MessageShare(message_id=msnode.getAttribute("message_id"), recipient_id=msnode.getAttribute("recipient_id"), date_viewed=msnode.getAttribute("date_viewed"))
                m.message_shares.append(ms)
            except Exception, e:
                print "Problem adding message share: %s" % str(e)
        session.commit()
    
    #User Shares
    for node in dom.getElementsByTagName("user_shares"):
        for unode in node.getElementsByTagName("user_share"):
            flFile = session.query(File).filter(File.id == unode.getAttribute("file_id")).one()
            us = UserShare(user_id=unode.getAttribute("user_id"), file_id=unode.getAttribute("file_id"))
            flFile.user_shares.append(us)
            session.add(us)
        session.commit()
    
    #Group Shares
    for node in dom.getElementsByTagName("group_shares"):
        for gnode in node.getElementsByTagName("group_shares"):
            flFile = session.query(File).filter(File.id == gnode.getAttribute("file_id")).one()
            gs = GroupShare(group_id=gnode.getAttribute("group_id"), file_id=gnode.getAttribute("file_id"))
            flFile.group_shares.append(gs)
            session.add(gs)
        session.commit()
    
    #Public Shares
    for node in dom.getElementsByTagName("public_shares"):
        for pnode in node.getElementsByTagName("public_share"):
            ps = PublicShare(id=pnode.getAttribute("id"), owner_id=pnode.getAttribute("owner_id"), date_expires=pnode.getAttribute("date_expires"), 
            reuse=pnode.getAttribute("reuse"), password=pnode.getAttribute("password") if pnode.getAttribute("password") != "" else None )
            session.add(ps)
            for psfnode in pnode.getElementsByTagName("file"):
                flFile = session.query(File).filter(File.id == int(psfnode.getAttribute("id"))).one()
                ps.files.append(flFile)
        session.commit()
    
    #Dynamic Attribute Shares
    for node in dom.getElementsByTagName("attribute_shares"):
        for anode in node.getElementsByTagName("attribute_share"):
            flFile = session.query(File).filter(File.id == anode.getAttribute("file_id")).one()
            ashare = AttributeShare(attribute_id=anode.getAttribute("attribute_id"), file_id=anode.getAttribute("file_id"))
            flFile.attribute_shares.append(ashare)
            session.add(ashare)
        session.commit()

    #Config Parameters
    for node in dom.getElementsByTagName("config_parameters"):
        for cnode in node.getElementsByTagName("config_parameter"):
            try:
                parameter = session.query(ConfigParameter).filter(ConfigParameter.name == cnode.getAttribute("name")).one()
                parameter.value = cnode.getAttribute("value")
            except sqlalchemy.orm.exc.NoResultFound:
                print "Found old config parameter, skipping"
        session.commit()
    
    for node in dom.getElementsByTagName("deleted_files"):
            for dnode in node.getElementsByTagName("deleted_file"):
                    d = DeletedFile(file_name=dnode.getAttribute("file_name"))
                    session.add(d)
            session.commit()
                
    #Audit Logs
    for node in dom.getElementsByTagName("audit_logs"):
        for anode in node.getElementsByTagName("audit_log"):
            log = AuditLog(anode.getAttribute("initiator_user_id"),\
            anode.getAttribute("action"), anode.getAttribute("affected_user_id"),\
            anode.getAttribute("message"), anode.getAttribute("date"), \
            anode.getAttribute("affected_role_id"), anode.getAttribute("file_id"), anode.getAttribute("id"))
            if log.action == "Create Private Share":
                log.action = "Create User Share"
            if log.action == "Create Private Group Share":
                log.action = "Create Group Share"
            session.add(log)
        session.commit()
        
    
    

class LegacyDBConverter():
    connection = None
    dbHost = None
    dbUser = None
    dbPassword = None
    dbName = None
    db = None
    cursor = None
    role_user_ids = []
    def __init__(self, dbHost, dbUser, dbPassword, dbName):
        self.dbHost = dbHost
        self.dbUser = dbUser
        self.dbPassword = dbPassword
        self.dbName = dbName
        self.get_connection()

    def get_connection(self):
        self.db = MySQLdb.connect(self.dbHost, self.dbUser, self.dbPassword, self.dbName)
        self.cursor = self.db.cursor(cursorclass=MySQLdb.cursors.DictCursor)

    def get_db(self):
        return MySQLdb.connect(self.dbHost, self.dbUser, self.dbPassword, self.dbName)

    def port_database(self, outfile=None):
        if outfile is None:
            outfile = os.path.join(os.getcwd(), "FL_Data_Export.xml")
        
        configParameters = self.GetAllParameters()
        roles, role_permissions = self.GetRoles()
        files = self.GetAllFiles()
        groups = self.GetAllGroups ()
        permissions = self.GetAllPermissions()
        userShares = self.GetAllUserShares(roles)
        groupShares = self.GetAllGroupShares()
        hiddenShares = self.GetAllHiddenShares()
        attributes = self.GetAllAttributes()
        attributeShares = self.GetAllAttributeShares()
        publicShares = self.GetAllPublicShares ()
        users = self.GetAllUsers ()
        messages = self.GetMessages()
        messageShares = self.GetAllMessageShares()
        uploadRequests = self.GetUploadRequests()
        deletedFiles = self.GetAllDeletedFiles()
        auditLogs = self.GetAuditLogs()
        templatePath = os.path.join(os.getcwd(), "lib", "DataSchema.tmpl")
        tpl = str(Template(file=templatePath, searchList=[locals(),globals()]))
        f = open(outfile, "wb")
        f.write(tpl)
        f.close()
        print "Data has been exported to %s" % outfile

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
        sql = "SELECT * FROM file"
        sql_args = None
        results = self.execute(sql, sql_args)
        allFiles = []
        if results is not None and len(results)>0:
            for row in results:
                currentFile = None
                if (row['file_owner_id'] in self.role_user_ids):
                    currentFile = File(name=row['file_name'], type=row['file_type'], notes=row['file_notes'], size=row['file_size'], date_uploaded=row['file_uploaded_datetime'], owner_id=None, role_owner_id=row['file_owner_id'], date_expires=row['file_expiration_datetime'], passed_avscan=row['file_passed_avscan'], encryption_key=row['file_encryption_key'], id=row['file_id'], status=row['file_status'],  notify_on_download=row['file_notify_on_download'], upload_request_id=row['file_upload_ticket_id'])
                else:
                    currentFile = File(name=row['file_name'], type=row['file_type'], notes=row['file_notes'], size=row['file_size'], date_uploaded=row['file_uploaded_datetime'], owner_id=row['file_owner_id'], role_owner_id=None, date_expires=row['file_expiration_datetime'], passed_avscan=row['file_passed_avscan'], encryption_key=row['file_encryption_key'], id=row['file_id'], status=row['file_status'],  notify_on_download=row['file_notify_on_download'], upload_request_id=row['file_upload_ticket_id'])
                allFiles.append(currentFile)
        return allFiles

#Groups
    def GetAllGroups (self):
        sql = "SELECT * FROM groups"
        sql_args = []
        results = self.execute(sql,sql_args)
        allGroups = []
        for row in results:
            group=None
            if row['group_owner_id'] in self.role_user_ids:
                group = Group(id=row['group_id'], name=row['group_name'], role_owner_id=row['group_owner_id'], scope=row['group_scope'])
            else:
                group = Group(id=row['group_id'], name=row['group_name'], owner_id=row['group_owner_id'], scope=row['group_scope'])
            sql_args = [group.id,]
            sql = "SELECT * FROM group_membership WHERE group_membership_group_id=%s"
            memberResults = self.execute(sql,sql_args)
            for memberRow in memberResults:
                group.members.append(User(id=memberRow['group_membership_user_id']))
            sql = "SELECT * FROM group_permission WHERE group_permission_group_id=%s"
            permissionResults = self.execute(sql,sql_args)
            for permissionRow in permissionResults:
                group.permissions.append(Permission(id=permissionRow['group_permission_permission_id']))
            allGroups.append(group)
        return allGroups

#Permissions
    def GetAllPermissions(self):
        sql = "SELECT * FROM permission WHERE permission_id NOT LIKE '(role)%%'"
        permissions = []
        results = self.execute(sql, None)
        for row in results:
            permissions.append(Permission(id=row['permission_id'], name=row['permission_name']))
        return permissions

#Private Shares
    def GetAllUserShares(self, rolesList=[]):
        roles = []
        for role in rolesList:
            roles.append(role.id)
        sql = "SELECT * FROM private_share"
        privateShareList = []
        results = self.execute(sql, None)
        for prShR in results:
            if prShR['private_share_target_id'] not in roles: #Roles no longer have the ability to be shared with
                privateShareList.append(UserShare(file_id=prShR['private_share_file_id'], user_id=prShR['private_share_target_id']))
        return privateShareList

#Private Group Shares
    def GetAllGroupShares(self):
        sql = "SELECT * FROM private_group_share"
        privateGroupShareList = []
        results = self.execute(sql, None)
        for row in results:
            privateGroupShareList.append(GroupShare(file_id=row['private_group_share_file_id'], group_id=row['private_group_share_target_id']))
        return privateGroupShareList

    def GetAllHiddenShares(self):
        sql = "SELECT * FROM hidden_share"
        results = self.execute(sql, None)
        hidden_shares = []
        for row in results:
            hidden_shares.append(HiddenShare(owner_id=row['hidden_share_target_id'], file_id=row['hidden_share_file_id']))
        return hidden_shares

#Private Attribute Shares
    def GetAllAttributes(self):
        sql = "SELECT * FROM attribute"
        results = self.execute(sql, None)
        attributes = []
        for row in results:
            attr = Attribute(id=row['attribute_id'], name=row['attribute_name'])
            attributes.append(attr)
        return attributes

    def GetAllAttributeShares(self):
        sql = "SELECT * FROM private_attribute_share"
        attributeShares = []
        results = self.execute(sql, None)
        for row in results:
            attributeShares.append(AttributeShare(attribute_id=row["private_attribute_share_attribute_id"], file_id=row["private_attribute_share_file_id"]))
        return attributeShares

#Public Shares
    def GetAllPublicShares (self):
        sql = "SELECT * FROM public_share, file WHERE file.file_id = public_share.public_share_file_id"
        results = self.execute(sql, None)
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
            if rolePermissions.has_key(row["user_permission_user_id"])==False:
                rolePermissions[row["user_permission_user_id"]] = []
            rolePermissions[row["user_permission_user_id"]].append(row['user_permission_permission_id'][6:])

        userPermissions={}
        pSql = "SELECT * FROM user_permission WHERE user_permission_permission_id NOT LIKE '(role)%%'"
        sql_args = []
        permResults = self.execute(pSql, sql_args)
        for row in permResults:
            if userPermissions.has_key(row["user_permission_user_id"])==False:
                userPermissions[row["user_permission_user_id"]] = []
            userPermissions[row["user_permission_user_id"]].append(row['user_permission_permission_id'])

        sql = "SELECT * FROM user"
        sql_args = []
        results = self.execute(sql, sql_args)
        currentUser = None
        for row in results:
            if row['user_id'] not in roleUserIds:
                currentUser = User(first_name=row['user_first_name'], last_name=row['user_last_name'], email=row['user_email'], quota=row['user_quota'], date_last_login=row['user_last_login_datetime'], date_tos_accept=row['user_tos_accept_datetime'], id=row['user_id'], password=row['user_password_hash'])
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
        role_permissions = {}
        pSql = "SELECT * FROM user_permission WHERE user_permission_permission_id NOT LIKE '(role)%%'"
        permResults = self.execute(pSql, None)
        for row in permResults:
            if role_permissions.has_key(row["user_permission_user_id"])==False:
                role_permissions[row["user_permission_user_id"]] = []
            role_permissions[row["user_permission_user_id"]].append(row['user_permission_permission_id'])
        rolesResults = self.execute(rSql, None)
        for row in rolesResults:
            userId = row['permission_id'][6:]
            sql = "SELECT * FROM user WHERE user_id=%s"
            sql_args=[userId,]
            roleUserResults = self.execute(sql, sql_args)
            for userRow in roleUserResults:
                roleName = "%s %s" % (userRow['user_first_name'], userRow['user_last_name'])
                newRole = Role(name=roleName, quota=int(userRow['user_quota']), email=userRow['user_email'], id=userRow['user_id'])
                self.role_user_ids.append(userRow['user_id'])
                roles.append(newRole)
        return roles, role_permissions
    
    def GetMessages(self):
        messages = []
        sql = "SELECT * FROM message"
        results = self.execute(sql, None)
        for row in results:
            if row['message_owner_id'] not in self.role_user_ids:
                messages.append(Message(id=row['message_id'], subject=row['message_subject'], date_sent=row['message_create_datetime'], owner_id=row['message_owner_id'], date_expires=row['message_expiration_datetime'], encryption_key=row['message_encryption_key']))
        return messages

    def GetAllMessageShares(self):
        messageRecipients = []
        sql = "SELECT * FROM message_recipient"
        results = self.execute(sql, None)
        for row in results:
            if row['message_recipient_user_id'] not in self.role_user_ids:
                messageRecipients.append(MessageShare(message_id=row['message_recipient_message_id'], recipient_id=row['message_recipient_user_id'], date_viewed=row['message_recipient_viewed_datetime']))
        return messageRecipients

#Upload Tickets
    def GetUploadRequests(self):
        sql = "SELECT * FROM upload_ticket"
        results = self.execute(sql, None)
        tickets = []
        if results is not None:
            for row in results:
                if row['upload_ticket_owner_id'] not in self.role_user_ids:
                    tickets.append(UploadRequest(owner_id=row['upload_ticket_owner_id'], max_file_size=row['upload_ticket_max_size'], date_expires=row['upload_ticket_expiration'], password=row['upload_ticket_password_hash'], scan_file=row['upload_ticket_scan_file'], type=row['upload_ticket_type'], id=row['upload_ticket_id']))
        return tickets

    def GetAllDeletedFiles(self):
        sql = "SELECT * FROM deletion_queue"
        sql_args=None
        results = self.execute(sql, sql_args)
        files = []
        for row in results:
            files.append(DeletedFile(file_name=row['deletion_queue_file_path']))
        return files

    def GetAuditLogs(self):
        logs = []
        sql = "SELECT * FROM audit_log"
        results = self.execute(sql, None)
        if results is not None and len(results) > 0:
            for row in results:
                fileId = None
                if row['audit_log_message'].find("[File ID") > -1:
                    m = re.search(r"\[File ID: (\d+)\]", row['audit_log_message'])
                    fileId = int(m.group(1).strip())
                newLog = None
                if row['audit_log_initiator_user_id'] in self.role_user_ids:
                    newLog = AuditLog(None, row['audit_log_action'],\
                    row['audit_log_message'], row['audit_log_action_affected_user_id'],\
                    row['audit_log_initiator_user_id'], fileId,row['audit_log_datetime'], row['audit_log_id'])
                else:
                    newLog = AuditLog(row['audit_log_initiator_user_id'], row['audit_log_action'],\
                    row['audit_log_message'], row['audit_log_action_affected_user_id'],\
                     None, fileId, row['audit_log_datetime'], row['audit_log_id'])
                logs.append(newLog)
        return logs

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


