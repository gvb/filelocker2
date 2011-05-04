# -*- coding: utf-8 -*-
class ActionLog:
    def __init__(self, initiatorUserId, action, affectedUserId, message, actionDatetime, displayClass=None, logId=None):
            self.initiatorUserId = initiatorUserId
            self.action = action
            self.affectedUserId = affectedUserId
            self.message = message
            self.actionDatetime = actionDatetime
            self.displayClass = displayClass
            self.logId = logId
    
    def __str__(self):
        return "[%s] [%s] [%s] [%s] [%s]" % (self.message, self.actionDatetime.strftime("%m/%d/%Y"), self.initiatorUserId, self.action, self.affectedUserId)
        
    def get_dict(self):
        return {"initiatorUserId":self.initiatorUserId, "action": self.action, "affectedUserId": self.affectedUserId, "message": self.message, "actionDatetime": self.actionDatetime.strftime("%m/%d/%Y %H:%M"), "displayClass": self.displayClass, "logId": self.logId}