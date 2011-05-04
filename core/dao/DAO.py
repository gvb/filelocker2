# -*- coding: utf-8 -*-

class DAO:
    connection = None
    def createFile (self, flFile):
        pass
    def getFile (self, fileId):
        pass
    def updateFile (self, flFile):
        pass
    def deleteFile (self, fileId):
        pass
    def createGroup (self, group):
        pass
    def getGroup (self, groupId):
        pass
    def updateGroup (self, group):
        pass
    def deleteGroup (self, groupId):
        pass
    def createPermission (self, permission):
        pass
    def getPermission (self, permissionId):
        pass
    def updatePermission (self, permission):
        pass
    def deletePermission (self, permissionId):
        pass
    def createPrivateShare (self, privateShare):
        pass
    def getPrivateShare (self, privateShareId):
        pass
    def updatePrivateShare (self, privateShare):
        pass
    def deletePrivateShare (self, privateShareId):
        pass
    def createPublicShare (self, publicShare):
        pass
    def getPublicShare (self, publicShareId):
        pass
    def updatePublicShare (self, publicShare):
        pass
    def deletePublicShare (self, publicShareId):
        pass
    def createUser (self, user):
        pass
    def getUser (self, userId):
        pass
    def updateUser (self, user):
        pass
    def deleteUser (self, userId):
        pass
    
    def getCurrentQuotaUsage(self, userId):
        pass
    def queueForDeletion(self, filePath):
        pass
    def deQueueForDeletion(self, filePath):
        pass
    def getFilesQueuedForDeletion(self):
        pass
