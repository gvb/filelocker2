try:
    from hashlib import md5
except ImportError, ie:
    from md5 import md5
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy import Column,String,Enum,Integer,BigInteger,DateTime,Boolean,ForeignKey
__author__="wbdavis"
__date__ ="$Sep 27, 2011 8:48:55 PM$"
Base = declarative_base()

class File(Base):
    __tablename__ = "file"
    file_id = Column(Integer, primary_key=True)
    file_name = Column(String(255))
    file_type = Column(String)
    file_size = Column(BigInteger)
    file_notes = Column(String)
    file_uploaded_datetime = Column(DateTime)
    file_owner_id = Column(String(50), ForeignKey('user.user_id'))
    file_expiration_datetime = Column(DateTime)
    file_passed_avscan = Column(Boolean)
    file_encryption_key = Column(String(64))
    file_status = Column(String)
    file_location = Column(Enum("local", "remote"))
    file_notify_on_download = Column(Boolean)
    file_upload_ticket = Column(String(64))
    private_group_shares = relationship("PrivateGroupShare", backref="file")
    private_shares = relationship("PrivateShare", backref="file")
    public_shares = relationship("PublicShare", backref="file")
    private_attribute_shares = relationship("PrivateAttributeShare", backref="file")

    def __init__ (self, fileName, fileType, fileNotes, fileSizeBytes, fileUploadedDatetime, fileOwnerId, fileExpirationDatetime, filePassedAvScan, fileEncryptionKey=None, fileId=None, fileStatus=None, fileLocation="local", fileNotifyOnDownload=False, fileUploadTicketId=None):
        self.file_name = fileName
        self.file_type = fileType
        self.file_notes = fileNotes
        self.file_size = fileSizeBytes
        self.file_uploaded_datetime = fileUploadedDatetime
        self.file_owner_id = fileOwnerId
        self.file_expiration_datetime = fileExpirationDatetime
        self.file_passed_avscan = filePassedAvScan
        self.file_encryption_key = fileEncryptionKey
        self.file_status = fileStatus
        self.file_location = fileLocation
        self.file_notify_on_download = fileNotifyOnDownload
        self.file_upload_ticket = fileUploadTicketId
        if fileId is not None:
            self.file_id = fileId

class PrivateShare(Base):
    __tablename__ = "private_share"
    private_share_target_id = Column(Integer, ForeignKey("user.user_id"), primary_key=True)
    private_share_file_id = Column(Integer, ForeignKey("file.file_id"), primary_key=True)
    file = relationship("File", backref=backref('private_shares'))
    def __init__(self, fileId, targetId):
        self.private_share_file_id = fileId
        self.private_share_target_id = targetId

class PrivateGroupShare(Base):
    __tablename__ = "private_group_share"
    private_group_share_target_id = Column(Integer, ForeignKey("groups.group_id"), primary_key=True)
    private_group_share_file_id = Column(Integer, ForeignKey("file.file_id"), primary_key=True)
    file = relationship("File", backref=backref('private_group_shares'))
    def __init__(self, fileId, targetId):
        self.private_group_share_file_id = fileId
        self.private_group_share_target_id = targetId

class PublicShare(Base):
    __tablename__="public_share"
    public_share_id = Column(String(64), primary_key=True)
    public_share_file_id = Column(Integer, ForeignKey("file.file_id"), nullable=False)
    public_share_expiration = Column(DateTime)
    public_share_password_hash = Column(String(64))
    public_share_type = Column(Enum("single", "multi"), default="single")
    file = relationship("File", backref=backref('public_shares'))
    def __init__(self, fileId, ownerId, expirationDateTime, passwordHash, shareType="single", shareId=None):
        self.public_share_id = shareId
        self.public_share_file_id = fileId
        self.public_share_expiration = expirationDateTime
        self.public_share_password_hash = passwordHash
        self.public_share_type = shareType

    def generateShareId(self):
        import random
        return md5(str(random.random())).hexdigest()

class PrivateAttributeShare(Base):
    __tablename__ = "private_attribute_share"
    private_attribute_share_file_id = Column(Integer, ForeignKey("file.file_id"), primary_key=True)
    private_attribute_share_attribute_id = Column(String(50), ForeignKey("attribute.attribute_id"), primary_key=True)
    file = relationship("File", backref=backref('private_attribute_shares'))
    def __init__(self, fileId, attributeId):
        self.private_attribute_share_file_id = fileId
        self.private_attribute_share_attribute_id = attributeId

class ConfigParameter(Base):
    __tablename__ = "config"
    config_parameter_name = Column(String(30), primary_key=True)
    config_parameter_description = Column(String)
    config_parameter_type = Column(Enum("boolean", "number", "text", "datetime"))
    config_parameter_value = Column(String)

    def __init__ (self, parameterName, parameterDescription, pType, value):
        self.config_parameter_name = parameterName
        self.config_parameter_description = parameterDescription
        self.config_parameter_type = pType
        self.config_parameter_value = value
class User(Base):
    __tablename__ = "user"

    id = Column(String(50), primary_key=True)
    name = Column(String(50))
    email = Column(String(256))
    lastLoginDate = Column(DateTime)
    tosAcceptDate = Column(DateTime)
    salt = Column(Integer)
    password = Column(String(40))

    self.isRole = False
    self.userLastLogin = userLastLogin
    self.user = userTosAcceptDatetime
    self.userAttributes = []
    self.password = None
    def __init__ (self, firstName, lastName, userEmail, userQuota, userLastLogin, userTosAcceptDatetime, userId=None, userQuotaUsed=None):
        self.userFirstName = firstName
        self.userLastName = lastName
        self.userDisplayName = "%s %s" % (firstName, lastName)
        self.userEmail = userEmail
        self.userQuota = userQuota
        self.isRole = False
        self.userLastLogin = userLastLogin
        self.userTosAcceptDatetime = userTosAcceptDatetime
        self.userAttributes = []
        self.salt
        self.password = None
        if userId is not None:
            self.userId = userId
        if userQuotaUsed is not None:
            self.userQuotaUsed = userQuotaUsed
    def get_copy(self):
        cUser = User(self.userFirstName, self.userLastName, self.userEmail, self.userQuota, self.userLastLogin, self.userTosAcceptDatetime, self.userId, self.userQuotaUsed)
        return cUser

    def get_dict(self):
        return {'userFirstName':self.userFirstName, 'userLastName':self.userLastName, 'userDisplayName': self.userDisplayName, 'userEmail': self.userEmail, 'isRole': self.isRole, 'isAdmin': self.isAdmin, 'userId': self.userId, 'userQuotaUsed': self.userQuotaUsed, 'userQuota': self.userQuota}

    def __str__(self):
        return "First Name: %s Last Name: %s Display Name: %s Email: %s Quota: %s Last Login: %s TOS Accept Time: %s" % (self.userFirstName, self.userLastName, self.userDisplayName, self.userEmail, self.userQuota, self.userLastLogin, self.userTosAcceptDatetime)

group_membership_table = Table("group_membership", Base.metadata,
    Column("group_membership_group_id", Integer, ForeignKey("groups.group_id")),
    Column("group_membership_user_id", String(50), ForeignKey("user.user_id")))

class Group:
    __tablename__ = "groups"
    group_id = Column(Integer, primary_key=True)
    group_name = Column(String(255), nullable=False)    
    group_owner_id = Column(String(30))
    group_scope = Column(Enum("public", "private", "reserved"), default="private")
    group_members = relationship("User", secondary=group_membership_table)
    def __init__(self, groupScope, ownerId, groupName, groupMembers=None, groupId=None):
            self.group_scope = groupScope #public, private, reserved
            self.group_owner_id = ownerId
            self.group_name = groupName
            if groupMembers is not None:
                self.group_members = groupMembers
            else:
                self.group_members = []
            if groupId is not None:
                self.group_id = groupId
            else:
                self.group_id = None