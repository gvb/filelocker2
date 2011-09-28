# -*- coding: utf-8 -*-
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
from sqlalchemy import Column,String,Integer,ForeignKey
class PrivateAttributeShare(Base):
    __tablename__ = "private_attribute_share"
    private_attribute_share_file_id = Column(Integer, ForeignKey("file.file_id"), primary_key=True)
    private_attribute_share_attribute_id = Column(String(50), ForeignKey("attribute.attribute_id"), primary_key=True)
    def __init__(self, fileId, attributeId):
        self.private_attribute_share_file_id = fileId
        self.private_attribute_share_attribute_id = attributeId