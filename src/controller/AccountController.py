import cherrypy
import logging
from twisted.plugin import getPlugins, IPlugin
from lib.SQLAlchemyTool import session
from Cheetah.Template import Template
import plugins
__author__="wbdavis"
__date__ ="$Sep 25, 2011 9:37:17 PM$"

class AccountController:

    def install_user(self, user):
        if user is not None:
            if user.quota is None:
                user.quota = int(session.query(ConfigParameter).filter(ConfigParameter.id=="default_quota").one().value)
            session.add(user)
            session.add(ActionLog(user.id, "Install User", "User %s (%s) installed" % (user.display_name, user.id)))
            session.commit()
        else:
            raise Exception("User %s doesn't exist in directory" % userId)

    def get_user(self, userId, login=False):
        import warnings
        warnings.simplefilter("ignore")
        user = session.query(User).filter(User.id==userId).one()
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
                        attr = session.query(Attribute).filter(Attribute.id=attributeId).one()
                        if attr is not None:
                            user.userAttributes.append(attr)
                        uniqueAttributeList.append(attributeId)
        return user

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def update_user(self, emailAddress, format="json", **kwargs):
        fl, user, sMessages, fMessages = cherrypy.thread_data.flDict['app'], cherrypy.session.get("user"), [], []
        updatedUserObject = User(user.userFirstName, user.userLastName, emailAddress, user.userQuota, user.userLastLogin, user.userTosAcceptDatetime, user.userId)
        try:
            if kwargs.has_key("password") and kwargs.has_key("confirmPassword"):
                if kwargs['password'] != kwargs['confirmPassword']:
                    fMessages.append("Passwords do match. Please retype your new password")
                elif kwargs['password'] != None and kwargs['password'] != "":
                    fl.reset_password(user, user.userId, kwargs['password'])
                    sMessages.append("Password successfully changed")
                else:
                    fMessages.append("Password cannot be blank")
            fl.update_user(user, updatedUserObject)
            sMessages.append("Email address successfully updated")
        except FLError, fle:
            fMessages.extend(fle.failureMessages)
            sMessages.extend(fle.successMessages)
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def switch_roles(self, roleUserId=None, format="json", **kwargs):
        user, fl= (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'])
        try:
            if roleUserId is None:
                cherrypy.session['user'] = fl.get_user(cherrypy.session.get("original_user").userId, True)
                cherrypy.session['sMessages'].append("Role reverted back to %s" % str(cherrypy.session.get("user").userId))
            elif fl.check_permission(user, "(role)%s" % roleUserId) or (cherrypy.session.has_key("original_user") and cherrypy.session.get("original_user").userId == roleUserId):
                cherrypy.session['user'] = fl.get_user(roleUserId, True)
                cherrypy.session['sMessages'].append("Role successfully changed to %s" % str(roleUserId))
            else:
                cherrypy.session['fMessages'].append("You do not have permission to switch to this role")
        except FLError, fle:
            cherrypy.session['sMessages'].extend(fle.successMessages)
            cherrypy.session['fMessages'].extend(fle.failureMessages)
        return fl_response(cherrypy.session['sMessages'], cherrypy.session['fMessages'], format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_search_widget(self, context, **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        groups = fl.get_user_groups(user, user.userId)
        userShareableAttributes = fl.get_available_attributes_by_user(user)
        tpl = Template(file=fl.get_template_file('search_widget.tmpl'), searchList=[locals(),globals()])
        return str(tpl)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def search_users(self, firstName=None, lastName=None, userId=None, format="json", external=False, **kwargs):
        user, fl, foundUsersJSON, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [], [])
        tooManyResults = False
        if external == "true":
            external = True
        else:
            external = False
        try:
            if firstName is not None or lastName is not None or userId is not None: #Must have something to search on
                if firstName == "": firstName = None
                if lastName == "": lastName = None
                if userId == "": userId = None
                if userId is not None:
                    userId = strip_tags(userId)
                if firstName is not None:
                    firstName = strip_tags(firstName)
                if lastName is not None:
                    lastName = strip_tags(lastName)
                foundUsers = fl.search_users(external, firstName, lastName, userId)
                for foundUser in foundUsers:
                    foundUsersJSON.append({"displayName": foundUser.userDisplayName, "userId": foundUser.userId})
                sMessages.append("User search complete")
            else:
                fMessages.append("Please specify the first name, last name, or username of the user for whom you are searching")
        except FLError, fle:
            if fle.partialSuccess:
                tooManyResults = True
            else:
                logging.error("[%s] [searchUsers] [Errors during directory search: %s]" % (user.userId, str(fMessages)))
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)

        if format=="json":
            return fl_response(sMessages, fMessages, format, data=foundUsersJSON)
        elif format=="autocomplete":
            shareLinkList = []
            if len(fMessages) > 0:
                shareLinkList.append({'value': 0, 'label': fMessages[-1]})
                if tooManyResults:
                    fMessages = [] #no need for a failure message on too many results, that'll display in result window
                sMessage = [] #We don't need to flash a success message every time a search completes
            else:
                for foundUser in foundUsersJSON:
                    shareLinkList.append({'value': foundUser['userId'], 'label': foundUser['displayName']})
            return fl_response(sMessages, fMessages, "json", data=shareLinkList) #This is kind of a hack since autocomplete requires a unique data structure, eventually we may be able to move this to the formatter

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def create_group(self, groupName, groupMemberIds=None, groupScope=None, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        if groupMemberIds is not None:
            groupMemberIds = split_list_sanitized(groupMemberIds)
        else:
            groupMemberIds = []
        groupName = strip_tags(groupName)
        if groupScope is not None:
            groupScope = strip_tags(groupScope)
        else:
            groupScope = "private"
        try:
            if groupName != "":
                fl.create_group(user, groupName, groupMemberIds, groupScope)
                sMessages.append("Group %s created successfully" % str(groupName))
            else:
                fMessages.append("Group name is not valid")
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)

    @cherrypy.tools.requires_login()
    @cherrypy.expose
    def delete_group(self, groupId, format="json", **kwargs):
        user, fl, sMessages, fMessages  = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        groupIdList = split_list_sanitized(groupId)
        for groupId in groupIdList:
            try:
                groupName = fl.delete_group(user, groupId)
                sMessages.append("Group %s deleted successfully" % groupName)
            except FLError, fle:
                sMessages.extend(fle.successMessages)
                fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)

    @cherrypy.tools.requires_login()
    @cherrypy.expose
    def update_group(self, groupId, users=None, groupName=None, groupScope="private", format="json", **kwargs):
        user, fl, sMessages, fMessages  = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            userIds = split_list_sanitized(users)
            groupName = strip_tags(groupName)
            if groupScope is not None:
                groupScope = strip_tags(groupScope.lower())
            fl.update_group(user, groupId, userIds, groupName, groupScope)
        except FLError, fle:
            fMessages.extend(fle.failureMessages)
            sMessages.extend(fle.successMessages)
        return fl_response(sMessages, fMessages, format)

    @cherrypy.tools.requires_login()
    @cherrypy.expose
    def remove_user_from_group(self, userId, groupId, format="json", **kwargs):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        userIds = split_list_sanitized(userId)
        for memberId in userIds:
            try:
                fl.remove_user_from_group(user, memberId, groupId)
                sMessages.append("Member %s removed successfully" % memberId)
            except FLError, fle:
                fMessages.extend(fle.failureMessages)
                sMessages.extend(fle.successMessages)
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def add_user_to_group(self, userId, groupId, format="json", **kwargs):
        user, fl, sMessages, fMessages  = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        groupIdList = split_list_sanitized(groupId)
        for groupIdFromList in groupIdList:
            try:
                fl.add_user_to_group(user, userId, groupIdFromList)
            except FLError, fle:
                sMessages.extend(fle.successMessages)
                fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_group_members(self, groupId, format="searchbox_html", **kwargs):
        user, fl = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'])
        group = fl.get_group(user, groupId)
        searchWidget = HTTP_User.get_search_widget(HTTP_User(), "manage_groups")
        templateFile = fl.get_template_file('view_group.tmpl')
        tpl = Template(file=templateFile, searchList=[locals(),globals()])
        return str(tpl)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_groups(self, format="json"):
        user, fl, sMessages, fMessages = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'], [], [])
        try:
            groups = fl.get_user_groups(user, user.userId)
            groups = sorted(groups, key=lambda k: k.groupId)
            if format == "cli":
                groupsXML = ""
                for group in groups:
                    groupsXML += "<group id='%s' name='%s'></group>" % (group.groupId, group.groupName)
                groups = groupsXML
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        yield fl_response(sMessages, fMessages, format, data=groups)


if __name__ == "__main__":
    print "Hello";