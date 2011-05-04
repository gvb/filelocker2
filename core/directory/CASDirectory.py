#! /usr/local/bin/python
# -*- coding: utf-8 -*-
 
import sys

from SOAPpy import Config, HTTPTransport, SOAPAddress, WSDL
import urllib, urllib2
import logging
from LDAPDirectory import LDAPDirectory

class CASDirectory(object):
    """A class for working with a CAS server."""
    
    def __init__(self, config, renew=False, **kwords):
        
        self.user_directory = LDAPDirectory(config)
        self.url = config['directory']['casurl']
        self.wslogin = config['directory']['wslogin']
        self.wspassword = config['directory']['wspassword']
        self.renew = renew
        self.paths = {
            'login_path': '/login',
            'logout_path': '/logout',
            'validate_path': '/serviceValidate',
        }
        self.paths.update(kwords)  
        
    def lookup_user(self, userId):
        return self.user_directory.lookup_user(userId)
        
    def get_user_matches(self, firstName=None, lastName=None, userId=None):
        return self.user_directory.get_user_matches(firstName, lastName, userId)
    
    
    def login_url(self, service):
        """Return the login URL for the given service."""
        base = self.url + self.paths['login_path'] + '?service=' + urllib.quote_plus(service)
        if self.renew:
            base += "&renew=true"
        return base

    def logout_url(self, url=None):
        """Return the logout URL."""
        base = self.url + self.paths['logout_path'] 
        if url:
            base += '?url=' + urllib.quote_plus(url)
        return base

    def validate_url(self, service, ticket):
        """Return the validation URL for the given service. (For CAS 1.0)"""
        base = self.url + self.paths['validate_path'] + '?service=' + urllib.quote_plus(service) + '&ticket=' + urllib.quote_plus(ticket)
        if self.renew:
            base += "&renew=true"
        return base

    def validate_ticket(self, service, ticket):
        """Validate the given ticket against the given service."""
        logging.debug("CAS: self.validate_url(%s, %s)" % (str(service), str(ticket)))
        VALIDATE_URL = self.validate_url(service, ticket)
        try:
            f = urllib2.urlopen(VALIDATE_URL)
            valid = False
            user = None
            response = f.read()
            if response.find("cas:authenticationSuccess")>=0:
                logging.debug("CAS: Auth success\nResponse: %s" % response)
                valid = True
                startIndex = response.rfind("<cas:user>")+len("<cas:user>")
                endIndex = response.rfind("</cas:user>")
                user = response[startIndex:endIndex]
            else:
                logging.debug("CAS: Auth failure\nResponse: %s" % response)
                valid = False
            return (valid, user)
        except Exception, e:
            logging.critical("Error in CAS ticket validation: %s" % (str(e)))
            return (False, None)
        
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
