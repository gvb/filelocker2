import cherrypy
import FileService
import StringIO
from Models import ProgressFile

def get_field_storage():
    try:
        class FileFieldStorage(cherrypy._cpcgifs.FieldStorage):
            def __del__(self, *args, **kwargs):
                try:
                    uploadKey = None
                    if cherrypy.session.has_key("user"):
                        uploadKey = cherrypy.session.get('user').id
                    elif cherrypy.session.has_key("uploadRequest"):
                        uploadKey = cherrypy.session.has_key("uploadRequest").owner_id+":"+cherrypy.session.has_key("uploadRequest").id
                    if cherrypy.file_uploads.has_key(uploadKey):
                        for transfer in cherrypy.file_uploads[uploadKey]:
                            if transfer.file_object.name == self.file_location:
                                cherrypy.file_uploads[uploadKey].remove(transfer)
                        if len(cherrypy.file_uploads[uploadKey]) == 0:
                            del cherrypy.file_uploads[uploadKey]
                    if os.path.isfile(self.file_location):
                        tempFileName = self.file_location.split(os.path.sep)[-1]
                        FileService.queue_for_deletion(tempFileName)
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
                    if cherrypy.session.has_key("uploadRequest"):
                        uploadKey = cherrypy.session.get("uploadRequest").ownerId+":"+cherrypy.session.get("uploadTicket").ticketId
                    elif cherrypy.session.has_key("user"):
                        uploadKey = cherrypy.session.get('user').userId

                    if cherrypy.file_uploads.has_key(uploadKey):
                        cherrypy.file_uploads[uploadKey].append(fo)
                    else:
                        cherrypy.file_uploads[uploadKey] = [fo,]
                    return fo
                else:
                    return StringIO.StringIO("")
        return FileFieldStorage
    except Exception, e:
        class FileRequestBody(cherrypy._cpreqbody.RequestBody):
            def __del__(self, *args, **kwargs):
                try:
                    uploadKey = None
                    if cherrypy.session.has_key("user"):
                        uploadKey = cherrypy.session.get('user').id
                    elif cherrypy.session.has_key("uploadRequest"):
                        uploadKey = cherrypy.session.has_key("uploadRequest").owner_id+":"+cherrypy.session.has_key("uploadRequest").id
                    if cherrypy.file_uploads.has_key(uploadKey):
                        for transfer in cherrypy.file_uploads[uploadKey]:
                            if transfer.file_object.name == self.file_location:
                                cherrypy.file_uploads[uploadKey].remove(transfer)
                        if len(cherrypy.file_uploads[uploadKey]) == 0:
                            del cherrypy.file_uploads[uploadKey]
                    if os.path.isfile(self.file_location):
                        tempFileName = self.file_location.split(os.path.sep)[-1]
                        FileService.queue_for_deletion(tempFileName)
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
                    if cherrypy.session.has_key("uploadRequest"):
                        uploadKey = cherrypy.session.get("uploadRequest").ownerId+":"+cherrypy.session.get("uploadTicket").ticketId
                    elif cherrypy.session.has_key("user"):
                        uploadKey = cherrypy.session.get('user').userId

                    if cherrypy.file_uploads.has_key(uploadKey):
                        cherrypy.file_uploads[uploadKey].append(fo)
                    else:
                        cherrypy.file_uploads[uploadKey] = [fo,]
                    return fo
                else:
                    return StringIO.StringIO("")
        return FileRequestBody