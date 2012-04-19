# -*- coding: utf-8 -*-
import cherrypy
import datetime
from twisted.plugin import getPlugins, IPlugin
from lib.SQLAlchemyTool import session
from lib.Formatters import *
from lib.Models import *
import plugins

__author__="wbdavis"
__date__ ="$Jan 31, 2012 3:11:02 AM$"

def user_has_permission(user, permissionId):
    #print "User Permissions: %s" % str(user.permissions)
    for permission in user.permissions:
        if permission.id == permissionId:
            return True
    for group in user.groups:
        for permission in group.permissions:
            if permission.id == permissionId:
                return True
    return False

def role_has_permission(role, permissionId):
    for permission in role.permissions:
        if permission.id == permissionId:
            return True
    return False

def install_user(self, user):
    if user is not None:
        if user.quota is None:
            user.quota = int(session.query(ConfigParameter).filter(ConfigParameter.id=="default_quota").one().value)
        session.add(user)
        session.add(AuditLog(user.id, "Install User", "User %s (%s) installed" % (user.display_name, user.id)))
        session.commit()
    else:
        raise Exception("User %s doesn't exist in directory" % userId)

def get_user(userId, login=False):
    import warnings
    authType = session.query(ConfigParameter).filter(ConfigParameter.name=="auth_type").one().value
    warnings.simplefilter("ignore")
    user = session.query(User).filter(User.id==userId).scalar()
    if user is None and authType!="local": #This would be silly if we are using local auth, there's no other source of user info
        directory = ExternalDirectory()
        user = directory.lookup_user(userId)
        if user is not None:
            if user.quota is None:
                user.quota = int(session.query(ConfigParameter).filter(ConfigParameter.id=="default_quota").one().value)
            session.add(user)
            session.commit()
    if user is not None:
        attributeList = []
        for permission in user.permissions:
            if permission.id.startswith("(attr)"):
                attributeList.append(permission.id.split("(attr)")[1])
        for group in user.groups:
            for permission in group.permissions:
                if permission.id.startswith("(attr)"):
                    attributeList.append(permission.id.split("(attr)")[1])
        if login:
            for flPlugin in getPlugins(FilelockerPlugin, plugins):
                attributeList.extend(flPlugin.get_user_attributes(user.id, self)) #Send user object off to  plugin to get the list populated
                if flPlugin.is_authorized(user.userId, self) == False: #Checks if any plugin is going to explicitly deny this user access to Filelocker
                    user.authorized = False
            uniqueAttributeList = []
            for attributeId in attributeList:
                if attributeId not in uniqueAttributeList:
                    attr = session.query(Attribute).filter(Attribute.id==attributeId).scalar()
                    if attr is not None:
                        user.attributes.append(attr)
                    uniqueAttributeList.append(attributeId)
            user.date_last_login = datetime.datetime.now()
            session.commit()
            setup_session(user.get_copy())
    if user.quota is None: #Catch for users that got added with nil quotas
        user.quota = 0
        session.commit()
    return user

def get_shareable_attributes_by_user(user):
    """
    This function gets the attributes that a user has permission to share with.

    Examples of this would be a teacher for a class being able to share with all users
    who have the class as an attribute"""
    attributeList = []
    allAttributes = session.query(Attribute).all()
    if user_has_permission(user, "admin"):
        attributeList = allAttributes
    else:
        for attribute in allAttributes:
            if user_has_permission(user, "(attr)%s" % attribute.id):
                attributeList.append(attribute)
    return attributeList

def get_shareable_attributes_by_role(role):
    """
    This function gets the attributes that a role has permission to share with.

    Examples of this would be a teacher for a class being able to share with all users
    who have the class as an attribute"""
    attributeList = []
    allAttributes = session.query(Attribute).all()
    if role_has_permission(role, "admin"):
        attributeList = allAttributes
    else:
        for attribute in allAttributes:
            if role_has_permission(role, "(attr)%s" % attribute.id):
                attributeList.append(attribute)
    return attributeList

def setup_session(user):
    cherrypy.session['user'] = user
    cherrypy.session['current_role'] = None
    cherrypy.session['sMessages'] = []
    cherrypy.session['fMessages'] = []

class ExternalDirectory(object):
    directory = None
    def __init__(self, localOverride=False):
        directoryType = session.query(ConfigParameter).filter(ConfigParameter.name=="directory_type").one().value
        if directoryType == "local" or localOverride:
            from directory import LocalDirectory
            self.directory = LocalDirectory.LocalDirectory()
        elif directoryType == "ldap":
            from directory import LDAPDirectory
            self.directory = LDAPDirectory.LDAPDirectory()
    def lookup_user(self, userId):
        return self.directory.lookup_user(userId)
    def authenticate(self, username, password):
        return self.directory.authenticate(username, password)
    def get_user_matches(self, firstname, lastname, userId):
        return self.directory.get_user_matches(firstname, lastname, userId)