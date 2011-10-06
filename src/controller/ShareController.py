import cherrypy
import logging
from Cheetah.Template import Template
__author__="wbdavis"
__date__ ="$Sep 25, 2011 9:28:23 PM$"
class ShareController:
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def create_private_share(self, fileIds, targetId=None, groupId=None, notify="yes", format="json", **kwargs):
        user, fl, sMessages, fMessages  = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        fileIds = split_list_sanitized(fileIds)
        if targetId == "":
            targetId = None
        if targetId is not None:
            targetId = strip_tags(targetId)
        if groupId == "":
            groupId = None
        if groupId is not None:
            groupId = strip_tags(groupId)
        if notify != "yes":
            notify = False
        else:
            notify = True
        try:
            if targetId is not None:
                fl.private_share_files_user(user, fileIds, targetId, notify)
                sMessages.append("Shared file(s) successfully")
            if groupId is not None:
                fl.private_share_files_group(user, fileIds, groupId, notify)
                sMessages.append("Shared file(s) successfully")
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def create_private_attribute_shares(self, fileIds, attributeId, format="json", **kwargs):
        user, fl, sMessages, fMessages  = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            fileIds = split_list_sanitized(fileIds)
            for fileId in fileIds:
                fl.private_attribute_share_file(user, fileId, attributeId)
            sMessages.append("Successfully shared file(s) with users having the %s attribute" % attributeId )
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def delete_private_attribute_shares(self, fileIds, attributeId, format="json", **kwargs):
        user, fl, sMessages, fMessages  = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            fileIdList = split_list_sanitized(fileIds)
            for fileId in fileIdList:
                fl.delete_private_attribute_share(user, fileId, attributeId)
            sMessages.append("Successfully unshared file(s) with users having the %s attribute") % attributeId
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def create_public_share(self, fileId, expiration, shareType, notifyEmails, format="json", **kwargs):
        user, fl, sMessages, fMessages, shareId = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [], None)
        fileId = strip_tags(fileId)
        try:
            expiration = datetime.datetime(*(time.strptime(strip_tags(expiration), "%m/%d/%Y")[0:6]))
            try:
                notifyEmailList = split_list_sanitized(notifyEmails)
                password = None
                if shareType != "multi":
                    shareType = "single"
                if kwargs.has_key("password") and kwargs['password']!="":
                    password = kwargs['password']
                shareId = fl.public_share_file(user, fileId, password, expiration, shareType, notifyEmailList)
                sMessages.append("File shared successfully")
            except FLError, fle:
                sMessages.extend(fle.successMessages)
                fMessages.extend(fle.failureMessages)
        except Exception, e:
            if expiration is None or expiration == "":
                fMessages.append("Public shares must have an expiration date.")
            else:
                fMessages.append("Invalid expiration date format. Date must be in mm/dd/yyyy format.")
            logging.error("[%s] [createPublicShare] [Unable to create public share: %s]" % (user.userId, str(e)))
        return fl_response(sMessages, fMessages, format, data=shareId)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def delete_public_share(self, fileId, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        fileId = strip_tags(fileId)
        try:
            fl.delete_public_share(user, fileId)
            sMessages.append("Successfully unshared file")
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
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

def get_user_shareable_attributes(self, user):
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
            if AccountController.user_has_permission(user, attributePermissionId)
                attributeList.append(attribute)
    return attributeList

 def get_files_shared_with_user_by_attribute(user):
    attributeShareDictionary = {}
    for attributeShare in user.private_attribute_shares:
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