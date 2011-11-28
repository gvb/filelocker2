# -*- coding: utf-8 -*-
import logging

class Directory:
    def lookup_user(userId):
        pass #Return either a user object or None
    def authenticate(userId, password):
        pass #Return either True or False
    def get_user_matches(firstname, lastname, userId):
        pass #Returns list of User objects based off info in the directory