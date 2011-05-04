# -*- coding: utf-8 -*-
try:
    from hashlib import md5
except ImportError, ie:
    from md5 import md5
class UploadTicket:
    def __init__ (self, ownerId, maxFileSize, expiration, passwordHash, scanFile, ticketType, ticketId = None):
        self.ownerId = ownerId
        self.maxFileSize = maxFileSize
        self.expiration = expiration
        self.passwordHash = passwordHash
        self.scanFile = scanFile
        self.ticketType = ticketType
        self.expired = False
        if ticketId is not None:
            self.ticketId = ticketId

    def generateTicketId(self):
        import random
        return md5(str(random.random())).hexdigest()
        
    def check_password(self, password):
        passwordHash = None
        if password is not None:
            passwordHash = md5(password).hexdigest()
        if passwordHash == self.passwordHash:
            return True
        else:
            return False
    
    def __str__(self):
        return "UPLOAD TICKET  [ownerId: %s, maxFileSize: %s, expiration: %s, passwordHash: %s, scanFile: %s, ticketType: %s, ticketId: %s]" % (self.ownerId, self.maxFileSize, self.expiration, self.passwordHash, self.scanFile, self.ticketType, self.ticketId)
