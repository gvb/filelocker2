from cherrypy.lib.sessions import Session
try:
    import cPickle as pickle
except ImportError:
    import pickle
    
try:
    from hashlib import md5
except ImportError, ie:
    from md5 import md5
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy import *
from lib.SQLAlchemyTool import configure_session_for_app, session, _engines
__author__="wbdavis"
__date__ ="$Sep 27, 2011 8:48:55 PM$"
Base = declarative_base()

#Database Backended Models
class User(Base):
    __tablename__ = "users"
    id = Column(String(30), primary_key=True)
    quota = Column(Integer)
    date_last_login = Column(DateTime)
    date_tos_accept = Column(DateTime)
    email = Column(String(320), default="directory")
    first_name = Column(String(100))
    last_name = Column(String(100))
    password = Column(String(72))
    permissions = relationship("Permission", secondary=user_permissions_table)
    quota_used = 0
    salt = None
    is_role = False
    attributes = []
    display_name=None
    def get_copy(self):
        cUser = User(first_name=self.first_name, last_name=self.last_name, email=self.email, quota=self.quota, last_login_date=self.last_login_date, tos_accept_date=self.tos_accept_date, id=self.id, quota_used=self.quota_used)
        return cUser

    def get_dict(self):
        return {'userFirstName':self.first_name, 'userLastName':self.last_name, 'userDisplayName': self.display_name, 'userEmail': self.email, 'isRole': self.is_role, 'userId': self.id, 'userQuotaUsed': self.quota_used, 'userQuota': self.quota}

group_membership_table = Table("group_membership", Base.metadata,
    Column("group_id", Integer, ForeignKey("groups.id")),
    Column("user_id", String(50), ForeignKey("users.id")))

class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    owner_id = Column(String(30), ForeignKey("users.id"))
    scope = Column(Enum("public", "private", "reserved"), default="private")
    members = relationship("User", secondary=group_membership_table, backref="groups")
    permissions = relationship("Permission", secondary=group_permissions_table)

class File(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    type = Column(Text)
    size = Column(BigInteger)
    notes = Column(Text)
    uploaded_date = Column(DateTime)
    owner_id = Column(String(50), ForeignKey('users.id'))
    date_expires = Column(DateTime)
    passed_avscan = Column(Boolean)
    encryption_key = Column(String(64))
    status = Column(String(255))
    notify_on_download = Column(Boolean)
    upload_ticket = Column(String(64))
    #private_group_shares = relationship("PrivateGroupShare", backref="file")
    #private_shares = relationship("PrivateShare", backref="file")
    #public_shares = relationship("PublicShare", backref="file")
    #private_attribute_shares = relationship("PrivateAttributeShare", backref="file")

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
    
message_recipients_table = Table("message_recipients", Base.metadata,
    Column("message_id", Integer, ForeignKey("messages.id"), primary_key=True, nullable=False),
    Column("recipient_id", String(50), ForeignKey("users.id"), primary_key=True, nullable=False),
    Column("date_viewed", DateTime, default=None))

class PrivateShare(Base):
    __tablename__ = "private_shares"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    file_id = Column(Integer, ForeignKey("files.id"), primary_key=True)
    flFile = relationship("File", backref('private_shares'))

class PrivateGroupShare(Base):
    __tablename__ = "private_group_shares"
    group_id = Column(Integer, ForeignKey("groups.id"), primary_key=True)
    file_id = Column(Integer, ForeignKey("files.id"), primary_key=True)
    flFile = relationship("File", backref('private_group_shares'))

class PublicShare(Base):
    __tablename__="public_shares"
    id = Column(String(64), primary_key=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False)
    expiration_date = Column(DateTime)
    password = Column(String(64))
    reuse = Column(Enum("single", "multi"), default="single")
    flFile = relationship("File", backref('public_shares'))

    def generateShareId(self):
        import random
        return md5(str(random.random())).hexdigest()

class PrivateAttributeShare(Base):
    __tablename__ = "private_attribute_shares"
    file_id = Column(Integer, ForeignKey("files.id"), primary_key=True)
    attribute_id = Column(String(50), ForeignKey("attributes.id"), primary_key=True)
    flFile = relationship("File", backref('private_attribute_shares'))

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

class Permission(Base):
    __tablename__ = "permissions"
    id = Column(String(50), primary_key=True)
    name = Column(String(255))
    inherited_from = None

    def __str__(self):
        return str(self.get_dict())

    def get_dict(self):
        return {'permissionId': self.id, 'permissionName': self.name, 'inheritedFrom':self.inherited_from}

user_permissions_table = Table("user_permissions", Base.metadata,
    Column("user_id", String(30), ForeignKey("users.id"), primary_key=True, nullable=False),
    Column("permission_id", String(50), ForeignKey("permissions.id"), primary_key=True, nullable=False))

group_permissions_table = Table("group_permissions", Base.metadata,
    Column("group_id", Integer, ForeignKey("groups.id"), primary_key=True),
    Column("permission_id", String(50), ForeignKey("permissions.id"), primary_key=True))

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

def create_database_tables(dburi):
    engine = create_engine(dburi, echo=True)
    Base.metadata.create_all(engine)

#Non database backended models
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

    def get_user_attributes(userId, fl):
        """
        This function should return a list of attribute IDs that a user possesses.
        """

    def is_authorized(userId, fl):
        """
        This function should return True unless you want to explicitly deny a user access to Filelocker. You can check a file or a database of unauthorized users
        or maybe check a directory for certain attributes (staff, currentStudent, etc) before granting permission. If any plugins return False, the user will not
        be permitted to log in.
        """

