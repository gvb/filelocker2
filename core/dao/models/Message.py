# -*- coding: utf-8 -*-
import datetime
class Message:
    def __init__(self, subject, body, createDatetime, ownerId, expirationDatetime, recipients, encryptionKey=None, messageId=None):
        self.messageSubject = subject
        self.messageBody = body
        self.messageCreateDatetime = createDatetime
        self.messageOwnerId = ownerId
        self.messageExpirationDatetime = expirationDatetime
        self.messageEncryptionKey = encryptionKey
        self.messageRecipients = recipients
        self.messageId = messageId
        self.messageViewedDatetime = None
    
    def get_dict(self):
        messageViewedDatetime, messageCreateDatetime, messageExpirationDatetime = (None, None, None)
        if self.messageViewedDatetime is not None:
            messageViewedDatetime = self.messageViewedDatetime.strftime("%m/%d/%Y")
        if self.messageCreateDatetime is not None:
            messageCreateDatetime = self.messageCreateDatetime.strftime("%m/%d/%Y")
        if self.messageExpirationDatetime is not None:
            messageExpirationDatetime = self.messageExpirationDatetime.strftime("%m/%d/%Y")
        messageDict = {'subject': self.messageSubject, 'body': self.messageBody, 'creationDatetime': messageCreateDatetime, 'ownerId': self.messageOwnerId, 'expirationDatetime': messageExpirationDatetime, 'id': self.messageId, 'viewedDatetime': messageViewedDatetime}
        if self.messageRecipients is not None:
            messageDict['messageRecipients'] = self.messageRecipients
        return messageDict
        