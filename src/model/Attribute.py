# -*- coding: utf-8 -*-
class Attribute:
    userId = None
    def __init__ (self, attributeId, attributeName):
        self.attributeId = attributeId
        self.attributeName = attributeName
    
    def __str__(self):
        return "%s (%s)" % (attributeName, attributeId)