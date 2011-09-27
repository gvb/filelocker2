# -*- coding: utf-8 -*-
from Share import Share
class PrivateAttributeShare(Share):
    def __init__(self, fileId, attributeId):
        self.fileId = fileId
        self.attribute = attributeId