# -*- coding: utf-8 -*-
class RemoteServer:
    def __init__(self, address, name, ownerId, username, password, domain, serverId = None):
        self.serverId = serverId
        self.serverAddress = address
        self.displayName = name
        self.ownerId = ownerId
        self.username = username
        self.password = password
        self.domain = domain
class RemoteFile:
    def __init__(self, fileId, filePath, fileServerId):
        self.fileId = fileId
        self.filePath = filePath
        self.fileServerId = fileServerId