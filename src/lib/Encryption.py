# -*- coding: utf-8 -*-
import os
import cherrypy
import struct, string, math, hmac # RFC2104
try:
    from hashlib import md5
except ImportError, ie:
    from md5 import md5
from Crypto.Cipher import XOR
from Crypto.Cipher import AES
from Crypto.Hash import SHA256

from random import SystemRandom

#Module responsible for building the AES encryption function
def new_encrypter(password):
   iteration = 2048
   keyBytes = 32
   encrypter = None
   m = md5()
   m.update(str(SystemRandom().random()))
   salt = m.hexdigest()[0:16]
   try:
      key = KeyGen().makeKey(password, str(salt), iteration, keyBytes)
      encrypter = AES.new(key, AES.MODE_CBC, salt)
   except Exception, e:
      cherrypy.log.error("Unable to create encrypter: %s" % str(e))
   return encrypter, salt

def new_decrypter(password, salt):
   iteration = 2048
   keyBytes = 32
   decrypter = None
   password = str(password).encode("ascii")
   try:
      key = KeyGen().makeKey(password, salt, iteration, keyBytes)
      decrypter = AES.new(key, AES.MODE_CBC, salt)
   except Exception, e:
      cherrypy.log.error("Unable to create decrypter: %s" % str(e))
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
            raise Exception("ERROR! Input is not correct!")

        if keyLength > ((2^32 - 1) * self.hashLength):
            maxlength = (2^32 - 1) * self.hashLength
            raise Exception("ERROR! Key is to large! Maxlength is", str(maxlength))
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

def hash_password(password, salt=None):
    sha = SHA256.new()
    if salt is None:
        salt = os.urandom(8).encode('hex')

    cryptoString = "%s%s" % (salt,password)
    sha.update(cryptoString)
    saltedHash = "%s%s" % (salt, sha.hexdigest()) #Yum
    return saltedHash #8char salt, 64 char hash, 72 chars total

def compare_password_hash(plaintextPassword, saltedHash):
    if len(saltedHash)==32: #Old md5, unsalted
        if saltedHash == md5(plaintextPassword).hexdigest():
            return True
        else:
            return False
    else:
        salt = saltedHash[0:16]
        resultingHash = hash_password(plaintextPassword, salt)
        if resultingHash == saltedHash:
            return True
        else:
            return False
    
def generatePassword():
   #Based on the example from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/59873
   import string
   chars = string.letters + string.digits
   newpasswd=""
   for i in range(32):
       newpasswd += SystemRandom().choice(chars)
   return newpasswd
