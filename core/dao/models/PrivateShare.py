# -*- coding: utf-8 -*-
from Share import Share
class PrivateShare(Share):
    def __init__(self, fileId, ownerId, targetId):
        self.fileId = fileId
        self.ownerId = ownerId
        self.targetId = targetId
