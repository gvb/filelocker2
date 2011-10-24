import cherrypy
import logging
from Cheetah.Template import Template
from lib.SQLAlchemyTool import session
import AccountController
from lib.Formatters import *
from lib.Models import *
__author__="wbdavis"
__date__ ="$Sep 25, 2011 9:28:23 PM$"
class ShareController:
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def create_private_share(self, fileIds, targetId=None, groupId=None, notify="yes", format="json", **kwargs):
        user, sMessages, fMessages  = (cherrypy.session.get("user"), [], [])
        fileIds = split_list_sanitized(fileIds)
        targetId = strip_tags(targetId) if targetId is not None and targetId != "" else None
        groupId = strip_tags(groupId) if groupId is not None and groupId != "" else None
        notify = True if notify.lower() == "yes" else False
        try:
            if targetId is not None:
                for fileId in fileIds:
                    session.add(PrivateShare(user_id=targetId, file_id=fileId))
                sMessages.append("Shared file(s) successfully")
            if groupId is not None:
                for fileId in fileIds:
                    session.add(PrivateGroupShare(group_id=groupId, file_id=fileId))
                sMessages.append("Shared file(s) successfully")
        except Exception, e:
            fMessages.append(str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def create_private_attribute_shares(self, fileIds, attributeId, format="json", **kwargs):
        user, sMessages, fMessages  = (cherrypy.session.get("user"), [], [])
        try:
            userShareableAttributes, permission = AccountController.get_shareable_attributes_by_user(user), False
            for attribute in userShareableAttributes:
                if attributeId == attribute.id:
                    permission = True
                    break
            if permission:
                fileIds = split_list_sanitized(fileIds)
                for fileId in fileIds:
                    session.add(PrivateAttributeShare(file_id=fileId, attributeId=attributeId))
                sMessages.append("Successfully shared file(s) with users having the %s attribute" % attributeId )
            else:
                fMessages.append("You do not have permission to share with this attribute")
        except Exception, e:
            fMessages.append(str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def delete_private_attribute_shares(self, fileIds, attributeId, format="json", **kwargs):
        user, sMessages, fMessages  = (cherrypy.session.get("user"), [], [])
        try:
            userShareableAttributes, permission = AccountController.get_shareable_attributes_by_user(user), False
            for attribute in userShareableAttributes:
                if attributeId == attribute.id:
                    permission = True
                    break
            if permission:
                fileIdList = split_list_sanitized(fileIds)
                for fileId in fileIdList:
                    pas = session.query(PrivateAttributeShare).filter(PrivateAttributeShare.attribute_id==attributeId and PrivateAttributeShare.fileId==fileId).one()
                    session.delete(pas)
                sMessages.append("Successfully unshared file(s) with users having the %s attribute") % attributeId
            else:
                fMessages.append("You do not have permission to delete attribute shares for this attribute")
        except Exception, e:
            fMessages.append(str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def create_public_share(self, fileId, expiration, shareType, notifyEmails, format="json", **kwargs):
        user, sMessages, fMessages, shareId = (cherrypy.session.get("user"), [], [], None)
        fileId = strip_tags(fileId)
        try:
            flFile = session.query(File).filter(File.id==fileId).one()
            try:
                expiration = datetime.datetime(*(time.strptime(strip_tags(expiration), "%m/%d/%Y")[0:6]))
            except Exception, e:
                raise Exception("Invalid expiration date format. Date must be in mm/dd/yyyy format.")
            if expiration is None or expiration == "":
                raise Exception("Public shares must have a valid expiration date")
            if flFile.owner_id == user.id or AccountController.user_has_permission(user, "admin"):
                notifyEmailList = split_list_sanitized(notifyEmails)
                password = None
                if shareType != "multi":
                    shareType = "single"
                if kwargs.has_key("password") and kwargs['password']!="":
                    password = kwargs['password']
                ps = PublicShare(file_id=flFile.id, date_expires=expiration, reuse=shareType)
                ps.id = ps.generate_share_id()
                ps.set_password(password)
                session.add(ps)
                session.commit()
                sMessages.append("File shared successfully")
            else:
                fMessages.append("You do not have permission to publicly share this file")
        except Exception, e:
            fMessages.append(str(e))
            logging.error("[%s] [create_public_share] [Unable to create public share: %s]" % (user.id, str(e)))
        return fl_response(sMessages, fMessages, format, data=shareId)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def delete_public_share(self, fileId, format="json", **kwargs):
        #TODO: Public sharing has to be redone to accomodate multi-shares
        user, sMessages, fMessages = (cherrypy.session.get("user"), [], [])
        fileId = strip_tags(fileId)
        try:
            fl.delete_public_share(user, fileId)
            ps = session.query(PublicShare).all()
            sMessages.append("Successfully unshared file")
        except Exception, e:
            fMessags.append(str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def delete_share(self, fileIds, targetId=None, shareType="private", format="json"):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        shareType = strip_tags(shareType.lower())
        fileIds = split_list_sanitized(fileIds)
        for fileId in fileIds:
            flFile = fl.get_file(user, fileId)
            try:
                if shareType == "private" or shareType =="private_group":
                    if targetId is not None:
                        if shareType == "private":
                            targetName = "User not found"
                            targetUser = fl.directory.lookup_user(targetId)
                            fl.delete_private_share(user, fileId, targetId)
                            if(targetUser is not None):
                                targetName = targetUser.userDisplayName
                            sMessages.append("Successfully unshared file %s with user %s" % (flFile.fileName, targetName))
                        elif shareType == "private_group":
                            group = fl.get_group(user, targetId)
                            fl.delete_private_group_share(user, fileId, targetId)
                            sMessages.append("Successfully unshared file %s with group %s" % (flFile.fileName, group.groupName))
                    else:
                        fMessages.append("A user, group, or share ID must be specified in order to delete a share")
                elif shareType == "all":
                    fl.delete_all_shares(user, fileId)
                    sMessages.append("Successfully deleted all shares for the file %s" % flFile.fileName)
                elif shareType=="private_attribute":
                    if targetId is not None:
                        for fileId in fileIds:
                            fl.delete_private_attribute_share(user, fileId, targetId)
                        sMessages.append("Successfully unshared file(s) with users having the %s attribute" % targetId)
                    else:
                        fMessages.append("An attribute ID must be specified in order to delete a share")
                else:
                    fMessages.append("Unrecognized share type: %s" % shareType)
            except FLError, fle:
                fMessages.extend(fle.failureMessages)
                sMessages.extend(fle.successMessages)
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def unhide_all_shares(self, format="json"):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            fl.unhide_all_private_shares(user)
            sMessages.append("Successfully unhid shares")
        except FLError, fle:
            fMessages.extend(fle.failureMessages)
            sMessages.extend(fle.successMessages)
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def hide_share(self, fileIds, format="json"):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        fileIds = split_list_sanitized(fileIds)
        for fileId in fileIds:
            try:
                fl.hide_private_share(user, fileId)
                sMessages.append("Successfully hid share. Unhide shares in Account Settings.")
            except FLError, fle:
                fMessages.extend(fle.failureMessages)
                sMessages.extend(fle.successMessages)
        return fl_response(sMessages, fMessages, format)

def get_user_shareable_attributes(user):
    """
    This function gets the attributes that a user has permission to share with.

    Examples of this would be a teacher for a class being able to share with all users
    who have the class as an attribute"""
    attributeList = []
    allAttributes = session.query(Attribute).all()
    if AccountController.user_has_permission(user, "admin"):
        attributeList = allAttributes
    else:
        for attribute in allAttributes:
            attributePermissionId = "(attr)%s" % attribute.attributeId
            if AccountController.user_has_permission(user, attributePermissionId):
                attributeList.append(attribute)
    return attributeList

def get_files_shared_with_user_by_attribute(user):
    """Builds a dictionary keyed by attribute id with values that are lists of files shared by this attribute"""
    attributeShareDictionary = {}
    for attributeId in user.attributes:
        attribute = session.query(Attribute).filter(Attribute.id==attributeId).scalar() #Do this to ensure this attribute is even recognized by the system
        if attribute is not None:
            for attributeShare in session.query(PrivateAttributeShare).filter(PrivateAttributeShare.attribute_id==attribute.id).all():
                if attributeShareDictionary.has_key(attributeShare.attribute_id)==False:
                    attributeShareDictionary[attributeShare.attribute_id] = []
                attributeShareDictionary[attributeShare.attribute_id].append(attributeShare.flFile)
    return attributeShareDictionary
    
def get_files_shared_with_user_privately(user):
    fileList = []
    userShares = session.query(PrivateShare).filter(PrivateShare.user_id == user.id)
    for share in userShares:
        fileList.append(share.flFile)
    return fileList



if __name__ == "__main__":
    print "Hello";