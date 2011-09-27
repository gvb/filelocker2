# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, String, DateTime
class User(Base):
    __tablename__ = "user"

    id = Column(String(50), primary_key=True)
    name = Column(String(50))
    email = Column(String(256))
    lastLoginDate = Column(DateTime)
    tosAcceptDate = Column(DateTime)
    salt = Column(Integer)
    password = Column(String(40))

    self.isRole = False
    self.userLastLogin = userLastLogin
    self.user = userTosAcceptDatetime
    self.userAttributes = []
    self.password = None
    def __init__ (self, firstName, lastName, userEmail, userQuota, userLastLogin, userTosAcceptDatetime, userId=None, userQuotaUsed=None):
        self.userFirstName = firstName
        self.userLastName = lastName
        self.userDisplayName = "%s %s" % (firstName, lastName)
        self.userEmail = userEmail
        self.userQuota = userQuota
        self.isRole = False
        self.userLastLogin = userLastLogin
        self.userTosAcceptDatetime = userTosAcceptDatetime
        self.userAttributes = []
        self.salt
        self.password = None
        if userId is not None:
            self.userId = userId
        if userQuotaUsed is not None:
            self.userQuotaUsed = userQuotaUsed

    
    def get_copy(self):
        cUser = User(self.userFirstName, self.userLastName, self.userEmail, self.userQuota, self.userLastLogin, self.userTosAcceptDatetime, self.userId, self.userQuotaUsed)
        return cUser
    
    def get_dict(self):
        return {'userFirstName':self.userFirstName, 'userLastName':self.userLastName, 'userDisplayName': self.userDisplayName, 'userEmail': self.userEmail, 'isRole': self.isRole, 'isAdmin': self.isAdmin, 'userId': self.userId, 'userQuotaUsed': self.userQuotaUsed, 'userQuota': self.userQuota}
    
    def __str__(self):
        return "First Name: %s Last Name: %s Display Name: %s Email: %s Quota: %s Last Login: %s TOS Accept Time: %s" % (self.userFirstName, self.userLastName, self.userDisplayName, self.userEmail, self.userQuota, self.userLastLogin, self.userTosAcceptDatetime)