import Filelocker
import os
import cherrypy
import logging
from lib.Formatters import *
from Cheetah.Template import Template
__author__="wbdavis"
__date__ ="$Sep 25, 2011 9:36:30 PM$"

class AdminController:
    @cherrypy.expose
    @cherrypy.tools.requires_login(permission="admin")
    def get_all_users(self, start=0, length=50, format="json", **kwargs):
        user, sMessages, fMessages = cherrypy.session.get("user"), [], []
        try:
            start, length = int(strip_tags(start)), int(strip_tags(length))
            flUserQuery = session.query(User)
            if (length is not None):
                flUserQuery = flUserQuery.limit(length)
            if (start is not None and start > 0):
                flUserQuery = flUserQuery.offset(start)
            flUsers = flUserQuery.all()
        except Exception, e:
            fMessages.append("Problem getting users: %s" % str(e))
        return fl_response(sMessages, fMessages, format, data=flUsers)

    @cherrypy.expose
    @cherrypy.tools.requires_login(permission="admin")
    def get_user_permissions(self, userId, format="json", **kwargs):
        sMessages, fMessages, permissionData = ([], [], [])
        try:
            userId = strip_tags(userId)
            flUser = session.query(User).filter(User.id == userId).one()
            for permission in flUser.permissions:
                permissionData.append({'permissionId': permission.id, 'permissionName': permission.name, 'inheritedFrom': "user"})
            for group in flUser.groups:
                permissionData.append({'permissionId': permission.id, 'permissionName': permission.name, 'inheritedFrom': "(group) %s" % group.name})
            else:
                fMessages.append("You do not have permission to view permissions for this user")
        except sqlalchemy.orm.exc.NoResultFound:
            fMessages.append("The user ID: %s does not exist" % str(userId))
        except Exception, e:
            logging.error("Couldn't get permissions for user %s: %s" % (userId, str(e)))
            fMessages.append("Could not get permissions: %s" % str(e))
        return fl_response(sMessages, fMessages, format, data=permissionData)

    @cherrypy.expose
    @cherrypy.tools.requires_login(permission="admin")
    def bulk_create_user(self, quota, password, permissions, format="json", **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"),[], [])
        try:
            permissions = split_list_sanitized(permissions)
            line = cherrypy.request.body.readline()
            count = 0
            while line != "":
                (userId, userFirstName, userLastName, userEmailAddress) = split_list_sanitized(line)
                if session.query(User).filter(User.id==userId).scalar() is None:
                    newUser = User(first_name=userFirstName, last_name=userLastName, email=userEmailAddress.replace("\n",""), quota=quota, id=userId)
                    newUser.set_password(password)
                    session.add(newUser)
                    for permissionId in permissions:
                        permission = session.query(Permission).filter(Permission.id==permissionId).one()
                        newUser.permissions.append(permission)
                    session.commit()
                    count = count + 1
                else:
                    fMessages.append("User %s already exists." % userId)
                line = cherrypy.request.body.readline()
            if len(fMessages) == 0:
                sMessages.append("Created %s users" % count)
        except ValueError, ve:
            fMessages.append("CSV file not parsed correctly, possibly in wrong format.")
        except Exception, e:
            logging.error("[%s] [bulk_create_user] [Problem creating users in bulk: %s]" % (user.id, str(e)))
            fMessages.append("Problem creating users in bulk: %s" % str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login(permission="admin")
    def download_user_data(self):
        user = cherrypy.session.get("user")
        try:
            userList = session.query(User).all()
            mycsv = ""
            for flUser in userList:
                mycsv = mycsv + flUser.id + ", " + flUser.first_name + ", " + flUser.last_name + ", " + flUser.email + "\n"
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
            logging.error("[%s] [download_user_data] [Unable to serve user data CSV: %s]" % (user.id, str(e)))
            raise HTTPError(500, "Unable to serve user data CSV: %s" % str(e))
        
    @cherrypy.expose
    @cherrypy.tools.requires_login(permission="admin")
    def grant_user_permission(self, userId, permissionId, format="json", **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"), [], [])
        try:
            permission = session.query(Permission).filter(Permission.id == permissionId).one()
            try:
                flUser = session.query(User).filter(User.id == userId).one()
                flUser.permissions.append(permission)
                session.commit()
                sMessages.append("User %s granted permission %s" % (userId, permissionId))
            except sqlalchemy.orm.exc.NoResultFound:
                fMessages.append("User with ID: %s does not exist" % str(userId))
        except sqlalchemy.orm.exc.NoResultFound:
            fMessages.append("Permission with ID: %s does not exist" % str(permissionId))
        except Exception, e:
            session.rollback()
            logging.error("[%s] [grant_user_permission] [Problem granting user a permission: %s]" % (user.id, str(e)))
            fMessages.append("Problem granting a user permission: %s" % str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def revoke_user_permission(self, userId, permissionId, format="json", **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"), [], [])
        try:
            permission = session.query(Permission).filter(Permission.id == permissionId).one()
            try:
                flUser = session.query(User).filter(User.id == userId).one()
                flUser.permissions.remove(permission)
                session.commit()
                sMessages.append("User %s no longer has permission %s" % (userId, permissionId))
            except sqlalchemy.orm.exc.NoResultFound:
                fMessages.append("User with ID: %s does not exist" % str(userId))
        except sqlalchemy.orm.exc.NoResultFound:
            fMessages.append("Permission with ID: %s does not exist" % str(permissionId))
        except Exception, e:
            session.rollback()
            logging.error("[%s] [revoke_user_permission] [Problem revoking a user permission: %s]" % (user.id, str(e)))
            fMessages.append("Problem revoking a user permission: %s" % str(e))
        return fl_response(sMessages, fMessages, format)
    
    @cherrypy.expose
    @cherrypy.tools.requires_login(permission="admin")
    def update_user(self, userId, quota, email, firstName, lastName, password, confirmPassword, format="json", **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"), [], [])
        try:
            userId = strip_tags(userId)
            updateUser = get_user(userId) #This kind of implicitly enforces permissions
            updateUser.email = strip_tags(email)
            updateUser.quota = int(quota)
            updateUser.first_name = strip_tags(firstName)
            updateUser.last_name = strip_tags(lastName)
            if password != "" and password != None and confirmPassword != "" and confirmPassword != None:
                if password == confirmPassword:
                    updateUser.set_password(password)
                else:
                    fMessages.append("Passwords do not match, password has not be reset")
            sMessages.append("Successfully updated user settings")
            session.commit()
        except Exception, e:
            session.rollback()
            logging.error("[%s] [(admin)update_user] [Problem revoking a user permission: %s]" % (user.id, str(e)))
            fMessages.append("Problem while updating user object: %s" % str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login(permission="admin")
    def get_vault_usage(self, format="json", **kwargs):
        user, sMessages, fMessages, vaultUsedMB, vaultCapacityMB = (cherrypy.session.get("user"), [], [], 0, 0)
        try:
            vaultSpaceFreeMB, vaultCapacityMB = FileController.get_vault_usage()
            vaultUsedMB = vaultCapacityMB - vaultSpaceFreeMB
        except Exception, e:
            logging.error("[%s] [get_vault_usage] [Error while getting quota: %s]" % (user.id,str(e)))
            fMessages.append("Could not get vault usage: %s" % str(e))
        return fl_response(sMessages, fMessages, format, data={'vaultCapacityMB': vaultCapacityMB , 'vaultUsedMB': vaultUsedMB})

    @cherrypy.expose
    @cherrypy.tools.requires_login(permission="admin")
    def delete_users(self, userIds, format="json", **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"),  [], [])
        userIds = split_list_sanitized(userIds)
        try:
            for userId in userIds:
                try:
                    delUser = session.query(User).filter(User.id == userId).one()
                    session.delete(delUser)
                    sMessages.append("Successfully deleted user %s" % userId)
                except sqlalchemy.orm.exc.NoResultFound:
                    fMessages.append("User with ID:%s does not exist" % userId)
                except Exception, e:
                    fMessages.append("Could not delete user: %s" % str(e))
                session.commit()
        except Exception, e:
            session.rollback()
            logging.error("[%s] [(admin)delete_users] [Could not delete users: %s]" % (user.id, str(e)))
            fMessages.append("Could not delete users: %s" % str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def update_server_config(self, format="json", **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"), [], [])
        try:
            for key in kwargs:
                if key.startswith("config_name_"):
                    parameterName = key[12:]
                    description = kwargs['config_desc_%s' % parameterName]
                    value = None
                    if parameterName.endswith("pass"): #Don't strip characters from passwords
                        value = kwargs[key]
                    else:
                        value = strip_tags(kwargs[key])
                    parameter = session.query(ConfigParameter).filter(ConfigParameter.name == parameterName).one()
                    parameter.description = description
                    parameter.value = value
            session.commit()
            Filelocker.update_config(cherrypy.request.app.config)
        except Exception, e:
            session.rollback()
            logging.error("[%s] [update_server_config] [Could not update server config: %s]" % (user.id, str(e)))
            fMessages.append("Unable to update config: %s" % str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login(permission="admin")
    def create_attribute(self, attributeName, attributeId, format="json", **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"), [], [])
        try:
            attributeName, attributeId = strip_tags(attributeName), strip_tags(attributeId)
            if attributeId is None:
                fMessages.append("You must specify an ID for an attribute")
            elif attributeName is None:
                fMessages.append("You must give this attribute a name")
            else:
                attribute = Attribute(name=attributeName, id=attributeId)
                session.add(attribute)
                session.commit()
                sMessages.append("Successfully created a new attribute")
        except Exception, e:
            session.rollback()
            logging.error("[%s] [create_attribute] [Could not create attribute: %s]" % (user.id, str(e)))
            fMessages.append("Unable to create attribute: %s" % str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login(permission="admin")
    def delete_attributes(self, attributeIds, format="json", **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"), [], [])
        try:
            attributeIdList = split_list_sanitized(attributeIds)
            for attributeId in attributeIdList:
                try:
                    delAttribute = session.query(Attribute).filter(Attribute.id==attributeId).one()
                    session.delete(delAttribute)
                    sMessages.append("Successfully deleted attribute: %s" % attributeId)
                except sqlalchemy.orm.exc.NoResultFound:
                    fMessages.append("Attribute with ID: %s does not exist" % str(attributeId))
            session.commit()
        except Exception, e:
            logging.error("[%s] [delete_attributes] [Could not delete attributes: %s]" % (user.id, str(e)))
            fMessages.append("Unable to delete attribute: %s" % str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login(permission="admin")
    def get_template_text(self, templateName, format="json", **kwargs):
        user, sMessages, fMessages, templateText = (cherrypy.session.get("user"), [], [], "")
        try:
            templateName = strip_tags(templateName)
            templateFilePath = fl.get_template_file(templateName)
            templateFile = open(templateFilePath)
            templateText = templateFile.read()
        except Exception, e:
            logging.error("[%s] [get_template_text] [Unable to load template text: %s]" % (user.id, str(e)))
            fMessages.append("Unable to load template text: %s" % str(e))
        return fl_response(sMessages, fMessages, format, data=templateText)

    @cherrypy.expose
    @cherrypy.tools.requires_login(permission="admin")
    def save_template(self, templateName, templateText, format="json", **kwargs):
        user, sMessages, fMessages, config, templateText = (cherrypy.session.get("user"), [], [], cherrpy.request.app.config['filelocker'], "")
        try:
            templateName = strip_tags(templateName)
            filePath = os.path.join(config['vault'], "custom", templateName)
            if os.path.exists(os.path.join(config['vault'], "custom")) == False:
                os.mkdir(os.path.join(config['vault'], "custom"))
            templateFile = open(filePath, "w")
            templateFile.write(templateText)
            templateFile.close()
            sMessages.append("Successfully saved custom template file")
            templateFile = open(get_template_file(templateName))
            templateText = templateFile.read()
        except Exception, e:
            logging.error("[%s] [save_template] [Unable to save template text: %s]" % (user.id, str(e)))
            fMessages.append("Unable to save template text: %s" % str(e))
        return fl_response(sMessages, fMessages, format, data=templateText)

    @cherrypy.expose
    @cherrypy.tools.requires_login(permission="admin")
    def revert_template(self, templateName, format="json", **kwargs):
        user, sMessages, fMessages, config, templateText = (cherrypy.session.get("user"), [], [], cherrpy.request.app.config['filelocker'], None)
        try:
            templateName = strip_tags(templateName)
            filePath = os.path.join(config['vault'], "custom", templateName)
            if os.path.exists(filePath): #This causes no problems if the tempate doesn't already exist
                os.remove(filePath)
            templateFile = open(fl.get_template_file(templateName))
            templateText = templateFile.read()
            sMessages.append("Successfully reverted template file %s to original." % templateName)
        except Exception, e:
            logging.error("[%s] [revert_template] [Unable to revert template text: %s]" % (user.id, str(e)))
            fMessages.append("Unable to revert template text: %s" % str(e))
        return fl_response(sMessages, fMessages, format, data=templateText)
    
if __name__ == "__main__":
    print "Hello";