# -*- coding: utf-8 -*-
from Share import Share
try:
    from hashlib import md5
except ImportError, ie:
    from md5 import md5
class PublicShare(Share):
    def __init__(self, fileId, ownerId, expirationDateTime, passwordHash, shareType="single", shareId=None):
        self.fileId = fileId
        self.ownerId = ownerId
        self.expirationDateTime = expirationDateTime
        self.passwordHash = passwordHash
        self.shareType = shareType
        self.shareId = shareId

    def generateShareId(self):
        import random
        return md5(str(random.random())).hexdigest()