import cherrypy
import datetime
import logging
from twisted.plugin import getPlugins, IPlugin
import sqlalchemy
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
    def create_user(self, userId, firstName, lastName, email, quota, format="json", **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"), [], [])
        try:
            newUser = User(id=strip_tags(userId), first_name=strip_tags(firstName), last_name=strip_tags(lastName), email=strip_tags(email), quota=int(quota))
            if kwargs.has_key("password") and kwargs.has_key("confirmPassword"):
                if kwargs['password'] == kwargs['confirmPassword']:
                    newUser.set_password(kwargs['password'])
                else:
                    raise Exception("Passwords do not match")
            session.add(newUser)
            session.add(AuditLog(user.id, "Create User", "You created a new user with ID:\"%s\" on the system" % newUser.id, newUser.id))
            session.commit()
            sMessages.append("Created user %s (%s)" % (newUser.display_name, newUser.id))
        except ValueError:
                fMessages.append("Invalid number entered for quota. Quota set to 0.")
        except Exception, e:
            logging.error("Could not create user account with ID:%s - %s" % (userId, str(e)))
            fMessages.append("[%s] [create_user] [Could not create user account: %s]" % (user.id, str(e)))
        return fl_response(sMessages, fMessages, format)
    
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def update_user(self, userId, quota=None, email=None, firstName=None, lastName=None, password=None, confirmPassword=None, format="json", **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"), [], [])
        try:
            userId = strip_tags(userId)
            if userId == user.id or user_has_permission(user, "admin"):
                updateUser = get_user(userId) #This kind of implicitly enforces permissions
                updateUser.email = strip_tags(email) if strip_tags(email) is not None else updateUser.email
                updateUser.quota = int(strip_tags(quota)) if strip_tags(quota) is not None else updateUser.quota
                updateUser.first_name = strip_tags(firstName) if strip_tags(firstName) is not None else updateUser.first_name
                updateUser.last_name = strip_tags(lastName) if strip_tags(lastName) is not None else updateUser.last_name
                if password != "" and password != None and confirmPassword != "" and confirmPassword != None:
                    if password == confirmPassword:
                        updateUser.set_password(password)
                    else:
                        fMessages.append("Passwords do not match, password has not be reset")
                sMessages.append("Successfully updated user settings")
                session.add(AuditLog(user.id, "User Update", "User account \"%s\" has been updated" % userId, userId))
                session.commit()
            else:
                 fMessages.append("You do not have permission to update this user")
        except Exception, e:
            session.rollback()
            logging.error("[%s] [update_user] [Problem rupdating user: %s]" % (user.id, str(e)))
            fMessages.append("Problem while updating user: %s" % str(e))
        return fl_response(sMessages, fMessages, format)

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
                    session.add(AuditLog(user.id, "Delete User", "User with ID: \"%s\" deleted from system" % delUser.id, "admin"))
                    sMessages.append("Successfully deleted user %s" % userId)
                except sqlalchemy.orm.exc.NoResultFound:
                    fMessages.append("User with ID:%s does not exist" % userId)
                except Exception, e:
                    fMessages.append("Could not delete user: %s" % str(e))
                session.commit()
        except Exception, e:
            session.rollback()
            logging.error("[%s] [delete_users] [Could not delete users: %s]" % (user.id, str(e)))
            fMessages.append("Could not delete users: %s" % str(e))
        return fl_response(sMessages, fMessages, format)
    
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
            session.add(AuditLog(user.id, "Create Group", "You created a group named \"%s\"" % group.name, None))
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
                if group.owner_id == user.id or user_has_permission(user, "admin"):
                    session.delete(group)
                    sMessages.append("Group %s deleted successfully" % group.name)
                    session.add(AuditLog(user.id, "Delete Group", "You deleted group \"%s\"" % group.name, None))
            session.commit()
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
    def remove_users_from_group(self, userIds, groupId, format="json", **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"), [], [])
        try:
            userIds = split_list_sanitized(userIds)
            groupId = int(strip_tags(groupId))
            group = session.query(Group).filter(Group.id==groupId).one()
            if group.owner_id == user.id or user_has_permission(user, "admin"):
                for userId in userIds:
                    user = get_user(userId)
                    group.members.remove(user)
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
    def add_user_to_group(self, userId, groupId, format="json", **kwargs):
        user, sMessages, fMessages  = (cherrypy.session.get("user"), [], [])
        try:
            userId = strip_tags(userId)
            groupId = int(strip_tags(groupId))
            group = session.query(Group).filter(Group.id == groupId).one()
            if group.owner_id == user.id or user_has_permission(user, "admin"):
                try:
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
    
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_group_members(self, groupId, **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"),  [], [])
        searchWidget = self.get_search_widget("manage_groups")
        groupId = strip_tags(groupId)
        group = session.query(Group).filter(Group.id == groupId).one()
        if group.owner_id == user.id or user_has_permission(user, "admin"):
            tpl = Template(file=get_template_file('view_group.tmpl'), searchList=[locals(),globals()])
            return str(tpl)
        else:
            raise cherrypy.HTTPError(413, "Not permitted")
    
    @cherrypy.expose
    @cherrypy.tools.requires_login(permission="admin")
    def create_role(self, roleId, roleName, email, quota, format="json", **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"), [], [])
        try:
            roleId = strip_tags(roleId)
            existingRole = session.query(Role).filter(Role.id == roleId).scalar()
            if existingRole is None:
                roleName = strip_tags(roleName)
                email = strip_tags(email)
                quota = int(quota)
                newRole = Role(id=roleId, name=roleName, email=email, quota=quota)
                session.add(newRole)
                session.add(AuditLog(user.id, "Add Role", "You added a role to the system named \"%s\"" % newRole.name, None))
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
            roleId = strip_tags(roleId)
            existingRole = session.query(Role).filter(Role.id == roleId).one()
            existingRole.name = strip_tags(roleName)
            existingRole.email = strip_tags(email)
            existingRole.quota = int(quota)
            session.add(AuditLog(user.id, 'Update Role', "Role \"%s\"(%s) has been updated" % (existingRole.name, existingRole.id), None, existingRole.id))
            session.commit()
            sMessages.append("Successfully updated a role named %s." % str(roleName))
        except ValueError:
            fMessages.append("Quota must be a positive integer")
        except sqlalchemy.orm.exc.NoResultFound:
            fMessages.append("Role with ID:%s could not be found to update." % str(roleId))
        except Exception, e:
            session.rollback()
            logging.error("[%s] [create_role] [Problem creating role: %s]" % (user.id, str(e)))
            fMessages.append("Problem creating role: %s" % str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login(permission="admin")
    def get_all_roles(self, roleId, roleName, email, quota, format="json", **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"), [], [])
        try:
            roles = session.query(Role).all()
            sMessages.append("Successfully fetched roles %s")
        except Exception, e:
            logging.error("[%s] [get_all_roles] [Problem getting roles: %s]" % (user.id, str(e)))
            fMessages.append("Problem getting roles: %s" % str(e))
        return fl_response(sMessages, fMessages, format, data=roles)

    @cherrypy.expose
    @cherrypy.tools.requires_login(permission="admin")
    def get_role_members(self, roleId, **kwargs):
        searchWidget = self.get_search_widget("manage_roles")
        roleId = strip_tags(roleId)
        try:
            role = session.query(Role).filter(Role.id == roleId).one()
            tpl = Template(file=get_template_file('view_role.tmpl'), searchList=[locals(),globals()])
            return str(tpl)
        except Exception, e:
            raise cherrypy.HTTPError(500, str(e))


    @cherrypy.expose
    @cherrypy.tools.requires_login(permission="admin")
    def delete_roles(self, roleIds, format="json", **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"), [], [])
        try:
            roleIds = split_list_sanitized(roleIds)
            for roleId in roleIds:
                try:
                    role = session.query(Role).filter(Role.id == roleId).one()
                    session.delete(role)
                    session.add(AuditLog(user.id, "Delete Role", "You deleted role \"%s\" from the system" % role.name, None))
                except sqlalchemy.orm.exc.NoResultFound:
                    fMessages.append("The role ID: %s does not exist" % str(roleId))
            session.commit()
            sMessages.append("Successfully deleted roles%s." % str(roleId))
        except Exception, e:
            session.rollback()
            logging.error("[%s] [delete_roles] [Problem deleting roles: %s]" % (user.id, str(e)))
            fMessages.append("Problem deleting roles: %s" % str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def switch_roles(self, roleId=None, format="json", **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"), [], [])
        try:
            if strip_tags(roleId) is None:
                cherrypy.session['current_role'] = None
            else:
                attachedUser = session.query(User).filter(User.id==user.id).one()
                for role in attachedUser.roles:
                    if role.id == roleId:
                        cherrypy.session['current_role'] = role.get_copy()
                        sMessages.append("Switched to role %s" % role.name)
                        break
                    fMessages.append("You are not a member of this role")
        except Exception, e:
            fMessages.append("Unable to switch roles: %s" % str(e))
            logging.error("Error switching roles: %s" % str(e))
        return fl_response(sMessages, fMessages, format)
    
    @cherrypy.expose
    @cherrypy.tools.requires_login(permission="admin")
    def add_users_to_role(self, roleId, userIds, format="json", **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"), [], [])
        try:
            roleId = strip_tags(roleId)
            userIds = split_list_sanitized(userIds)
            if userIds is not None and roleId is not None:
                role = session.query(Role).filter(Role.id==roleId).one()
                for userId in userIds:
                    try:
                        user = get_user(userId)
                        role.members.append(user)
                        session.commit()
                    except sqlalchemy.orm.exc.NoResultFound, nrf:
                        fMessages.append("User with ID:%s could not be found" % str(roleId))
                sMessages.append("Added user(s) to role: %s" % str(roleId))
        except sqlalchemy.orm.exc.NoResultFound, nrf:
            fMessages.append("Role with ID:%s could not be found" % str(roleId))
        except Exception, e:
            fMessages.append("Unable to add users to role: %s" % str(e))
            logging.error("[%s] [add_users_to_role] [Error addings users to role: %s]" % (userIds, str(e)))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login(permission="admin")
    def remove_users_from_role(self, roleId, userIds, format="json", **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"), [], [])
        try:
            roleId = strip_tags(roleId)
            userIds = split_list_sanitized(userIds)
            if userIds is not None and roleId is not None:
                role = session.query(Role).filter(Role.id==roleId).one()
                for userId in userIds:
                    try:
                        user = get_user(userId)
                        role.members.remove(user)
                        session.commit()
                    except sqlalchemy.orm.exc.NoResultFound, nrf:
                        fMessages.append("User with ID:%s could not be found" % str(roleId))
                sMessages.append("Removed user(s) from role: %s" % str(roleId))
        except sqlalchemy.orm.exc.NoResultFound, nrf:
            fMessages.append("Role with ID:%s could not be found" % str(roleId))
        except Exception, e:
            fMessages.append("Unable to remove users from roles: %s" % str(e))
            logging.error("[%s] [remove_users_from_role] [Unable to remove users from roles: %s]" % (userIds, str(e)))
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
    def get_user_permissions(self, userId, format="json", **kwargs):
        sMessages, fMessages, permissionData = ([], [], [])
        try:
            userId = strip_tags(userId)
            flUser = session.query(User).filter(User.id == userId).one()
            permissions = session.query(Permission).all()
            for permission in permissions:
                permissionFound = False
                if permission in flUser.permissions:
                    permissionFound = True
                    permissionData.append({'permissionId': permission.id, 'permissionName': permission.name, 'inheritedFrom': "user"})
                else:
                    for group in flUser.groups:
                        if permission in group.permissions:
                            permissionFound = True
                            permissionData.append({'permissionId': permission.id, 'permissionName': permission.name, 'inheritedFrom': "(group) %s" % group.name})
                            break
                    if permissionFound == False:
                        permissionData.append({'permissionId': permission.id, 'permissionName': permission.name, 'inheritedFrom': ""})
        except sqlalchemy.orm.exc.NoResultFound:
            fMessages.append("The user ID: %s does not exist" % str(userId))
        except Exception, e:
            logging.error("Couldn't get permissions for user %s: %s" % (userId, str(e)))
            fMessages.append("Could not get permissions: %s" % str(e))
        return fl_response(sMessages, fMessages, format, data=permissionData)

    @cherrypy.expose
    @cherrypy.tools.requires_login(permission="admin")
    def get_role_permissions(self, roleId, format="json", **kwargs):
        sMessages, fMessages, permissionData = ([], [], [])
        try:
            roleId = strip_tags(roleId)
            role = session.query(Role).filter(Role.id == roleId).one()
            permissions = session.query(Permission).all()
            for permission in permissions:
                if permission in role.permissions:
                    permissionData.append({'permissionId': permission.id, 'permissionName': permission.name, 'inheritedFrom': "role"})
                else:
                    permissionData.append({'permissionId': permission.id, 'permissionName': permission.name, 'inheritedFrom': ""})
        except sqlalchemy.orm.exc.NoResultFound:
            fMessages.append("The role ID: %s does not exist" % str(roleId))
        except Exception, e:
            logging.error("[%s] [get_role_permissions] [Couldn't get permissions for role %s: %s]" % (user.id, roleId, str(e)))
            fMessages.append("Could not get permissions: %s" % str(e))
        return fl_response(sMessages, fMessages, format, data=permissionData)

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
    def grant_user_permission(self, userId, permissionId, format="json", **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"), [], [])
        try:
            userId = strip_tags(userId)
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
    @cherrypy.tools.requires_login(permission="admin")
    def grant_role_permission(self, roleId, permissionId, format="json", **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"), [], [])
        try:
            roleId = strip_tags(roleId)
            permission = session.query(Permission).filter(Permission.id == permissionId).one()
            try:
                role = session.query(Role).filter(Role.id == roleId).one()
                role.permissions.append(permission)
                session.commit()
                sMessages.append("Role %s granted permission %s" % (roleId, permissionId))
            except sqlalchemy.orm.exc.NoResultFound:
                fMessages.append("Role with ID: %s does not exist" % str(roleId))
        except sqlalchemy.orm.exc.NoResultFound:
            fMessages.append("Permission with ID: %s does not exist" % str(permissionId))
        except Exception, e:
            session.rollback()
            logging.error("[%s] [grant_role_permission] [Problem granting role a permission: %s]" % (user.id, str(e)))
            fMessages.append("Problem granting a role permission: %s" % str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def revoke_user_permission(self, userId, permissionId, format="json", **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"), [], [])
        try:
            permission = session.query(Permission).filter(Permission.id == permissionId).one()
            try:
                flUser = session.query(User).filter(User.id == userId).one()
                if (flUser.id == user.id and permission.id == "admin"):
                    fMessages.append("You cannot remove admin permissions from your own account")
                else:
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
    @cherrypy.tools.requires_login()
    def revoke_role_permission(self, roleId, permissionId, format="json", **kwargs):
        user, sMessages, fMessages = (cherrypy.session.get("user"), [], [])
        try:
            roleId = strip_tags(roleId)
            permission = session.query(Permission).filter(Permission.id == permissionId).one()
            try:
                role = session.query(Role).filter(Role.id == roleId).one()
                role.permissions.remove(permission)
                session.commit()
                sMessages.append("Role %s no longer has permission %s" % (roleId, permissionId))
            except sqlalchemy.orm.exc.NoResultFound:
                fMessages.append("Role with ID: %s does not exist" % str(roleId))
        except sqlalchemy.orm.exc.NoResultFound:
            fMessages.append("Permission with ID: %s does not exist" % str(permissionId))
        except Exception, e:
            session.rollback()
            logging.error("[%s] [revoke_role_permission] [Problem revoking a role permission: %s]" % (user.id, str(e)))
            fMessages.append("Problem revoking a role permission: %s" % str(e))
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

if __name__ == "__main__":
    print "Hello";