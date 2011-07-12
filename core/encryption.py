# -*- coding: utf-8 -*-
import struct, string, math, hmac # RFC2104
try:
    from hashlib import md5
except ImportError, ie:
    from md5 import md5
from Crypto.Cipher import XOR
from Crypto.Cipher import AES
from Crypto import Random
import os
import re
import sys
import stat
import logging
#Module responsible for building the AES encryption function
def new_encrypter(password):
   iteration = 2048
   keyBytes = 32
   encrypter = None
   m = md5()
   m.update(str(Random.get_random_bytes(32)))
   salt = m.hexdigest()[0:16]
   try:
      key = KeyGen().makeKey(password, str(salt), iteration, keyBytes)
      encrypter = AES.new(key, AES.MODE_CBC, salt)
   except Exception, e:
      logging.critical("Unable to create encrypter: %s" % str(e))
   return encrypter, salt

def new_decrypter(password, salt):
   iteration = 2048
   keyBytes = 32
   decrypter = None
   try:
      key = KeyGen().makeKey(password, str(salt), iteration, keyBytes)
      decrypter = AES.new(key, AES.MODE_CBC, salt)
   except Exception, e:
      logging.critical("Unable to create decrypter: %s" % str(e))
   return decrypter
   
#PBKDFv2 Key Generator, based on the one found in the Revolution package for the Evolution mail client
class KeyGen: 
    def __init__(self):
        self.hashLength = 32
        
    def makeKey(self, Password, Salt, count, keyLength):
        try:
            str(Password)
            str(Salt)
            int(count)
            float(keyLength) 
            int(count)
        except:
            raise "ERROR! Input is not correct!"

        if keyLength > ((2^32 - 1) * self.hashLength):
            maxlength = (2^32 - 1) * self.hashLength
            raise "ERROR! Key is to large! Maxlength is", str(maxlength)
        l = math.ceil(keyLength / float(self.hashLength))
        r = keyLength - (l - 1) * self.hashLength
        T = ""
        for blockindex in range(int(l)):
            T += self.F(Password, Salt, count, blockindex)
        DK = T[:keyLength]
        return DK
            
    def F(self, Password, Salt, count, i):
        istr = struct.pack(">I", i+1)
        PRFMaster = hmac.new(Password)
        PRF = PRFMaster.copy()
        PRF.update(Salt)
        PRF.update(istr)
        U = PRF.digest() 
        Fbuf = U
        iteration = 1
        while iteration < count:
            PRF = PRFMaster.copy()
            PRF.update(U)
            U = PRF.digest()
            Fbuf = self._xor(U, Fbuf)    
            iteration += 1
        return Fbuf

    def _xor(self, a, b):
        if len(a) != len(b):
            raise "ERROR: Strings are of different size! %s %s" % (len(a), len(b))
        xor = XOR.new(a)
        return xor.encrypt(b)
    
def generatePassword():
   #Based on the example from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/59873
   import string
   chars = string.letters + string.digits
   newpasswd=str(Random.get_random_bytes(32))
   return newpasswd
