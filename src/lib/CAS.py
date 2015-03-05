#! /usr/local/bin/python
# -*- coding: utf-8 -*-
import cherrypy
import urllib
import urllib2

class CAS(object):
    """A class for working with a CAS server."""
    
    def __init__(self, url, renew=False, **kwords):
        
        self.url = url
        
        self.renew = renew
        self.paths = {
            'login_path': '/login',
            'logout_path': '/logout',
            'validate_path': '/serviceValidate',
            'authenticate_path': '/v1/tickets'
        }
        self.paths.update(kwords)  
       
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
        VALIDATE_URL = self.validate_url(service, ticket)
        try:
            f = urllib2.urlopen(VALIDATE_URL)
            valid = False
            user = None
            response = f.read()
            if response.find("cas:authenticationSuccess")>=0:
                valid = True
                startIndex = response.rfind("<cas:user>")+len("<cas:user>")
                endIndex = response.rfind("</cas:user>")
                user = response[startIndex:endIndex]
            else:
                valid = False
            return valid, user
        except Exception, e:
            cherrypy.log.error("Error in CAS ticket validation: %s" % (str(e)))
            return (False, None)
            
    def proxy_cas_authenticate(self, username, password):
        try:
            authURL = self.url + self.paths['authenticate_path']
            values = {'username': username, 'password': password}
            data = urllib.urlencode(values)
            req = urllib2.Request(authURL, data)
            response = urllib2.urlopen(req)
            if 200 <= response.getcode() <= 299:
                return True
        except urllib2.HTTPError:
            return False
        except Exception, e:
            cherrypy.log.error("[system] [proxyCasLogin] [%s]" % str(e))
            return False
            
           