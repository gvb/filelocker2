# -*- coding: utf-8 -*-
import logging

class Directory:
    def lookup_user(userId):
        pass #Return either a user object or None
    def authenticate(userId, password):
        pass #Return either True or False
    def get_user_matches(firstname, lastname, userId):
        pass #Returns list of User objects based off info in the directory

def directory_factory(fl):
    if fl.directoryConfig['directory_type'] != "local":
        if fl.directoryConfig['directory_type'] == "ldap":
            from LDAPDirectory import LDAPDirectory
            directory = LDAPDirectory(fl.directoryConfig)
            return directory
        elif fl.directoryConfig['directory_type'] == "ws":
            from WSDirectory import WSDirectory
            return WSDirectory(fl.directoryConfig)
        else:
            logging.error("Invalid directory type specified in config: %s" % str(fl.directoryConfig['directory_type']))
    else:
        return fl.localDirectory