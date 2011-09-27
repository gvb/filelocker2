# -*- coding: utf-8 -*-
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
from sqlalchemy import Column,String,Enum,Sequence,Integer,BigInteger,DateTime,Boolean,ForeignKey
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