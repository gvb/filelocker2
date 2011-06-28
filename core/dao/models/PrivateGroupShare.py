# -*- coding: utf-8 -*-
from Share import Share
class PrivateGroupShare(Share):
    def __init__(self, fileId, ownerId, targetId):
        self.fileId = fileId
        self.ownerId = ownerId
        self.targetId = targetId
    
    def __str__(self):
        return "FileId: %s OwnerId:%s TargetId:%s" % (self.fileId, self.ownerId, self.targetId)
