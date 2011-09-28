# -*- coding: utf-8 -*-
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
from sqlalchemy import Column,Integer,ForeignKey
class PrivateGroupShare(Base):
    __tablename__ = "private_group_share"
    private_group_share_target_id = Column(Integer, ForeignKey("user.user_id"), primary_key=True)
    private_group_share_file_id = Column(Integer, ForeignKey("file.file_id"), primary_key=True)
    def __init__(self, fileId, targetId):
        self.private_group_share_file_id = fileId
        self.private_group_share_target_id = targetId

