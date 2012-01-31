import datetime
import logging
import sys
import time
import StringIO
import sqlalchemy
import cherrypy
try:
    import cPickle as pickle
except ImportError:
    import pickle
try:
    from hashlib import md5
except ImportError, ie:
    from md5 import md5
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relation, backref, sessionmaker, mapper
from sqlalchemy import *
from lib.SQLAlchemyTool import configure_session_for_app, session, _engines
from lib.Encryption import hash_password

__author__="wbdavis"
__date__ ="$Sep 27, 2011 8:48:55 PM$"
Base = declarative_base()
BIGINT_ALIAS = None
FILE_FIELD_STORAGE = None
try: 
    import cherrypy._cpreqbody
    FILE_FIELD_STORAGE = cherrypy._cpreqbody.RequestBody
except ImportError: 
    import cherrypy._cpcgifs
    FILE_FIELD_STORAGE = cherrypy._cpcgifs.FieldStorage
    
try:
    from sqlalchemy.types import BigInteger
    BIGINT_ALIAS = BigInteger
except Exception, e:
    try:
        from sqlalchemy.databases.mysql import MSBigInteger
        logging.debug("Exeption e: %s" % str(e))
        BIGINT_ALIAS = MSBigInteger
    except Exception, e:
        logging.erro("Couldn't setup large integer storage: %s" % str(e))
  
#Database Backended Models
user_permissions_table = Table("user_permissions", Base.metadata,
    Column("user_id", String(30), ForeignKey("users.id"), primary_key=True, nullable=False),
    Column("permission_id", String(50), ForeignKey("permissions.id"), primary_key=True, nullable=False))

class User(Base):
    __tablename__ = "users"
    id = Column(String(30), primary_key=True)
    quota = Column(Integer)
    date_last_login = Column(DateTime, nullable=True)
    date_tos_accept = Column(DateTime, nullable=True)
    email = Column(String(320), default="")
    first_name = Column(String(100))
    last_name = Column(String(100))
    password = Column(String(80), nullable=True)
    _display_name = Column("display_name", Text, nullable=True)
    permissions = relation("Permission", secondary=lambda: user_permissions_table, backref="users")
    groups = relation("Group", secondary=lambda: group_membership_table, backref="members")
    quota_used = 0
    salt = None
    is_role = False
    authorized = True
    attributes = []
    received_messages = relation("MessageShare", backref="recipient", cascade="all, delete-orphan")
    upload_requests = relation("UploadRequest", backref="owner")
    user_shares = relation("UserShare", backref="users", cascade="all, delete-orphan")

    
    def set_display_name(self, value):
        self._display_name = value

    def get_display_name(self):
        if self._display_name is None or self._display_name == "":
            if self.last_name is None or self.last_name == "":
                return "%s" % (self.first_name)
            else:
                return "%s %s" % (self.first_name, self.last_name)
        else:
            return self._display_name

    def set_password(self, password):
        self.password = hash_password(password)
        
    display_name = property(get_display_name, set_display_name)

    def get_copy(self):
        loadedPermissions = []
        for permission in self.permissions:
            loadedPermissions.append(permission.get_copy())
        cUser = User(first_name=self.first_name, last_name=self.last_name, email=self.email, quota=self.quota, date_last_login=self.date_last_login, date_tos_accept=self.date_tos_accept, id=self.id, quota_used=self.quota_used, permissions=loadedPermissions)
        return cUser

    def get_dict(self):
        return {'userFirstName':self.first_name, 'userLastName':self.last_name, 'userDisplayName': self.display_name, 'userEmail': self.email, 'isRole': self.is_role, 'userId': self.id, 'userQuotaUsed': self.quota_used, 'userQuota': self.quota}

role_membership_table = Table("role_membership", Base.metadata,
    Column("role_id", String(30), ForeignKey("roles.id")),
    Column("user_id", String(30), ForeignKey("users.id")))

class Role(Base):
    __tablename__ = "roles"
    id = Column(String(30), primary_key=True, nullable=False)
    name = Column(String(50), nullable=False)
    email = Column(String(320), nullable=True)
    quota = Column(Integer, nullable=False)
    members = relation("User", secondary=lambda: role_membership_table, backref="roles")
    permissions = relation("Permission", secondary=lambda: role_permissions_table)

    def get_dict(self):
        membersList, permissionsList = [], []
        for member in self.members:
            membersList.append(member.get_dict())
        for permission in self.permissions:
            permissionsList.append(permission.get_dict())
        return {'id': self.id, 'name':self.name, 'email': self.email, 'quota':self.quota, 'members':membersList, 'permissions':permissionsList}
    
    def get_copy(self):
        loadedPermissions = []
        for permission in self.permissions:
            loadedPermissions.append(permission.get_copy())
        return Role(id=self.id, name=self.name, email=self.email, quota=self.quota, permissions=loadedPermissions)

role_permissions_table = Table("role_permissions", Base.metadata,
    Column("role_id", String(30), ForeignKey("roles.id"), primary_key=True, nullable=False),
    Column("permission_id", String(50), ForeignKey("permissions.id"), primary_key=True, nullable=False))
    
class Permission(Base):
    __tablename__ = "permissions"
    id = Column(String(50), primary_key=True)
    name = Column(String(255))
    inherited_from = None

    def __str__(self):
        return str(self.get_dict())

    def get_copy(self):
        return Permission(id=self.id, name=self.name, inherited_from=self.inherited_from)

    def get_dict(self):
        return {'id': self.id, 'name': self.name, 'inherited_from':self.inherited_from}


group_membership_table = Table("group_membership", Base.metadata,
    Column("group_id", Integer, ForeignKey("groups.id"), primary_key=True),
    Column("user_id", String(30), ForeignKey("users.id"), primary_key=True))

group_permissions_table = Table("group_permissions", Base.metadata,
    Column("group_id", Integer, ForeignKey("groups.id"), primary_key=True),
    Column("permission_id", String(50), ForeignKey("permissions.id"), primary_key=True))

class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    owner_id = Column(String(30), ForeignKey("users.id"), nullable=True)
    role_owner_id = Column(String(30), ForeignKey("roles.id"), nullable=True)
    #SQL Alchemy 0.5 doesn't support enums
    scope = Column(String(15), default="private")
#    members = relation("User", secondary=group_membership_table, backref="groups")
    permissions = relation("Permission", secondary=group_permissions_table)
    
    def get_dict(self):
        users = {}
        for user in self.members:
            users.append({'id':user.id, 'name':user.display_name})
        return {'id': self.id, 'name': self.name, 'owner_id':self.owner_id, 'role_owner_id':self.role_owner_id, 'scope': self.scope, 'members':users}

class File(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    type = Column(Text)
    size = Column(BIGINT_ALIAS)
    notes = Column(Text)
    date_uploaded = Column(DateTime)
    owner_id = Column(String(30), ForeignKey('users.id'), nullable=True)
    role_owner_id = Column(String(30), ForeignKey('roles.id'), nullable=True)
    date_expires = Column(DateTime)
    passed_avscan = Column(Boolean)
    encryption_key = Column(String(64))
    status = Column(String(255))
    notify_on_download = Column(Boolean, nullable=False)
    md5 = Column(String(64), nullable=True)
    upload_request_id = Column(String(64), ForeignKey("upload_requests.id"))
    document_type = None

    user_shares = relation("UserShare", backref="files", cascade="all, delete-orphan")
    #public_shares = relation("PublicShare", backref="files")
    group_shares = relation("GroupShare", backref="files", cascade="all, delete-orphan")
    attribute_shares = relation("AttributeShare", backref="files", cascade="all, delete-orphan")

    def shared_with(self, user):
        for share in self.user_shares:
            if share.user_id == user.id:
                return True
        groupIds = []
        for group in user.groups:
            groupIds.append(group.id)
        for share in group_shares:
            if share.group_id in groupIds:
                return True
        for share in attribute_shares:
            if share.attribute_id in user.attributes:
                return True
        return False

    def get_copy(self):
        return File(name = self.name, type = self.type, size = self.size, notes=self.notes,\
                    date_uploaded=self.date_uploaded, owner_id = self.owner_id, role_owner_id=self.role_owner_id, date_expires=self.date_expires,\
                    passed_avscan = self.passed_avscan, encryption_key=self.encryption_key, status=self.status,\
                    notify_on_download=self.notify_on_download, md5=self.md5,\
                    upload_request_id=self.upload_request_id)

    def get_dict(self):
        return {'name': self.name, 'id': self.id, 'owner_id': self.owner_id, 'role_owner_id': self.role_owner_id,\
        'size': self.size, 'date_uploaded': self.date_uploaded.strftime("%m/%d/%Y"),\
        'date_expires': self.date_expires.strftime("%m/%d/%Y"), 'passed_avscan':self.passed_avscan,\
        'document_type': self.document_type}

class HiddenShare(Base):
    __tablename__ = "hidden_shares"
    file_id = Column(Integer, ForeignKey("files.id"), primary_key=True)
    owner_id = Column(String(30), ForeignKey("roles.id"), primary_key=True)
    
class DeletedFile(Base):
    __tablename__ = "deletion_queue"
    file_name = Column(String(255), primary_key=True)

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    subject = Column(String(255))
    body = None #This is decrypted from the file, not stored in db
    date_sent = Column(DateTime, nullable=False)
    owner_id = Column(String(30), ForeignKey("users.id"), nullable=False)
    date_expires = Column(DateTime)
    encryption_key = Column(String(64), nullable=False)
    message_shares = relation("MessageShare", backref="message", single_parent=True, cascade="all, delete-orphan")

    def get_dict(self):
        messageViewedDatetime, messageCreateDatetime, messageExpirationDatetime = (None, None, None)
        if self.date_sent is not None:
            messageCreateDatetime = self.date_sent.strftime("%m/%d/%Y")
        if self.date_expires is not None:
            messageExpirationDatetime = self.date_expires.strftime("%m/%d/%Y")
        messageDict = {'subject': self.subject, 'body': self.body, 'creationDatetime': messageCreateDatetime, 'ownerId': self.owner_id, 'expirationDatetime': messageExpirationDatetime, 'id': self.id}
        messageDict['messageRecipients'] = []
        if self.message_shares is not None:
            for messageShare in self.message_shares:
                messageDict['messageRecipients'].append(messageShare.recipient_id)
        return messageDict

class MessageShare(Base):
    __tablename__ = "message_shares"
    message_id = Column(Integer, ForeignKey("messages.id"), primary_key=True)
    recipient_id = Column(String(30), ForeignKey("users.id"), primary_key=True)
    date_viewed = Column(DateTime, nullable=True, default=None)
    

class UserShare(Base):
    __tablename__ = "user_shares"
    user_id = Column(String(30), ForeignKey("users.id"), primary_key=True)
    file_id = Column(Integer, ForeignKey("files.id"), primary_key=True)
    flFile = relation("File")
    user = relation("User")

class GroupShare(Base):
    __tablename__ = "group_shares"
    group_id = Column(Integer, ForeignKey("groups.id"), primary_key=True)
    file_id = Column(Integer, ForeignKey("files.id"), primary_key=True)
    flFile = relation("File")
    group = relation("Group", backref="group_shares")

public_share_files = Table("public_share_files", Base.metadata,
    Column("share_id", String(64), ForeignKey("public_shares.id")),
    Column("file_id", Integer, ForeignKey("files.id")))
    
class PublicShare(Base):
    __tablename__="public_shares"
    id = Column(String(64), primary_key=True)
    owner_id = Column(String(30), ForeignKey("users.id"), nullable=True)
    role_owner_id = Column(String(30), ForeignKey("roles.id"), nullable=True)
    message = Column(Text, nullable=True)
    date_expires = Column(DateTime)
    password = Column(String(80))
    reuse = Column(String(15), default="single")
    files = relation("File", secondary=public_share_files, backref="public_shares")

    def generate_share_id(self):
        import random
        shareId = md5(str(random.random())).hexdigest()
        tryCount = 0
        existing = session.query(PublicShare).filter(PublicShare.id == shareId).scalar()
        while existing is not None and tryCount < 5:
            tryCount += 1
            shareId = md5(str(random.random())).hexdigest()
            existing = session.query(PublicShare).filter(PublicShare.id == shareId).scalar()
        if existing is not None:
            raise Exception("Could not create a unique share ID")
        self.id = shareId

    def set_password(self, password):
        self.password = hash_password(password)
        
    def get_dict(self):
        filesDict = {}
        for flFile in self.files:
            filesDict[flFile.id] = flFile.name
        return {'id':self.id, 'owner_id':self.owner_id, 'role_owner_id':self.role_owner_id, \
        'message': self.message, 'date_expires': self.date_expires.strftime("%m/%d/%Y") if self.date_expires is not None else None,\
        'reuse' : self.reuse, 'files': filesDict}

class AttributeShare(Base):
    __tablename__ = "attribute_shares"
    file_id = Column(Integer, ForeignKey("files.id"), primary_key=True)
    attribute_id = Column(String(50), ForeignKey("attributes.id"), primary_key=True)
    flFile = relation("File")
    attribute = relation("Attribute")

class UploadRequest(Base):
    __tablename__ = "upload_requests"
    id = Column(String(32), primary_key=True)
    owner_id = Column(String(30), ForeignKey("users.id"), nullable=False)
    max_file_size = Column(Float)
    scan_file = Column(Boolean, nullable=False)
    date_expires = Column(DateTime)
    password = Column(String(80))
    type = Column(String(15), default="single")
    expired = False

    def get_copy(self):
        return UploadRequest(id=self.id, owner_id=self.owner_id, max_file_size=self.max_file_size, scan_file=self.scan_file, date_expires=self.date_expires, password=self.password, type=self.type)

    def generate_id(self):
        import random
        shareId = md5(str(random.random())).hexdigest()
        tryCount = 0
        existing = session.query(UploadRequest).filter(UploadRequest.id == shareId).scalar()
        while existing is not None and tryCount < 5:
            tryCount += 1
            shareId = md5(str(random.random())).hexdigest()
            existing = session.query(UploadRequest).filter(UploadRequest.id == shareId).scalar()
        if existing is not None:
            raise Exception("Could not create a unique share ID")
        self.id = shareId

    def set_password(self, password):
        self.password = hash_password(password)

class ConfigParameter(Base):
    __tablename__ = "config"
    name = Column(String(30), primary_key=True)
    description = Column(Text, nullable=False)
    #Types: boolean, number, text, datetime
    type = Column(String(30))
    value = Column(String(255))

class Attribute(Base):
    __tablename__ = "attributes"
    id = Column(String(50), primary_key=True)
    name = Column(String(255), nullable=False)

    def __str__(self):
        return "%s (%s)" % (self.name, self.id)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    initiator_user_id = Column(String(30), ForeignKey("users.id"), nullable=False)
    action = Column(String(255), nullable=False)
    affected_user_id = Column(String(30), ForeignKey("users.id"))
    message = Column(Text, nullable=False)
    date = Column(DateTime, nullable=False)
    affected_role_id = Column(String(30), ForeignKey("roles.id"), nullable=True)
    file_id = Column(Integer, nullable=True)

    display_class = None

    def __init__(self, initiatorId, action, message, affectedId=None, role_id=None, file_id=None, date=datetime.datetime.now(), id=None):
        self.initiator_user_id = initiatorId
        self.action = action
        self.message = message
        self.affected_user_id = affectedId
        self.affected_role_id = role_id
        self.file_id = file_id
        self.date = date

    def __str__(self):
        return "Message [%s] Date[%s] Initiator[%s] Action[%s] Affected[%s] RoleInvolved[%s] FileId[%s]" % (self.message, self.date.strftime("%m/%d/%Y"), self.initiator_user_id, self.action, self.affected_user_id, self.affected_role_id, self.file_id)

    def get_dict(self):
        return {"initiatorUserId":self.initiator_user_id, "action": self.action, "affectedUserId": self.affected_user_id, "message": self.message, "actionDatetime": self.date.strftime("%m/%d/%Y %H:%M"), "displayClass": self.display_class, "logId": self.id, "roleId": self.affected_role_id, "fileId": self.file_id}

def create_admin_user(dburi, password):
    engine = create_engine(dburi, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    adminUser = session.query(User).filter(User.id=="admin").scalar()
    if adminUser is None:
        adminUser = User(id="admin", first_name="Administrator", quota=1024, date_tos_accept=datetime.datetime.now())
        session.add(adminUser)
        session.commit()
    adminUser.set_password(password)
    adminPermission = session.query(Permission).filter(Permission.id == "admin").one()
    if adminPermission not in adminUser.permissions:
        adminUser.permissions.append(adminPermission)
    session.commit()


def create_database_tables(dburi):
    engine = create_engine(dburi, echo=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    import Filelocker.__version__ as version
    initialConfigList = [("org_name", "Name of your organization.", "text", "My Company"),
    ("version", "Currently running version of Filelocker", "text", str(version)),
    ("org_url", "Home page of your organization.", "text", "http://www.mycompany.com"),
    ("admin_email", "Public email address of the Filelocker Administrator.", "text", "admin@mycompany.com"),
    ("max_file_life_days", "Max number of days a file can exist on the system. After this time, the file will be securely erased along with any shares it was associated with.", "number", "7"),
    ("user_inactivity_expiration", "Max number of days of inactivity permitted on a user account before the account is deleted from the system.", "number", "90"),
    ("delete_command", "Command used by the operating system that Filelocker is installed on to securely erase a file. This does not include arguments to the command (e.g. 'rm' not 'rm -p')", "text", "rm"),
    ("delete_arguments", "Any parameters needed by the delete command (in an additive fashion, such as -P, -fP, -fPq, etc)", "text", "-f"),
    ("antivirus_command", "Command to execute a virus scan of a file on the operating system on which Filelocker is installed.", "text", "clamscan"),
    ("file_command", "Command which returns information about a file's type. On most *nix systems, this will be the 'file -b' command", "text", "file -b"),
    ("max_file_size", "Maximum size (in Megabytes) for a single file on the system. Individual user quotas will ultimately override this if a user has less space available than this value.(DVD: 4812, CD: 700)","number", "4812"),
    ("default_quota", "Default quota (in Megabytes) assigned to each user. This can be changed by an administrator","number", "750"),
    ("smtp_sender", "This is the email address that Filelocker will send email notifications as.","text", "filelocker@mycompany.com"),
    ("smtp_server", "The server that Filelocker will use to send mail","text", ""),
    ("smtp_start_tls", "Should Filelocker use StartTLS when connection the SMTP server?","boolean", "No"),
    ("smtp_port", "SMTP Port","number", "25"),
    ("smtp_auth_required", "Does this SMTP server require authentication?","boolean", "No"),
    ("smtp_user", "If SMTP server requires authentication, what username should be used to connect (leave blank if no auth required)?","text", ""),
    ("smtp_pass", "If SMTP server requires authentication, what password should be used (leave blank if no auth required)?","text", ""),
    ("smtp_obscure_links", """Would you like for links in emails to obscured by adding spaces between periods and stripping off http:// and https://?""","boolean", "Yes"),
    ("auth_type", "Authentication mechanism Filelocker should use (e.g. LDAP, CAS, Local)","text", "local"),
    ("directory_type", "Type of directory to use (e.g. local, ldap)","text", "local"),
    ("cas_url", "URL of CAS server","text", ""),
    ("ldap_host", "URI of LDAP directory","text", ""),
    ("ldap_bind_dn", "LDAP Bind DN (e.g. ou=ped,dc=purdue,dc=edu)","text", ""),
    ("ldap_bind_user", "Account to use when binding to LDAP for searching (anonymous if blank)?", "text", ""),
    ("ldap_bind_pass", "Password to use when binding to LDAP for searching (anonymous if blank)?", "text", ""),
    ("ldap_is_active_directory", "Is this LDAP server and Active Directory server?", "boolean", "No"),
    ("ldap_domain_name", "Active Directory will not authenticate a bind unless you use the FQDN", "text", ""),
    ("ldap_user_name_attr", "LDAP username attribute","text", "uid"),
    ("ldap_last_name_attr", "LDAP last name attribute","text", "sn"),
    ("ldap_first_name_attr", "LDAP first name attribute","text", "givenName"),
    ("ldap_displayname_attr", "LDAP display name attribute, if one is to be used","text", "displayName"),
    ("ldap_email_attr", "LDAP email address attribute","text", "mail"),
    ("banner", "Message displayed to all users upon login", "text", ""),
    ("geotagging", "Should users be allowed to geotag Filelocker uploads?", "boolean", "No")]
    for cTuple in initialConfigList:
        confParameter = ConfigParameter(name=cTuple[0], description=cTuple[1], type=cTuple[2], value=cTuple[3])
        session.add(confParameter)
    adminPerm = Permission(id="admin", name="Administrator")
    expirationExemptPerm = Permission(id="expiration_exempt", name="User may have files that don't expire")
    session.add(adminPerm)
    session.add(expirationExemptPerm)
    session.commit()
    
def drop_database_tables(dburi):
    engine = create_engine(dburi, echo=True)
    conn = engine.connect()
    try:
        from sqlalchemy.schema import (DropTable, Table, ForeignKeyConstraint, DropConstraint, MetaData)
        from sqlalchemy.engine import reflection
        trans = conn.begin()
        inspector = reflection.Inspector.from_engine(engine)
        metadata = MetaData()
        tbs = []
        all_fks = []
        for table_name in inspector.get_table_names():
            fks = []
            for fk in inspector.get_foreign_keys(table_name):
                if not fk['name']:
                    continue
                fks.append(
                    ForeignKeyConstraint((), (), name=fk['name'])
                    )
            t = Table(table_name, metadata,*fks)
            tbs.append(t)
            all_fks.extend(fks)

        for fkc in all_fks:
            conn.execute(DropConstraint(fkc))

        for table in tbs:
            conn.execute(DropTable(table))
        trans.commit()
    except Exception, e:
        tables_list=['config' ,'user', 'deletion_queue', 'group_membership', 'group_permission', 'groups', 'permission',\
        'file', 'hidden_share', 'private_group_share','private_share', 'private_attribute_share', 'attribute', 'public_share',\
        'upload_ticket', 'user_permission', 'audit_log', 'cli_key' ,'message','message_recipient', 'session', 'user_permissions',\
        'role_membership','role_permissions', 'permissions', 'group_permissions',\
        'hidden_shares', 'messages', 'message_shares', 'user_shares', 'group_shares',\
        'public_share_files', 'public_shares', 'attribute_shares', 'upload_requests', 'attributes', 'audit_logs','files','users','roles']
        redelete_tables = []
        for table in tables_list:
            try:
                conn.execute("""DROP TABLE IF EXISTS %s""" % table)
            except sqlalchemy.exc.IntegrityError:
                redelete_tables.append(table)
        for table in redelete_tables:
            conn.execute("""DROP TABLE IF EXISTS %s""" % table)
    print "Dropped all"

#Non database backended models
class ProgressFile(object):
    def __init__(self, buf, fileName, file_object=None, uploadIndex=None, sessionId=None, *args, **kwargs):
        if file_object is None:
            #self.file_object = tempfile.NamedTemporaryFile(*args, **kwargs)
            self.file_object = get_temp_file()
        else:
            self.file_object = file_object
        self.sessionId = sessionId
        self.fileName = fileName
        self.transferred = 0
        self.buf = buf
        lcHDRS = {}
        for key, val in cherrypy.request.headers.iteritems():
            lcHDRS[key.lower()] = val
        self.pre_sized = float(lcHDRS['content-length'])
        self.speed = 1
        self.remaining = 0
        self.eta = 0
        self.uploadIndex = uploadIndex
        self._start = time.time()
        self.status = "Uploading"
    def write(self, data):
        now = time.time()
        self.transferred += len(data)
        if (now - self._start) == 0:
            self.speed = 0
        else:
            self.speed = self.transferred / (now - self._start)
        self.remaining = self.pre_sized - self.transferred
        if self.speed == 0: self.eta = 9999999
        else: self.eta = self.remaining / self.speed
        return self.file_object.write(data)

    def seek(self, pos):
        self.post_sized = self.transferred
        self.transferred = True
        return self.file_object.seek(pos)

    def read(self, size):
        return self.file_object.read(size)

    def stat_dict(self):
        valDict = {}
        valDict['fileName'] = self.fileName
        valDict['speed'] = '%9.2f' % (self.speed / 1024.0)
        valDict['sizeKB'] = '%9.2f' % (self.pre_sized / 1024.0)
        valDict['transferredKB'] = '%9.2f' % (self.transferred / 1024.0)
        valDict['eta'] = str(int(self.eta))
        if self.uploadIndex is not None:
            if self.uploadIndex.isdigit():
                valDict['uploadIndex'] = self.uploadIndex
            else:
                valDict['uploadIndex'] = "\"%s\"" % self.uploadIndex
        valDict['status'] = self.status
        return valDict


from zope.interface import Interface

class FilelockerPlugin(Interface):
    """
    Helper functions used by the extensible parts of Filelocker
    """

    def get_user_attributes(userId):
        """
        This function should return a list of attribute IDs that a user possesses.
        """

    def is_authorized(userId):
        """
        This function should return True unless you want to explicitly deny a user access to Filelocker. You can check a file or a database of unauthorized users
        or maybe check a directory for certain attributes (staff, currentStudent, etc) before granting permission. If any plugins return False, the user will not
        be permitted to log in.
        """

