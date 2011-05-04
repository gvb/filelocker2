#! /usr/local/bin/python
# -*- coding: utf-8 -*-
 
import sys

from SOAPpy import Config, HTTPTransport, SOAPAddress, WSDL
import urllib, urllib2
import logging

class CAS(object):
    """A class for working with a CAS server."""
    
    def __init__(self, config, renew=False, **kwords):
        self.wslogin = config['directory']['wslogin']
        self.wspassword = config['directory']['wspassword']

    def lookup_user(self, userId):
        return self.user_directory.lookup_user(userId)
        
    def get_user_matches(self, firstName=None, lastName=None, userId=None):
        return self.user_directory.get_user_matches(firstName, lastName, userId)
        
    def get_employee_status(self, userId):
        wsdlFile = "userinfoservice.wsdl" #can be URL of the wsdl, but downloading reduces transaction count
        myHTTPTransport.setAuthentication(self.wslogin, self.wspassword)
        server = WSDL.Proxy(wsdlFile, transport=myHTTPTransport)
        userCharacteristics = server.getI2A2Characteristics(userId)
        #0 is the characteristic for employees at Purdue, must be in the chars list
        if 0 in userCharacteristics:
            return True
        else:
            return False



class myHTTPTransport(HTTPTransport):
    username = None
    passwd = None

    @classmethod
    def setAuthentication(cls,u,p):
        cls.username = u
        cls.passwd = p

    def call(self, addr, data, namespace, soapaction=None, encoding=None, http_proxy=None, config=Config):

        if not isinstance(addr, SOAPAddress):
            addr=SOAPAddress(addr, config)

        if self.username != None:
            addr.user = self.username+":"+self.passwd

        return HTTPTransport.call(self, addr, data, namespace, soapaction, encoding, http_proxy, config)

if __name__ == '__main__':
    myHTTPTransport.setAuthentication(wslogin, wspassword)
    print "Auth set"
    server = WSDL.Proxy(wsdlFile, transport=myHTTPTransport)
    print "Server set"
    userInfo = server.getI2A2Characteristics(login)
    print "user info got"

    #print 'login = ' + userInfo.login
    #print 'puid = ' + str(userInfo.puid.puid)
    #print 'fullName = ' + userInfo.fullName
    #for group in userInfo.groups:
    #    print '  group = ' + group
    print str(userInfo[0])
