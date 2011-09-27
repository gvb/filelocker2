# -*- coding: utf-8 -*-
class Parameter:
    def __init__ (self, parameterName, parameterDescription, pType, value):
        self.parameterName = parameterName
        self.parameterDescription = parameterDescription
        self.value = value
        self.parameterType = pType
    
    def __str__(self):
        return "Parameter: %s Parameter Description: %s Type:%s Value: %s" % (self.parameterName, self.parameterDescription, self.parameterType, self.value)