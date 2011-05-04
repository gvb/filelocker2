# -*- coding: utf-8 -*-
class Group:
    groupMembers = []
    def __init__(self, groupScope, ownerId, groupName, groupMembers=None, groupId=None):
            self.groupScope = groupScope #public, private, reserved
            self.ownerId = ownerId
            self.groupName = groupName
            if groupMembers is not None:
                self.groupMembers = groupMembers
            else:
                self.groupMembers = []
            if groupId is not None:
                self.groupId = groupId
            else:
                self.groupId = None
