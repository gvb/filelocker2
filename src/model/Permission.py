    # -*- coding: utf-8 -*-
class Permission:
    permissionId = None
    permissionName = None
    def __init__(self, permissionId, permissionName, inheritedFrom = None):
        self.permissionId = permissionId
        self.permissionName = permissionName
        self.inheritedFrom = inheritedFrom
    
    def __str__(self):
        return str(self.get_dict())
    
    def get_dict(self):
        return {'permissionId': self.permissionId, 'permissionName': self.permissionName, 'inheritedFrom':self.inheritedFrom}