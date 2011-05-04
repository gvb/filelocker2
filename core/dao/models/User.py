# -*- coding: utf-8 -*-
class User:
    userId = None
    def __init__ (self, firstName, lastName, userEmail, userQuota, userLastLogin, userTosAcceptDatetime, userId=None, userQuotaUsed=None):
        self.userFirstName = firstName
        self.userLastName = lastName
        self.userDisplayName = "%s %s" % (firstName, lastName)
        self.userEmail = userEmail
        self.userQuota = userQuota
        self.isLocal = False
        self.isRole = False
        self.authorized = True
        self.userLastLogin = userLastLogin
        self.userTosAcceptDatetime = userTosAcceptDatetime
        self.userAttributes = []
        self.passwordHash = None
        self.userQuotaUsed = None
        if userId is not None:
            self.userId = userId
        if userQuotaUsed is not None:
            self.userQuotaUsed = userQuotaUsed
    
    def get_copy(self):
        cUser = User(self.userFirstName, self.userLastName, self.userEmail, self.userQuota, self.userLastLogin, self.userTosAcceptDatetime, self.userId, self.userQuotaUsed)
        return cUser
    
    def __str__(self):
        return "First Name: %s Last Name: %s Display Name: %s Email: %s Quota: %s Last Login: %s TOS Accept Time: %s" % (self.userFirstName, self.userLastName, self.userDisplayName, self.userEmail, self.userQuota, self.userLastLogin, self.userTosAcceptDatetime)