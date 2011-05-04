# -*- coding: utf-8 -*-
# To change this template, choose Tools | Templates
# and open the template in the editor.

__author__="wbdavis"
__date__ ="$Feb 22, 2010 4:50:01 PM$"

class FLError(Exception):
    failureMessages = []
    successMessages = []
    def __init__(self, partialSuccess, failureMessages, successMessages=None):
        self.partialSuccess = partialSuccess
        if failureMessages is not None:
            self.failureMessages = failureMessages
        if successMessages is not None:
            self.successMessages = successMessages

    def __str__(self):
        return "Filelocker Error: \n  Partial Success: %s\n   Failure Messages: %s\n   Success Messages: %s" % (self.partialSuccess, self.failureMessages, self.successMessages)
