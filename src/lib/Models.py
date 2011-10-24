import datetime
import time
import StringIO
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
from sqlalchemy.orm import relationship, backref, sessionmaker, mapper
from sqlalchemy import *
from lib.SQLAlchemyTool import configure_session_for_app, session, _engines
from lib.Encryption import hash_password
__author__="wbdavis"
__date__ ="$Sep 27, 2011 8:48:55 PM$"
Base = declarative_base()

#Database Backended Models
user_permissions_table = Table("user_permissions", Base.metadata,
    Column("user_id", String(30), ForeignKey("users.id"), primary_key=True, nullable=False),
    Column("permission_id", String(50), ForeignKey("permissions.id"), primary_key=True, nullable=False))

class User(Base):
    __tablename__ = "users"
    id = Column(String(30), primary_key=True)
    quota = Column(Integer)
    date_last_login = Column(DateTime)
    date_tos_accept = Column(DateTime)
    email = Column(String(320), default="directory")
    first_name = Column(String(100))
    last_name = Column(String(100))
    password = Column(String(80))
    permissions = relationship("Permission", secondary=lambda: user_permissions_table)
    quota_used = 0
    salt = None
    is_role = False
    authorized = True
    attributes = []
    display_name=None
    received_messages = relationship("ReceivedMessage", backref="messages")

    def set_password(self, password):
        self.password = hash_password(password)
        
    def get_copy(self):
        loadedPermissions = []
        for permission in self.permissions:
            loadedPermissions.append(permission.get_copy())
        cUser = User(first_name=self.first_name, last_name=self.last_name, email=self.email, quota=self.quota, date_last_login=self.date_last_login, date_tos_accept=self.date_tos_accept, id=self.id, quota_used=self.quota_used, permissions=loadedPermissions)
        return cUser

    def get_dict(self):
        return {'userFirstName':self.first_name, 'userLastName':self.last_name, 'userDisplayName': self.display_name, 'userEmail': self.email, 'isRole': self.is_role, 'userId': self.id, 'userQuotaUsed': self.quota_used, 'userQuota': self.quota}
#mapper(User, "users", properties={'permissions': relationship("Permission", lazy='joined')})
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
        return {'permissionId': self.id, 'permissionName': self.name, 'inheritedFrom':self.inherited_from}


group_membership_table = Table("group_membership", Base.metadata,
    Column("group_id", Integer, ForeignKey("groups.id")),
    Column("user_id", String(30), ForeignKey("users.id")))

group_permissions_table = Table("group_permissions", Base.metadata,
    Column("group_id", Integer, ForeignKey("groups.id"), primary_key=True),
    Column("permission_id", String(50), ForeignKey("permissions.id"), primary_key=True))

class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    owner_id = Column(String(30), ForeignKey("users.id"))
    scope = Column(Enum("public", "private", "reserved"), default="private")
    members = relationship("User", secondary=lambda: group_membership_table, backref="groups")
    permissions = relationship("Permission", secondary=lambda: group_permissions_table)

class File(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    type = Column(Text)
    size = Column(BigInteger)
    notes = Column(Text)
    date_uploaded = Column(DateTime)
    owner_id = Column(String(30), ForeignKey('users.id'))
    date_expires = Column(DateTime)
    passed_avscan = Column(Boolean)
    encryption_key = Column(String(64))
    status = Column(String(255))
    notify_on_download = Column(Boolean)
    md5 = Column(String(64), nullable=True)
    upload_request_id = Column(String(64), ForeignKey("upload_requests.id"))

    private_shares = relationship("PrivateShare", backref="files")
    public_shares = relationship("PublicShare", backref="files")
    private_group_shares = relationship("PrivateGroupShare", backref="files")
    private_attribute_shares = relationship("PrivateAttributeShare", backref="files")

    def shared_with(self, user):
        for share in private_shares:
            if share.user_id == user.id:
                return True
        groupIds = []
        for group in user.groups:
            groupIds.append(group.id)
        for share in private_group_shares:
            if share.group_id in groupIds:
                return True
        for share in private_attribute_shares:
            if share.attribute_id in user.attributes:
                return True
        return False

class DeletedFile(Base):
    __tablename__ = "deletion_queue"
    file_name = Column(String(255), primary_key=True)

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    subject = Column(String(255))
    body = None #This is decrypted from the file, not stored in db
    date_sent = Column(DateTime)
    owner_id = Column(String(30, ForeignKey("users.id")))
    date_expires = Column(DateTime)
    encryption_key = Column(String(64))
    date_viewed = None #This is for readers of recieved messages
    recipients = []

    def get_dict(self):
        messageViewedDatetime, messageCreateDatetime, messageExpirationDatetime = (None, None, None)
        if self.date_viewed is not None:
            messageViewedDatetime = self.date_viewed.strftime("%m/%d/%Y")
        if self.date_sent is not None:
            messageCreateDatetime = self.date_sent.strftime("%m/%d/%Y")
        if self.date_expires is not None:
            messageExpirationDatetime = self.date_expires.strftime("%m/%d/%Y")
        messageDict = {'subject': self.subject, 'body': self.body, 'creationDatetime': messageCreateDatetime, 'ownerId': self.owner_id, 'expirationDatetime': messageExpirationDatetime, 'id': self.id, 'viewedDatetime': messageViewedDatetime}
        if self.recipients is not None:
            messageDict['messageRecipients'] = self.recipients
        return messageDict

class ReceivedMessage(Base):
    __tablename__ = "message_recipients"
    message_id = Column(Integer, ForeignKey("messages.id"), primary_key=True)
    recipient_id = Column(String(30), ForeignKey("users.id"), primary_key=True)
    date_viewed = Column(DateTime, nullable=True, default=None)
    message = relationship("Message")

class PrivateShare(Base):
    __tablename__ = "private_shares"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    file_id = Column(Integer, ForeignKey("files.id"), primary_key=True)
    flFile = relationship("File")
    user = relationship("User")

class PrivateGroupShare(Base):
    __tablename__ = "private_group_shares"
    group_id = Column(Integer, ForeignKey("groups.id"), primary_key=True)
    file_id = Column(Integer, ForeignKey("files.id"), primary_key=True)
    flFile = relationship("File")
    group = relationship("Group")

class PublicShare(Base):
    __tablename__="public_shares"
    id = Column(String(64), primary_key=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False)
    date_expires = Column(DateTime)
    password = Column(String(80))
    reuse = Column(Enum("single", "multi"), default="single")
    flFile = relationship("File")

    def generate_share_id(self):
        import random
        shareId = md5(str(random.random())).hexdigest()
        while session.query(PublicShare).filter(PublicShare.id == shareId).scalar() is not None:
            shareId = md5(str(random.random())).hexdigest()
        return shareId

    def set_password(self, password):
        self.password = hash_password(password)

class PrivateAttributeShare(Base):
    __tablename__ = "private_attribute_shares"
    file_id = Column(Integer, ForeignKey("files.id"), primary_key=True)
    attribute_id = Column(String(50), ForeignKey("attributes.id"), primary_key=True)
    flFile = relationship("File")
    attribute = relationship("Attribute")

class UploadRequest(Base):
    __tablename__ = "upload_requests"
    id = Column(String(32), primary_key=True)
    owner_id = Column(String(30), ForeignKey("users.id"))
    max_file_size = Column(Float)
    scan_file = Column(Boolean)
    date_expires = Column(DateTime)
    password = Column(String(80))
    type = Column(Enum("single", "multi"))
    expired = False

    def generateTicketId(self):
        import random
        return md5(str(random.random())).hexdigest()

class ConfigParameter(Base):
    __tablename__ = "config"
    name = Column(String(30), primary_key=True)
    description = Column(Text)
    type = Column(Enum("boolean", "number", "text", "datetime"))
    value = Column(String(255))

class Attribute(Base):
    __tablename__ = "attributes"
    id = Column(String(50), primary_key=True)
    name = Column(String(255))

    def __str__(self):
        return "%s (%s)" % (self.name, self.id)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    initiator_user_id = Column(String(30), ForeignKey("users.id"))
    action = Column(String(255))
    affected_user_id = Column(String(30), ForeignKey("users.id"))
    message = Column(Text)
    date = Column(DateTime)
    display_class = None

    def __init__(self, initiatorId, action, message, affectedId=None):
        self.initiator_user_id = initiatorId
        self.action = action
        self.message = message
        self.affected_user_id = affectedId
        self.date = datetime.datetime.now()

    def __str__(self):
        return "[%s] [%s] [%s] [%s] [%s]" % (self.message, self.date.strftime("%m/%d/%Y"), self.initiator_user_id, self.action, self.affected_user_id)

    def get_dict(self):
        return {"initiatorUserId":self.initiator_user_id, "action": self.action, "affectedUserId": self.affected_user_id, "message": self.message, "actionDatetime": self.date.strftime("%m/%d/%Y %H:%M"), "displayClass": self.display_class, "logId": self.id}

def create_admin_user(dburi, password):
    adminUser = User(id="admin", first_name="Administrator", quota=1024, date_tos_accept=datetime.datetime.now())
    adminUser.set_password(password)
    engine = create_engine(dburi, echo=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    adminPermission = session.query(Permission).filter(Permission.id == "admin").one()
    adminUser.permissions.append(adminPermission)
    oldAdmin = session.query(User).filter(User.id=="admin").scalar()
    if oldAdmin is not None:
        session.delete(oldAdmin)
    session.add(adminUser)
    session.commit()
    print "Password after set: %s" % str(adminUser.password)


def create_database_tables(dburi):
    engine = create_engine(dburi, echo=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    initialConfigList = [("org_name", "Name of your organization.", "text", "My Company"),
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
    Base.metadata.drop_all(engine)
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

class FileFieldStorage(cherrypy._cpcgifs.FieldStorage):
    def __del__(self, *args, **kwargs):
        try:
            uploadKey = None
            if cherrypy.session.has_key("user"):
                uploadKey = cherrypy.session.get('user').userId
            elif cherrypy.session.has_key("uploadTicket"):
                uploadKey = cherrypy.session.has_key("uploadTicket").ownerId+":"+cherrypy.session.has_key("uploadTicket").ticketId
            if cherrypy.file_uploads.has_key(uploadKey):
                for transfer in cherrypy.file_uploads[uploadKey]:
                    if transfer.file_object.name == self.file_location:
                        cherrypy.file_uploads[uploadKey].remove(transfer)
                if len(cherrypy.file_uploads[uploadKey]) == 0:
                    del cherrypy.file_uploads[uploadKey]
            if os.path.isfile(self.file_location):
                fl = cherrypy.thread_data.flDict['app']
                tempFileName = self.file_location.split(os.path.sep)[-1]
                fl.queue_for_deletion(tempFileName)
        except KeyError:
            pass
        except KeyError, ke:
            pass
        except AttributeError, ae:
            pass
        except OSError, oe:
            pass
        except Exception, e:
            pass

    def make_file(self, binary=None):
        if self.filename is not None:
            uploadIndex = None
            if cherrypy.request.headers.has_key("uploadindex"):
                uploadIndex = cherrypy.request.headers['uploadindex']
            fo = ProgressFile(self.bufsize, self.filename, uploadIndex=uploadIndex)
            self.file_location = fo.file_object.name
            uploadKey = None
            if cherrypy.session.has_key("uploadTicket"):
                uploadKey = cherrypy.session.get("uploadTicket").ownerId+":"+cherrypy.session.get("uploadTicket").ticketId
            elif cherrypy.session.has_key("user"):
                uploadKey = cherrypy.session.get('user').userId

            if cherrypy.file_uploads.has_key(uploadKey):
                cherrypy.file_uploads[uploadKey].append(fo)
            else:
                cherrypy.file_uploads[uploadKey] = [fo,]
            return fo
        else:
            return StringIO.StringIO("")
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

