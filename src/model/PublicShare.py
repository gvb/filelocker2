# -*- coding: utf-8 -*-
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
Base = declarative_base()
from sqlalchemy import Column,String,Enum,Integer,DateTime,ForeignKey
try:
    from hashlib import md5
except ImportError, ie:
    from md5 import md5
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