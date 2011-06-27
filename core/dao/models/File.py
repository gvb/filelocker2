# -*- coding: utf-8 -*-
class File:
    def __init__ (self, fileName, fileType, fileNotes, fileSizeBytes, fileUploadedDatetime, fileOwnerId, fileExpirationDatetime, filePassedAvScan, fileEncryptionKey=None, fileId=None, fileStatus=None, fileLocation="local", fileNotifyOnDownload=False, fileUploadTicketId=None):
        self.fileName = fileName
        if self.fileName is None:
            fileName = "Unknown.fl"
        self.fileType = fileType
        self.fileNotes = fileNotes
        self.fileSizeBytes = fileSizeBytes
        self.fileUploadedDatetime = fileUploadedDatetime
        self.fileOwnerId = fileOwnerId
        self.fileExpirationDatetime = fileExpirationDatetime
        self.filePassedAvScan = filePassedAvScan
        self.fileEncryptionKey = fileEncryptionKey
        self.fileStatus = fileStatus
        self.fileLocation = fileLocation
        self.fileNotifyOnDownload = fileNotifyOnDownload
        self.fileUploadTicketId = fileUploadTicketId 
        if fileId is not None:
            self.fileId = fileId

    def __str__(self):
        return "Name: %s Type: %s Notes: %s OwnerId: %s FileID: %s" % (self.fileName, self.fileType, self.fileNotes, self.fileOwnerId, self.fileId)
        
        