import Filelocker
import os
import cherrypy
import logging
from lib.SQLAlchemyTool import session
import sqlalchemy
from lib.Models import *
import FileController
from lib.Formatters import *
from Cheetah.Template import Template
__author__="wbdavis"
__date__ ="$Sep 25, 2011 9:36:30 PM$"

class AdminController:
    
    @cherrypy.expose
    @cherrypy.tools.requires_login(permission="admin")
    def get_permissions(self, format="json", **kwargs):
        user, sMessages, fMessages, permissionData = (cherrypy.session.get("user"),[], [], [])
        try:
            permissions = session.query(Permission).all()
            for permission in permissions:
                permissionData.append({'permissionId': permission.id, 'permissionName': permission.name, 'inheritedFrom': ""})
            sMessages.append("Got permissions")
        except Exception, e:
            logging.error("%s] [] [Couldn't get permissions: %s]" % (user.id, str(e)))
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
                mycsv = mycsv + str(flUser.id) + ", " + str(flUser.first_name) + ", " + str(flUser.last_name) + ", " + str(flUser.email) + "\n"
            response = cherrypy.response
            response.headers['Cache-Control'] = "no-cache"
            response.headers['Content-Disposition'] = '%s; filename="%s"' % ("attachment", "FileockerUsers.csv")
            response.headers['Content-Type'] = "application/x-download"
            response.headers['Pragma']="no-cache"
            response.body = mycsv
            response.headers['Content-Length'] = len(response.body[0])
            response.stream = True
            return response.body
        except Exception, e:
            logging.error("[%s] [download_user_data] [Unable to serve user data CSV: %s]" % (user.id, str(e)))
            raise cherrypy.HTTPError(500, "Unable to serve user data CSV: %s" % str(e))

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
    def get_template_text(self, templateName, format="json", **kwargs):
        user, sMessages, fMessages, templateText = (cherrypy.session.get("user"), [], [], "")
        try:
            templateName = strip_tags(templateName)
            templateFilePath = get_template_file(templateName)
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
            templateFile = open(get_template_file(templateName))
            templateText = templateFile.read()
            sMessages.append("Successfully reverted template file %s to original." % templateName)
        except Exception, e:
            logging.error("[%s] [revert_template] [Unable to revert template text: %s]" % (user.id, str(e)))
            fMessages.append("Unable to revert template text: %s" % str(e))
        return fl_response(sMessages, fMessages, format, data=templateText)
    
if __name__ == "__main__":
    print "Hello";