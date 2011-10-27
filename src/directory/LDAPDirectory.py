# -*- coding: utf-8 -*-
import ldap
import logging
from lib.Models import User
#Thanks to user cywolf1 on SourceForge for the fixes in this module to get it to work with Active Directory
class LDAPDirectory(object):
    ldap.set_option(ldap.OPT_PROTOCOL_VERSION, ldap.VERSION3)
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
    ldap.set_option(ldap.OPT_REFERRALS, 0)
    def __init__(self, config):
        try:
            self.directoryHost = config['ldap_host']
            self.ldapBindPass = config['ldap_bind_pass']
            self.ldapBindUser = config['ldap_bind_user']
            self.isActiveDirectory = config['ldap_is_active_directory']
            self.domainName = config['ldap_domain_name']
            self.directoryBindDn = config['ldap_bind_dn']
            self.lastNameAttr = config['ldap_last_name_attr']
            self.firstNameAttr = config['ldap_first_name_attr']
            self.userIdAttr = config['ldap_user_name_attr']
            self.displayNameAttr = config['ldap_displayname_attr']
            self.emailAttr = config['ldap_email_attr']
        except Exception, e:
            logging.critical("Unable to build LDAP directory: %s" % str(e))
   
    def get_bind(self):
        l = ldap.initialize(self.directoryHost)
        if self.ldapBindUser is not None and self.ldapBindUser !="":
            l.simple_bind_s(self.ldapBindUser,self.ldapBindPass)
        else:
            l.simple_bind_s()
        return l
        
    def lookup_user(self, userId):
        """ get authentication data from form, authenticate against LDAP (or Active Directory),
            fetch some user infos from LDAP and create a user profile for that user that must
            be used by subsequent auth plugins (like moin_cookie) as we never return a user
            object from ldap_login.
        """
        foundUser = None
        l = self.get_bind()
        filterstr = "(%s=%s)" % (self.userIdAttr, userId)
        lusers = l.search_st(self.directoryBindDn, ldap.SCOPE_SUBTREE, filterstr, timeout=30.0)
        
        result_length = len(lusers)
        
        if result_length > 0:
            dn, ldap_dict = lusers[0]
            userFirstName, userLastName, userDisplayName, userEmail = (ldap_dict.get(self.firstNameAttr, [''])[0], ldap_dict.get(self.lastNameAttr, [''])[0], ldap_dict.get(self.displayNameAttr, [''])[0].title(), ldap_dict.get(self.emailAttr, [''])[0])
        else:
            userFirstName, userLastName, userDisplayName, userEmail = ("NOT FOUND", "NOT FOUND", userId + " NOT FOUND", "")
        foundUser = User(first_name=userFirstName, last_name=userLastName, email=userEmail, id=userId, display_name=userDisplayName)
        return foundUser
        
    #This function will do a search on an ldap directory getting all matches for a combination of first names and last names 
    def get_user_matches(self, firstName=None, lastName=None, userId=None):
        userMatches = []
        l = self.get_bind()
        filters = []
        lusers = None
        result = None
        result_length = 0
        message = "No matches"
        lusers = []
        
        if userId is not None: #This search takes priority, since it is more precise I suppose
            try:
                exactFilter = "(%s=%s)" % (self.userIdAttr, userId)
                lusers.extend(l.search_ext_s(self.directoryBindDn, ldap.SCOPE_SUBTREE, exactFilter, timeout=30.0))
                if len(lusers) == 0:
                    similarFilter = "(%s=*%s*)" % (self.userIdAttr, userId)
                    lusers.extend(l.search_ext_s(self.directoryBindDn, ldap.SCOPE_SUBTREE, similarFilter, timeout=30.0))
            except ldap.SIZELIMIT_EXCEEDED, se:
                if len(lusers) == 0:
                    raise Exception("Too many results.")
                else:
                    pass
            except ldap.ADMINLIMIT_EXCEEDED, ae:
                if len(lusers) == 0:
                    raise Exception("Too many results.")
                else:
                    pass
        else:
            if firstName is not None and lastName is not None:
                filters.append("(&(%s=%s*)(|(%s=%s*)))" % (self.lastNameAttr,lastName, self.firstNameAttr, firstName))
            elif firstName is None and lastName is not None:
                filters.append("(%s=%s*)" % (self.firstNameAttr, lastName)) #This is to check if it's a first name or a last name if they entered only one e.g. Cher, or Seal
                filters.append("(%s=%s)" % (self.lastNameAttr,lastName))
            elif firstName is not None:
                filters.append("(%s=%s)" % (self.firstNameAttr,firstName))
            for filterstr in filters:
                try:
                    lusers.extend(l.search_ext_s(self.directoryBindDn, ldap.SCOPE_SUBTREE, filterstr, timeout=30.0, sizelimit=10))
                except ldap.SIZELIMIT_EXCEEDED, se:
                    if len(lusers) == 0:
                        raise Exception("Too many results.")
                    else:
                        pass
                except ldap.ADMINLIMIT_EXCEEDED, ae:
                    if len(lusers) == 0:
                        raise Exception("Too many results.")
                    else:
                        pass
        
        #This creates an array of dictionaries with keys for the full name and alias
        for user in lusers:
            dn, ldap_dict = user
            userId = ldap_dict.get(self.userIdAttr, [''])[0]
            userFirstName = ldap_dict.get(self.firstNameAttr, [''])[0]
            userLastName = ldap_dict.get(self.lastNameAttr, [''])[0]
            userDisplayName = ldap_dict.get(self.displayNameAttr, [''])[0].title()
            email = ldap_dict.get(self.emailAttr, [''])[0]
            foundUser = User(first_name=userFirstName, last_name=userLastName, email=email, id=userId, display_name=userDisplayName)
            userMatches.append(foundUser)
        return userMatches
    
    def authenticate(self, userId, password):
        l = ldap.initialize(self.directoryHost)
        try:
            if userId is "" or password is "":
                logging.info("Username or password cannot be blank.  Anonymous logins are not permitted")
                raise ldap.INVALID_CREDENTIALS
            if self.isActiveDirectory.lower()=="yes":
                l.simple_bind_s(userId+"@"+self.domainName , password)
            else:
                l.simple_bind_s(self.userIdAttr+"="+userId+","+ self.directoryBindDn , password)
            return True #If no errors were raised while binding, we'll consider it a success
        except ldap.INVALID_CREDENTIALS:
            return False
        except Exception, e:
            logging.error("Error in authenticating user \"%s\": %s" % (str(userId), str(e)))
            return False
