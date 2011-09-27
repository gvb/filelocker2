import os
import cherrypy
import logging
from lib.Formatters import strip_tags
from Cheetah.Template import Template
__author__="wbdavis"
__date__ ="$Sep 25, 2011 9:36:30 PM$"
class AdminController:
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_all_users(self, start=0, length=50, format="json", **kwargs):
        user, fl, flUserList, sMessages, fMessages = cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], None, [], []
        try:
            start, length = int(strip_tags(start)), int(strip_tags(length))
            flUsers = fl.get_all_users(user, start, length)
            flUserList = []
            for user in flUsers:
                flUserList.append(user.get_dict())
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        except Exception, e:
            fMessages.append("Problem getting users: %s" % str(e))
        return fl_response(sMessages, fMessages, format, data=flUserList)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_user_permissions(self, userId, format="json", **kwargs):
        user, fl, sMessages, fMessages, permissionData = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [], [])
        try:
            if user.userId == userId or fl.check_admin(user): #To prevent user enumeration attacks
                userPermissions, groupPermissions = fl.get_user_permissions(userId)
                allPermissions = fl.get_all_permissions(user)
                for permission in allPermissions:
                    for gPerm in groupPermissions:
                        if gPerm.permissionId == permission.permissionId:
                            permissionData.append({'permissionId': permission.permissionId, 'permissionName': permission.permissionName, 'inheritedFrom': "(group) %s" % gPerm.inheritedFrom})
                            break
                    for uPerm in userPermissions:
                        if uPerm.permissionId == permission.permissionId:
                            permissionData.append({'permissionId': permission.permissionId, 'permissionName': permission.permissionName, 'inheritedFrom': "user"})
                            break
                    else:
                        permissionData.append({'permissionId': permission.permissionId, 'permissionName': permission.permissionName, 'inheritedFrom': ""})
            else:
                fMessages.append("You do not have permission to view permissions for this user")
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format, data=permissionData)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def create_user(self, userId, firstName, lastName, email, quota, isRole, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            try:
                quota = int(quota)
            except Exception, e:
                fMessages.append("Invalid number entered for quota. Quota set to 0.")
                quota = 0
            userId, firstName, lastName, email, quota = strip_tags(userId), strip_tags(firstName), strip_tags(lastName), strip_tags(email), quota
            newUser = User(firstName, lastName, email, quota, None, None, userId)
            password = None
            if kwargs.has_key("password"):
                password = kwargs['password']
            fl.create_user(user, newUser, password)
            if isRole == "yes":
                fl.make_role(user, newUser.userId)
            sMessages.append("Created user %s (%s)" % (newUser.userDisplayName, newUser.userId))
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def bulk_create_user(self, quota, password, permissions, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            permissions = split_list_sanitized(permissions)
            line = cherrypy.request.body.readline()
            count = 0
            while line != "":
                (userId, userFirstName, userLastName, userEmailAddress) = split_list_sanitized(line)
                if fl.get_user(userId) is None:
                    newUser = User(userFirstName, userLastName, userEmailAddress.replace("\n",""), quota, None, None, userId)
                    fl.create_user(user, newUser, password)
                    for permission in permissions:
                        fl.grant_user_permission(user, userId, permission)
                    count = count + 1
                else:
                    fMessages.append("User %s already exists." % userId)
                line = cherrypy.request.body.readline()
            if len(fMessages) == 0:
                sMessages.append("Created %s users" % count)
        except ValueError, ve:
            fMessages.append("CSV file not parsed correctly, possibly in wrong format.")
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def download_user_data(self):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            userList = fl.get_all_users(user, None, None)
            mycsv = ""
            for flUser in userList:
                mycsv = mycsv + flUser.userId + ", " + flUser.userFirstName + ", " + flUser.userLastName + ", " + flUser.userEmail + "\n"
            response = cherrypy.response
            response.headers['Cache-Control'] = "no-cache"
            response.headers['Content-Disposition'] = '%s; filename="%s"' % ("attachment", "fileLockerUsers.csv")
            response.headers['Content-Type'] = "application/x-download"
            response.headers['Pragma']="no-cache"
            response.body = mycsv
            response.headers['Content-Length'] = len(response.body[0])
            response.stream = True
            return response.body
        except Exception, e:
            fMessages.append("Error creating CSV of all users.")
            logging.error("Error: %s" % str(e))
            raise HTTPError(500, "Unable to serve user data CSV: %s" % str(e))

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def make_user_role(self, roleUserId, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            fl.make_role(user, roleUserId)
            sMessages.append("Successfully created a role for user %s. Other users who are granted the permission to assume this role may act on behalf of this user now." % str(roleUserId))
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def delete_user_role(self, roleUserId, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            fl.delete_role(user, roleUserId)
            sMessages.append("Successfully deleted the role aspect for user %s." % str(roleUserId))
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def grant_user_permission(self, userId, permissionId, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            fl.grant_user_permission(user, userId, permissionId)
            sMessages.append("User %s granted permission %s" % (userId, permissionId))
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def revoke_user_permission(self, userId, permissionId, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            fl.revoke_user_permission(user, userId, permissionId)
            sMessages.append("User permission revoked")
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def update_filelocker_user(self, userId, quota, email, firstName, lastName, password, confirmPassword, isRole, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            userId = strip_tags(userId)
            updateUser = fl.get_user(userId)
            try:
                newQuota = int(strip_tags(quota))
                updateUser.userQuota = newQuota
            except Exception, e:
                fMessages.append("Invalid quota entered: Quota must be a valid integer greater than 0")
            updateUser.userEmail = strip_tags(email)
            updateUser.userFirstName = strip_tags(firstName)
            updateUser.userLastName = strip_tags(lastName)
            if isRole == "yes":
                fl.make_role(user, userId) #Since this is more a function of making a permission, not updating the user
            else:
                fl.delete_role(user, userId)
            if password != "" and password != None and confirmPassword != "" and confirmPassword != None:
                if password == confirmPassword:
                    fl.update_user(user, updateUser, password)
                    sMessages.append("Successfully updated user settings")
                else:
                    fMessages.append("Passwords do not match")
            else:
                fl.update_user(user, updateUser)
                sMessages.append("Successfully updated user settings")
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        except Exception, e:
            fMessages.append("Problem while updating user object: %s" % str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_vault_usage(self, format="json", **kwargs):
        user, fl, sMessages, fMessages, vaultUsedMB, vaultCapacityMB = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [], 0, 0)
        try:
            vaultSpaceFreeMB, vaultCapacityMB = fl.get_vault_usage()
            vaultUsedMB = vaultCapacityMB - vaultSpaceFreeMB
        except FLError, fle:
            logging.error("[%s] [getVaultUsage] [Error while getting quota: %s]" % (user.userId,str(fle.failureMessages)))
            fMessages.extend(fle.failureMessages)
            sMessages.extend(fle.successMessages)
        return fl_response(sMessages, fMessages, format, data={'vaultCapacityMB': vaultCapacityMB , 'vaultUsedMB': vaultUsedMB})

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def delete_users(self, userIds, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        userIds = split_list_sanitized(userIds)
        try:
            for userId in userIds:
                try:
                    fl.delete_user(user, userId)
                    sMessages.append("Successfully deleted user %s" % userId)
                except FLError, fle:
                    sMessages.extend(fle.successMessages)
                    fMessages.extend(fle.failureMessages)
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        except Exception, e:
            fMessages.append("Unable to delete user: %s" % str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def update_local_directory_user(self, userId, firstName, lastName, email, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        password = None
        if kwargs.has_key("password"):
            password = kwargs['password']
        try:
            userId, firstName, lastName, email = strip_tags(userId), strip_tags(firstName), strip_tags(lastName), strip_tags(email)
            updateUser = User(firstName, lastName, email, None, None, None, userId)
            fl.update_local_user(user, updateUser, password)
            sMessags.append("Updated user %s" % userId)
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        except Exception, e:
            fMessages.append("Unable to update user: %s" % str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def update_server_config(self, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        configParameterList = []
        try:
            for key in kwargs:
                if key.startswith("config_name_"):
                    parameterName = key[12:]
                    description = kwargs['config_desc_%s' % parameterName]
                    if parameterName.endswith("pass"): #Don't strip characters from passwords
                        value = kwargs[key]
                    else:
                        value = strip_tags(kwargs[key])
                    parameter = Parameter(parameterName, description, None, value) #Type won't change, don't need to store or set
                    configParameterList.append(parameter)
            fl.update_config(user, configParameterList)
            for fl_instance in cherrypy.FLThreads:
                fl_instance['app'] = None
                fl_instance['app'] = Filelocker(cherrypy.request.app.config)
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        except Exception, e:
            fMessages.append("Unable to update config: %s" % str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def update_config_password(self, parameter, password, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        parameterName = parameter
        try:
            configParameterList = [Parameter(parameterName,None, "text", password),]
            fl.update_config(user, configParameterList)
            sMessages.append("Password parameter %s updated." % parameterName)
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        except Exception, e:
            fMessages.append("Unable to update config: %s" % str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def create_attribute(self, attributeName, attributeId, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            attributeName = strip_tags(attributeName)
            attributeId = strip_tags(attributeId)
            if attributeId is None or attributeId == "":
                fMessages.append("You must specify an ID for an attribute")
            elif attributeName is None or attributeName == "":
                fMessages.append("You must give this attribute a name")
            else:
                newAttribute = Attribute(attributeId, attributeName)
                fl.create_attribute(user, newAttribute)
                sMessages.append("Successfully created a new attribute")
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        except Exception, e:
            fMessages.append("Unable to create attribute: %s" % str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def delete_attributes(self, attributeIds, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            attributeIdList = split_list_sanitized(attributeIds)
            for attributeId in attributeIdList:
                fl.delete_attribute(user, strip_tags(attributeId))
                sMessages.append("Successfully deleted attribute: %s" % attributeId)
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        except Exception, e:
            fMessages.append("Unable to delete attribute: %s" % str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_template_text(self, templateName, format="json", **kwargs):
        user, fl, sMessages, fMessages, templateText = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [], "")
        try:
            if fl.check_admin(user):
                templateName = strip_tags(templateName)
                templateFilePath = fl.get_template_file(templateName)
                templateFile = open(templateFilePath)
                templateText = templateFile.read()
            else:
                raise FLError(False, ["You do not have permission to view or edit template files."])
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        except Exception, e:
            fMessages.append("Unable to load template text: %s" % str(e))
        return fl_response(sMessages, fMessages, format, data=templateText)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def save_template(self, templateName, templateText, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            templateName = strip_tags(templateName)
            fl.save_custom_template(user, templateName, templateText)
            sMessages.append("Successfully saved custom template file")
            templateFile = open(fl.get_template_file(templateName))
            templateText = templateFile.read()
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        except Exception, e:
            fMessages.append("Unable to save template text: %s" % str(e))
        return fl_response(sMessages, fMessages, format, data=templateText)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def revert_template(self, templateName, format="json", **kwargs):
        user, fl, sMessages, fMessages, templateText = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [], "")
        try:
            templateName = strip_tags(templateName)
            fl.delete_custom_template(user, templateName)
            sMessages.append("Successfully reverted template file %s to original." % templateName)
            templateFile = open(fl.get_template_file(templateName))
            templateText = templateFile.read()
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        except Exception, e:
            fMessages.append("Unable to save template text: %s" % str(e))
        return fl_response(sMessages, fMessages, format, data=templateText)
    
if __name__ == "__main__":
    print "Hello";