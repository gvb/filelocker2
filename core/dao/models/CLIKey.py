# -*- coding: utf-8 -*-
class CLIKey:
    CLIKeyHostIPv4 = None
    CLIKeyHostIPv6 = None
    CLIKeyValue = None
    def __init__ (self, CLIKeyHostIPv4, CLIKeyHostIPv6, CLIKeyValue):
        self.CLIKeyHostIPv4 = CLIKeyHostIPv4
        self.CLIKeyHostIPv6 = CLIKeyHostIPv6
        self.CLIKeyValue = CLIKeyValue
    
    def __str__(self):
        return "IPv4: %s, IPv6: %s, (%s)" % (CLIKeyHostIPv4, CLIKeyHostIPv6, CLIKeyValue)