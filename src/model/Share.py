# -*- coding: utf-8 -*-
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
from sqlalchemy import Column,String,Integer,ForeignKey
class Share(Base):
   shareId = Column(Integer, primary_key=True)
   fileId = Column(Integer, ForeignKey("file.file_id"))
   ownerId = Column(String(50), ForeignKey("user.user_id"))


