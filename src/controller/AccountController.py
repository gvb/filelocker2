import cherrypy
import datetime
import logging
from twisted.plugin import getPlugins, IPlugin
from lib.SQLAlchemyTool import session
from Cheetah.Template import Template
from lib.Formatters import *
from lib.Models import *
from directory import *
import plugins
__author__="wbdavis"
__date__ ="$Sep 25, 2011 9:37:17 PM$"

class AccountController:
    @cherrypy.expose
    @cherrypy.tools.requires_login(permission="admin")
    def create_user(self, userId, firstName, lastName, email, quota, isRole, format="json", **kwargs):
        sMessages, fMessages = ([], [])
        try:
            newUser = User(userId=strip_tags(userId), firstName=strip_tags(firstName), lastName=strip_tags(lastName), email=strip_tags(email), quota=int(quota))
            if kwargs.has_key("password"):
                newUser.set_password(kwargs['password'])
            session.add(newUser)
            session.commit()
            sMessages.append("Created user %s (%s)" % (newUser.display_name, newUser.id))
        except ValueError:
                fMessages.append("Invalid number entered for quota. Quota set to 0.")
        except Exception, e:
            logging.error("Could not create user acount with ID:%s - %s" % (userId, str(e)))
            fMessages.append("Could not create user acount: %s" % str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def update_user(self, format="json", **kwargs):
        user, sMessages, fMessages = cherrypy.session.get("user"), [], []
        try:
            currentUser = get_user(user.id) #This kind of implicitly enforces permissions
            if kwargs.has_key("password") and kwargs.has_key("confirmPassword"):
                if kwargs['password'] != kwargs['confirmPassword']:
                    fMessages.append("Passwords do match. Please retype your new password")
                elif kwargs['password'] != None and kwargs['password'] != "":
                    currentUser.set_password(kwargs['password'])
                    sMessages.append("Password successfully changed")
                else:
                    fMessages.append("Password cannot be blank")
            if kwargs.has_key("emailAddress"):
                currentUser.email = kwargs["emailAddress"]
                sMessages.append("Email address successfully updated")
            if kwargs.has_key("firstName") and strip_tags(kwargs['firstName']) is not None:
                currentUser.first_name = strip_tags(kwargs['firstName'])
            if kwargs.has_key("lastName") and strip_tags(kwargs['lastName']) is not None:
                currentUser.first_name = strip_tags(kwargs['lastName'])
            session.commit()
        except Exception, e:
            fMessages.append(str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def create_group(self, groupName, groupMemberIds=None, groupScope="private", format="json", **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"), [], [])
        try:
            scope = strip_tags(groupScope.lower()) if strip_tags(groupScope) is not None else "private"
            group = Group(name=strip_tags(groupName), scope=scope, owner_id=user.id)
            session.add(group)
            memberIds = split_list_sanitized(groupMemberIds)
            for memberId in memberIds:
                try:
                    member = session.query(User).filter(User.id==memberId).one()
                    group.members.append(member)
                except sqlalchemy.orm.exc.NoResultFound:
                    fMessages.append("Could not find user with id:\"%s\" to add to group" % str(memberId))
            session.commit()
        except Exception, e:
            session.rollback()
            fMessages.append("Could not create group: %s" % str(e))
            logging.error("[%s] [create_group] [Couldn't create group: %s]" % (user.id, str(e)))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.tools.requires_login()
    @cherrypy.expose
    def delete_groups(self, groupIds, format="json", **kwargs):
        user, sMessages, fMessages  = (cherrypy.session.get("user"),  [], [])
        try:
            groupIds = split_list_sanitized(groupIds)
            for groupId in groupIds:
                group = session.query(Group).filter(Group.id==groupId).one()
            groupName = fl.delete_group(user, groupId)
            sMessages.append("Group %s deleted successfully" % groupName)
        except sqlalchemy.orm.exc.NoResultFound, nrf:
            fMessages.append("Could not find group with ID: %s" % str(groupId))
        except Exception, e:
            session.rollback()
            fMessages.append("Could not delete groups: %s" % str(e))
            logging.error("[%s] [remove_users_from_group] [Could not delete groups: %s]" % (user.id, str(e)))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.tools.requires_login()
    @cherrypy.expose
    def update_group(self, groupId, groupName=None, groupScope="private", format="json", **kwargs):
        user, sMessages, fMessages  = (cherrypy.session.get("user"), [], [])
        try:
            groupId = strip_tags(groupId)
            group = session.query(Group).filter(Group.id == groupId).one()
            if group.owner_id == user.id or user_has_permission(user, "admin"):
                group.name = strip_tags(groupName) if strip_tags(groupName) is not None else group.name
                group.scope = strip_tags(groupScope.lower()) if groupScope is not None else group.scope
                session.commit()
                sMessages.append("Group updated")
            else:
                fMessages.append("You do not have permission to update this group")
        except sqlalchemy.orm.exc.NoResultFound, nrf:
            fMessages.append("Could not find group with ID: %s" % str(groupId))
        except Exception, e:
            session.rollback()
            logging.error("[%s] [update_group] [Couldn't update group: %s]" % (user.id, str(e)))
            fMessages.append("Could not update group: %s" % str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.tools.requires_login()
    @cherrypy.expose
    def remove_users_from_group(self, userId, groupId, format="json", **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"), [], [])
        try:
            userIds = split_list_sanitized(userIds)
            groupId = int(strip_tags(groupId))
            group = session.query(Group).filter(Group.id==groupId).one()
            if group.owner_id == user.id or user_has_permission(user, "admin"):
                for userId in userIds:
                    user = AccountController.get_user(userId)
                    group.remove(user)
                session.commit()
                sMessages.append("Group members removed successfully")
            else:
                fMessages.append("You do not have permission to modify group with ID:%s" % str(groupId))
        except ValueError:
            fMessages.append("Invalid group Id")
        except sqlalchemy.orm.exc.NoResultFound, nrf:
            fMessages.append("Group with ID:%s could not be found" % str(groupId))
        except Exception, e:
            session.rollback()
            fMessages.append("Couldn't remove members from group: %s" % str(e))
            logging.error("[%s] [remove_users_from_group] [Couldn't remove members from group: %s]" % (user.id, str(e)))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def add_users_to_group(self, userId, groupId, format="json", **kwargs):
        user, sMessages, fMessages  = (cherrypy.session.get("user"), [], [])
        try:
            userIds = split_list_sanitized(userIds)
            groupId = int(strip_tags(groupId))
            group = session.query(Group).filter(Group.id == groupId).one()
            if group.owner_id == user.id or user_has_permission(user, "admin"):
                try:
                    for userId in userIds:
                        user = get_user(userId)
                        group.members.append(user)
                    session.commit()
                except sqlalchemy.orm.exc.NoResultFound, nrf:
                    fMessages.append("Invalid user ID: %s, not added to group" % str(userId))
            else:
                fMessages.append("You do not have permission to modify group with ID:%s" % str(group.id))
        except ValueError:
            fMessages.append("Invalid group Id")
        except sqlalchemy.orm.exc.NoResultFound, nrf:
            fMessages.append("Group with ID:%s could not be found" % str(groupId))
        except Exception, e:
            session.rollback()
            logging.error("[%s] [add_users_to_group] [Couldn't add members to group: %s]" % (user.id, str(e)))
            fMessages.append(str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_groups(self, format="json"):
        user, sMessages, fMessages = (cherrypy.session.get("user"),  [], [])
        try:
            groups = session.query(Group).filter(Group.owner_id==user.id).all()
            if format == "cli":
                groupsXML = ""
                for group in groups:
                    groupsXML += "<group id='%s' name='%s'></group>" % (group.id, group.name)
                groups = groupsXML
        except Exception, e:
            fMessages.append("Could not get groups: %s" % str(e))
        return fl_response(sMessages, fMessages, format, data=groups)

    def get_group_members(self, groupId, **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"),  [], [])
        try:
            searchWidget = get_search_widget("manage_groups")
            templateFile = fl.get_template_file('view_group.tmpl')
                groupId = strip_tags(groupId)
            group = session.query(Group).filter(Group.id == groupId).one()
            if group.owner_id == user.id or user_has_permission(user, "admin"):
                pass
        except Exception, e:
            pass
        tpl = Template(file=get_template_file('files.tmpl'), searchList=[locals(),globals()])
        return str(tpl)
    @cherrypy.expose
    @cherrypy.tools.requires_login(permission="admin")
    def create_role(self, roleId, roleName, email, quota, format="json", **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"), [], [])
        try:
            roleId = strip_tags(roleId)
            existingRole = session.query(Role).filter(Role.id == roleId).scalar()
            if existingRole is None:
                newRole = Role(name=strip_tags(roleName), email=strip_tags(email), quota=int(quota))
                session.add(newRole)
                session.commit()
                sMessages.append("Successfully created a role named %s. Other users who are added to this role may act on behalf of this role now." % str(roleName))
            else:
                fMessages.append("A role with role ID: %s already exists" % str(roleId))
        except ValueError:
            fMessages.append("Quota must be a positive integer")
        except Exception, e:
            session.rollback()
            logging.error("[%s] [create_role] [Problem creating role: %s]" % (user.id, str(e)))
            fMessages.append("Problem creating role: %s" % str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login(permission="admin")
    def update_role(self, roleId, roleName, email, quota, format="json", **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"), [], [])
        try:
            roleId, roleName, email, quota = strip_tags(roleId), strip_tags(roleName), strip_tags(email), int(quota)
            updateRole = session.query(Role).filter(Role.id==roleId).one()
            updateRole.email = email
            updateRole.name = roleName
            updateRole.quota = quota
            session.commit()
            sMessages.append("Successfully updated role %s" % str(roleName))
        except sqlalchemy.orm.exc.NoResultFound:
            fMessages.append("The role ID: %s does not exist" % str(roleId))
        except ValueError:
            fMessages.append("Quota must be a positive integer")
        except Exception, e:
            session.rollback()
            logging.error("[%s] [update_role] [Problem updating role: %s]" % (user.id, str(e)))
            fMessages.append("Problem updating role: %s" % str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login(permission="admin")
    def delete_role(self, roleId, format="json", **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"), [], [])
        try:
            role = session.query(Role).filter(Role.id == roleId).one()
            sMessages.append("Successfully deleted the role aspect for user %s." % str(roleUserId))
        except sqlalchemy.orm.exc.NoResultFound:
            fMessages.append("The role ID: %s does not exist" % str(roleId))
        except Exception, e:
            session.rollback()
            logging.error("[%s] [delete_role] [Problem deleting role: %s]" % (user.id, str(e)))
            fMessages.append("Problem deleting role: %s" % str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def switch_roles(self, roleUserId=None, format="json", **kwargs):
        user = cherrypy.session.get("user")
        try:
            if roleUserId is None:
                cherrypy.session['current_role'] = None
            else:
                for role in user.roles:
                    if role.id == roleUserId:
                        cherrypy.session['current_role'] = role
                        sMessages.append("Switched to role %s" % role.name)
                        break
                    fMessages.append("You are not a member of this role")
        except Exception, e:
            fMessages.append("Unable to switch roles: %s" % str(e))
            logging.error("Error switching roles: %s" % str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_search_widget(self, context, **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"), [], [])
        groups = session.query(User).filter(User.id==user.id).one().groups
        userShareableAttributes = get_shareable_attributes_by_user(user)
        tpl = Template(file=get_template_file('search_widget.tmpl'), searchList=[locals(),globals()])
        return str(tpl)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def search_users(self, firstName=None, lastName=None, userId=None, format="json", external="false", **kwargs):
        config = cherrypy.request.app.config['filelocker']
        user, foundUsers, sMessages, fMessages, tooManyResults = (cherrypy.session.get("user"),[], [], [], False)
        external = False if external.lower() != "true" else True
        try:
            if firstName is not None or lastName is not None or userId is not None: #Must have something to search on
                firstName = strip_tags(firstName)
                lastName = strip_tags(lastName)
                userId = strip_tags(userId)
                directory = ExternalDirectory(config)
                foundUsers = directory.get_user_matches(firstName, lastName, userId)
            else:
                fMessages.append("Please specify the first name, last name, or username of the user for whom you are searching")
        except Exception, e:
            if str(e)=="toomany":
                tooManyResults = True
            else:
                logging.error("[%s] [search_users] [Errors during directory search: %s]" % (user.id, str(fMessages)))
                fMessages.append(str(e))

        if format=="autocomplete":
            shareLinkList = []
            if len(fMessages) > 0:
                shareLinkList.append({'value': 0, 'label': ""})
                if tooManyResults:
                    fMessages = [] #no need for a failure message on too many results, that'll display in result window
                sMessage = ["Got users"] #We don't need to flash a success message every time a search completes
            else:
                for foundUser in foundUsers:
                    shareLinkList.append({'value': foundUser.id, 'label': foundUser.display_name})
            return fl_response(sMessages, fMessages, "json", data=shareLinkList) #This is kind of a hack since autocomplete requires a unique data structure, eventually we may be able to move this to the formatter
        else:
            return fl_response(sMessages, fMessages, format, data=foundUsers)
        

#    Ideally this won't be needed anymore
#    @cherrypy.expose
#    @cherrypy.tools.requires_login()
#    def get_group_members(self, groupId, format="searchbox_html", **kwargs):
#        user, fl = (cherrypy.session.get("user"), cherrypy.thread_data.flDict['app'])
#        group = fl.get_group(user, groupId)
#        searchWidget = HTTP_User.get_search_widget(HTTP_User(), "manage_groups")
#        templateFile = fl.get_template_file('view_group.tmpl')
#        tpl = Template(file=templateFile, searchList=[locals(),globals()])
#        return str(tpl)



class ExternalDirectory(object):
    directory = None
    def __init__(self, config):
        directoryType = config['directory_type']
        if directoryType == "ldap":
            self.directory = LDAPDirectory.LDAPDirectory(config)
        elif directoryType == "local":
            from directory import LocalDirectory
            self.directory = LocalDirectory.LocalDirectory()
    def lookup_user(self, userId):
        return self.directory.lookup_user(userId)
    def authenticate(self, username, password):
        return self.directory.authenticate(username, password)
    def get_user_matches(self, firstname, lastname, userId):
        return self.directory.get_user_matches(firstname, lastname, userId)

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
    config = cherrypy.request.app.config['filelocker']
    warnings.simplefilter("ignore")
    user = session.query(User).filter(User.id==userId).scalar()
    if user is None and config['auth_type']!="local": #This would be silly if we are using local auth, there's no other source of user info
        directory = ExternalDirectory(config)
        user = directory.lookup_user(userId)
        if user is not None:
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

def setup_session(user):
    cherrypy.session['user'] = user
    cherrypy.session['current_role'] = None
    cherrypy.session['sMessages'] = []
    cherrypy.session['fMessages'] = []

if __name__ == "__main__":
    print "Hello";