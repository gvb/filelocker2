import cherrypy
import StringIO
__author__="wbdavis"
__date__ ="$Sep 26, 2011 9:11:39 PM$"

class FileFieldStorage(cherrypy._cpcgifs.FieldStorage):
    def __del__(self, *args, **kwargs):
        try:
            uploadKey = None
            if cherrypy.session.has_key("user"):
                uploadKey = cherrypy.session.get('user').userId
            elif cherrypy.session.has_key("uploadTicket"):
                uploadKey = cherrypy.session.has_key("uploadTicket").ownerId+":"+cherrypy.session.has_key("uploadTicket").ticketId
            if cherrypy.file_uploads.has_key(uploadKey):
                for transfer in cherrypy.file_uploads[uploadKey]:
                    if transfer.file_object.name == self.file_location:
                        cherrypy.file_uploads[uploadKey].remove(transfer)
                if len(cherrypy.file_uploads[uploadKey]) == 0:
                    del cherrypy.file_uploads[uploadKey]
            if os.path.isfile(self.file_location):
                fl = cherrypy.thread_data.flDict['app']
                tempFileName = self.file_location.split(os.path.sep)[-1]
                fl.queue_for_deletion(tempFileName)
        except KeyError:
            pass
        except KeyError, ke:
            pass
        except AttributeError, ae:
            pass
        except OSError, oe:
            pass
        except Exception, e:
            pass

    def make_file(self, binary=None):
        if self.filename is not None:
            uploadIndex = None
            if cherrypy.request.headers.has_key("uploadindex"):
                uploadIndex = cherrypy.request.headers['uploadindex']
            fo = ProgressFile(self.bufsize, self.filename, uploadIndex=uploadIndex)
            self.file_location = fo.file_object.name
            uploadKey = None
            if cherrypy.session.has_key("uploadTicket"):
                uploadKey = cherrypy.session.get("uploadTicket").ownerId+":"+cherrypy.session.get("uploadTicket").ticketId
            elif cherrypy.session.has_key("user"):
                uploadKey = cherrypy.session.get('user').userId

            if cherrypy.file_uploads.has_key(uploadKey):
                cherrypy.file_uploads[uploadKey].append(fo)
            else:
                cherrypy.file_uploads[uploadKey] = [fo,]
            return fo
        else:
            return StringIO.StringIO("")