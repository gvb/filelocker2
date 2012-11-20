import cherrypy
import time
import FileService
import os

class ProgressFile(object):
    def __init__(self, buf, fileName, file_object=None, uploadIndex=None, *args, **kwargs):
        if file_object is None:
            self.file_object = FileService.get_temp_file()
        else:
            self.file_object = file_object
        self.fileName = fileName
        self.transferred = 0
        self.buf = buf
        lcHDRS = {}
        for key, val in cherrypy.request.headers.iteritems():
            lcHDRS[key.lower()] = val
        self.pre_sized = float(lcHDRS['content-length'])
        self.speed = 1
        self.remaining = 0
        self.eta = 0
        self.uploadIndex = uploadIndex
        self._start = time.time()
        self.status = "Uploading"
    def write(self, data):
        now = time.time()
        self.transferred += len(data)
        if (now - self._start) == 0:
            self.speed = 0
        else:
            self.speed = self.transferred / (now - self._start)
        self.remaining = self.pre_sized - self.transferred
        if self.speed == 0: self.eta = 9999999
        else: self.eta = self.remaining / self.speed
        return self.file_object.write(data)

    def seek(self, pos):
        self.post_sized = self.transferred
        self.transferred = True
        return self.file_object.seek(pos)

    def read(self, size):
        return self.file_object.read(size)

    def stat_dict(self):
        valDict = {'fileName': self.fileName, 'speed': '%9.2f' % (self.speed / 1024.0),
                   'sizeKB': '%9.2f' % (self.pre_sized / 1024.0),
                   'transferredKB': '%9.2f' % (self.transferred / 1024.0), 'eta': str(int(self.eta))}
        if self.uploadIndex is not None:
            if self.uploadIndex.isdigit():
                valDict['uploadIndex'] = self.uploadIndex
            else:
                valDict['uploadIndex'] = "\"%s\"" % self.uploadIndex
        valDict['status'] = self.status
        return valDict

class FileFieldStorage(cherrypy._cpcgifs.FieldStorage):
    def __del__(self, *args, **kwargs):
        try:
            uploadKey = None
            if cherrypy.session.has_key("user"):
                uploadKey = cherrypy.session.get('user').id
            elif cherrypy.session.has_key("uploadRequest"):
                uploadKey = cherrypy.session.get("uploadRequest").owner_id+":"+cherrypy.session.get("uploadRequest").id
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
        except AttributeError, ae:
            pass
        except OSError, oe:
            pass
        except Exception, e:
            pass

    def make_file(self, binary=None):
        uploadIndex = None
        if cherrypy.request.headers.has_key("uploadindex"):
            uploadIndex = cherrypy.request.headers['uploadindex']
        fo = ProgressFile(self.bufsize, self.filename if self.filename is not None else "Default", uploadIndex=uploadIndex)
        self.file_location = fo.file_object.name
        uploadKey = None
        if cherrypy.session.has_key("uploadRequest"):
            uploadKey = cherrypy.session.get("uploadRequest").owner_id+":"+cherrypy.session.get("uploadRequest").id
        elif cherrypy.session.has_key("user"):
            uploadKey = cherrypy.session.get('user').id

        if cherrypy.file_uploads.has_key(uploadKey):
            cherrypy.file_uploads[uploadKey].append(fo)
        else:
            cherrypy.file_uploads[uploadKey] = [fo,]
        return fo