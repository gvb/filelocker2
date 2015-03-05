# -*- coding: utf-8 -*-
from zope.interface import Interface

class FilelockerPlugin(Interface):
    """
    Helper functions used by the extensible parts of Filelocker
    """
    
    def get_user_attributes(userId, fl):
        """
        This function should return a list of attribute IDs that a user possesses.
        """
        
    def is_authorized(userId, fl):
        """
        This function should return True unless you want to explicitly deny a user access to Filelocker. You can check a file or a database of unauthorized users
        or maybe check a directory for certain attributes (staff, currentStudent, etc) before granting permission. If any plugins return False, the user will not
        be permitted to log in.
        """
        