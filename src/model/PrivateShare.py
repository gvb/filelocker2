# -*- coding: utf-8 -*-
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
from sqlalchemy import Column,String,Integer,ForeignKey
class PrivateShare(Base):
    private_share_target_id = Column(Integer, ForeignKey("use.user_id"), primary_key=True)
    private_share_file_id = Column(Integer, ForeignKey("file.file_id"), primary_key=True)
    ownerId = Column(String(50), ForeignKey("user.user_id"))
    def __init__(self, fileId, ownerId, targetId):
        self.fileId = fileId
        self.ownerId = ownerId
        self.targetId = targetId
