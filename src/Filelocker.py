import cherrypy
__author__="wbdavis"
__date__ ="$Sep 25, 2011 9:09:40 PM$"

if __name__ == "__main__":
    cherrypy.tools.requires_login = cherrypy.Tool('before_request_body', requires_login, priority=70)
    cherrypy.tools.before_upload = cherrypy.Tool('before_request_body', before_upload, priority=71)
    cherrypy.file_uploads = dict()
    cherrypy.file_downloads = dict()