#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Filelocker Command Line Interface

This script allows advanced Filelocker users to interact with Filelocker via a 
command line. The CLI has two modes: interactive and scripted. After following 
the configuration instructions listed in "Help" (-h), users can enter 
interactive mode by simply running this Python program. In order to script 
Filelocker actions, users can specify an action with -a and other various 
arguments. This Python program has been tested on Python 2.6. It may work with 
other versions of Python, but your mileage may vary.
"""
md5Loaded = False
hashlibLoaded = False
try:
    import hashlib
    hashlibLoaded = True
except ImportError:
    try:
        import md5
        md5Loaded = True
    except ImportError:
        pass
import io
import itertools
import logging
import mimetools
import mimetypes
import os
import re
import stat
import sys
import threading
import time
import urllib
import urllib2
import ConfigParser
from functools import wraps
from optparse import OptionParser
from xml.sax import parseString, handler

__author__      = "Christopher Miller"
__copyright__   = "Copyright 2011, Purdue University"
__credits__     = "Christopher Miller, Brett Davis, Jim Dalton"
__license__     = "Open Source License. See LICENSE.txt."
__version__     = "2.4.2"
__maintainer__  = "Brett Davis"
__email__       = "wbdavis@purdue.edu"
__status__      = "Production"

CHUNK_SIZE = 8 * 1024
LOG_FILENAME = os.path.join(os.getcwd(), "filelocker_cli.log") #TODO move to config
LOG_LEVEL = logging.INFO #TODO move to config

logger = logging.getLogger("Filelocker CLI")
logger.setLevel(LOG_LEVEL)
fh = logging.FileHandler(LOG_FILENAME)
fh.setLevel(LOG_LEVEL)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
fh.setFormatter(formatter)
logger.addHandler(fh)

class CLI_Filelocker:
    def __init__(self, userId, showHash, isQuiet, scanFile, directory=None, configFile=None):
        """Initialization function for the Filelocker CLI
        
        This function populates class variables with data taken from the command 
        line arguments, parses the specified (or default) Filelocker CLI config 
        file, saves the config data, and attempts to authenticate against the 
        specified Filelocker server.
        """
        self.userId = userId
        self.showHash = showHash
        self.isQuiet = isQuiet
        self.scanFile = scanFile
        self.directory = directory
        self.clearScreen = True
        self.headerMessages = []
        try:
            self.installedHandler = urllib2.build_opener(urllib2.HTTPCookieProcessor())
            urllib2.install_opener(self.installedHandler)
            confParser = ConfigParser.ConfigParser()
            if configFile==None:
                configFile = os.path.join(os.getcwd(), "filelocker_cli.conf")
            if os.path.isfile(configFile)==False:
                self.cli_write("Filelocker_cli.conf could not be located at: %s", configFile)
                logger.error("Filelocker_cli.conf could not be located at: %s", configFile)
                sys.exit(0)
            confParser.read(configFile)
            self.serverLocation = confParser.get('filelocker_cli', 'server_url')
            CLIKey = confParser.get('filelocker_cli', 'cli_key')
            self.login(CLIKey, userId)
        except ConfigParser.Error, e:
            self.cli_write("Unable to parse config file at %s", configFile)
            logger.error("Unable to parse config file at %s: %s" % (configFile, str(e)))
            sys.exit(0)
        except Exception, e:
            self.cli_write("[Critical]: %s", str(e))
            logger.critical(str(e))
    
    def login(self, CLIKey, userId):
        """Authenticate a user against a Filelocker server
        
        This function sends the appropriate credentials to the specified 
        Filelocker server. The server checks the request's remote IP address, 
        coupled with the user ID and CLI key to see if the user is valid. If 
        the user is determined to be correct, a session is created and either 
        interactive mode begins or the scripted action is performed.
        """
        data = urllib.urlencode({'CLIkey': CLIKey, 'userId': userId})
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/xml"}
        response = self.send_data("/cli_interface/CLI_login", data, headers)
        if len(response.sMessages) > 0:
            for sMessage in response.sMessages:
                self.cli_write(sMessage)
                logger.info("Login succeeded for %s" % userId)
        if len(response.fMessages) > 0:
            for fMessage in response.fMessages:
                self.cli_write("Login failed: %s" % fMessage)
                logger.error("Login failed: %s" % fMessage)
            sys.exit(0)
            
# Menus
    def start_interactive(self, parser):
        """Display the main menu
        
        This function displays the main menu of basic Filelocker actions to a user 
        in interactive mode and processes the responses accordingly.
        """
        try:
            if self.isQuiet is False:
                self.redraw_header()
                self.clearScreen = True
                s = raw_input("Main Menu: \n\t1. Upload \n\t2. Share \n\t3. Download \n\t4. Delete\n\t5. Help\n\t6. Quit\nMake your selection: ").strip().lower()
                if(s=="1"):
                    self.start_interactive_upload(parser)
                elif(s=="2"):
                    self.start_interactive_share(parser)
                elif(s=="3"):
                    fileId = prompt_file_id()
                    self.download(fileId)
                    self.start_interactive(parser)
                elif(s=="4"):
                    fileId = prompt_file_id()
                    self.delete(fileId)
                    self.start_interactive(parser)
                elif(s=="5" or s=="h" or s=="help" or s=="?"):
                    parser.print_help()
                    self.clearScreen = False
                    self.start_interactive(parser)
                elif(s=="6" or s=="q" or s=="quit"):
                    sys.exit(0)
                else:
                    self.start_interactive(parser)
        except KeyboardInterrupt:
            print ""
    
    def start_interactive_upload(self, parser):
        """Display the "Upload" submenu
        
        This function displays the "Upload" submenu of Filelocker actions to a user 
        in interactive mode and processes the responses accordingly.
        """
        if self.isQuiet is False:
            self.redraw_header()
            self.clearScreen = True
            s = raw_input("Upload Menu: \n\t1. Upload \n\t2. Upload and Share with User \n\t3. Upload and Share with Group \n\t4. Back \n\t5. Help\n\t6. Quit\nMake your selection: ").strip().lower()
            if(s=="1"):
                filePath = prompt_file_path()
                self.upload(filePath)
                self.start_interactive_upload(parser)
            elif(s=="2"):
                filePath = prompt_file_path()
                targetUserId = prompt_target_id("user")
                self.upload_and_share(filePath, targetUserId, "user")
                self.start_interactive_upload(parser)
            elif(s=="3"):
                filePath = prompt_file_path()
                targetGroupId = prompt_target_id("group")
                self.upload_and_share(filePath, targetGroupId, "group")
                self.start_interactive_upload(parser)
            elif(s=="4"):
                self.start_interactive(parser)
            elif(s=="5" or s=="h" or s=="help" or s=="?"):
                parser.print_help()
                self.clearScreen = False
                self.start_interactive_upload(parser)
            elif(s=="6" or s=="q" or s=="quit"):
                sys.exit(0)
            else:
                self.start_interactive_upload(parser)
    
    def start_interactive_share(self, parser):
        """Display the "Share" submenu
        
        This function displays the "Share" submenu of Filelocker actions to a user 
        in interactive mode and processes the responses accordingly.
        """
        if self.isQuiet is False:
            self.redraw_header()
            self.clearScreen = True
            s = raw_input("Share Menu: \n\t1. Share with User \n\t2. Share with Group \n\t3. Back \n\t4. Help\n\t5. Quit\nMake your selection: ").strip().lower()
            if(s=="1"):
                fileId = prompt_file_id()
                targetUserId = prompt_target_id("user")
                self.share(fileId, targetUserId, "user")
                self.start_interactive_share(parser)
            elif(s=="2"):
                fileId = prompt_file_id()
                targetGroupId = prompt_target_id("group")
                self.share(fileId, targetGroupId, "group")
                self.start_interactive_share(parser)
            elif(s=="3"):
                self.start_interactive(parser)
            elif(s=="4" or s=="h" or s=="help" or s=="?"):
                parser.print_help()
                self.clearScreen = False
                self.start_interactive_share(parser)
            elif(s=="5" or s=="q" or s=="quit"):
                sys.exit(0)
            else:
                self.start_interactive_share(parser)
            
# Functionality
    def upload(self, filePath):
        """Upload a file to Filelocker
        
        This function calculates and displays the MD5 hash value for the given 
        file (if prompted), sets various fields, generates a multi-part form with 
        the specified file and fields, starts a poller that displays upload 
        progress, sends the form to Filelocker, and displays success and failure 
        messages.
        """
        fileName = os.path.basename(filePath)
        fileSize = os.path.getsize(filePath)
        params = {}
        params['format'] = 'cli';
        params['fileName'] = fileName
        if (hashlibLoaded or md5Loaded) and self.showHash:
            self.cli_write("Calculating MD5 Hash...")
            md5Hash = self.md5_for_file(filePath)
            params['fileNotes'] = 'Uploaded via Filelocker CLI. MD5 Hash: %s' % md5Hash
            self.cli_write("MD5 Hash: %s", md5Hash)
            logger.info("MD5 Hash for %s: %s" % (fileName, md5Hash))
            self.headerMessages.append("MD5 Hash for %s: %s" % (fileName, md5Hash))
        else:
            params['fileNotes'] = 'Uploaded via Filelocker CLI.'
        if self.scanFile:
            params['scanFile'] = str(self.scanFile)
        if os.path.isfile(filePath):
            f = io.open(filePath, "rb")
        else:
            self.cli_write("%s is not a valid file path" % filePath)
            logger.error("Upload failed: Invalid file path")
            sys.exit(0)
        headers = {"Content-Type": "application/octet-stream", "Accept": "text/xml", "Content-Length": fileSize, "X-File-Name": fileName}
        thread = self.poll_upload(fileName)
        data = urllib.urlencode(params)
        response = self.send_data("/file_interface/upload?"+data, f, headers)
        f.close()
        thread.join()
        if len(response.sMessages) > 0:
            for sMessage in response.sMessages:
                self.cli_write(sMessage)
                logger.info("Upload succeeded: %s" % sMessage)
                self.headerMessages.append(sMessage)
        if len(response.fMessages) > 0:
            for fMessage in response.fMessages:
                self.cli_write(fMessage)
                logger.error("Upload failed: %s" % fMessage)
                self.headerMessages.append(fMessage)
        if len(response.data) > 0:
            return response.data[0]['id']
    
    def upload_and_share(self, filePath, targetIds, scope):
        """Upload a file to Filelocker and share it with a user or group
        
        This function allows users to upload and share a file in one action.
        """
        fileId = self.upload(filePath)
        self.share(fileId, targetIds, scope)
        
    def share(self, fileIds, targetIds, shareType):
        """Share a file with a user or group
        
        This function iteratively shares a file with each user or group specified 
        in a comma-separated list of user IDs or group IDs.
        """
        targetIds = self.split_list_sanitized(targetIds)
        for targetId in targetIds:
            if shareType=="user":
                data = urllib.urlencode({'fileIds': fileIds, 'targetId': targetId, 'format': 'cli'})
            elif shareType=="group":
                data = urllib.urlencode({'fileIds': fileIds, 'groupId': targetId, 'format': 'cli'})
            else:
                sys.exit(0)
            headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/xml"}
            response = self.send_data("/share_interface/create_private_share", data, headers)
            if len(response.sMessages) > 0:
                for sMessage in response.sMessages:
                    self.cli_write(sMessage)
                    logger.info(sMessage)
                    self.headerMessages.append(sMessage)
            if len(response.fMessages) > 0:
                for fMessage in response.fMessages:
                    self.cli_write(fMessage)
                    logger.error(fMessage)
                    self.headerMessages.append(fMessage)

    def download(self, fileIds):
        """Download files from Filelocker
        
        This function iteratively downloads each file specified in a 
        comma-separated list of files. For each file, it sets the appropriate 
        parameters, initiates a request, starts a poller that displays 
        download progress, downloads the file, and displays success and 
        failure messages.
        """
        try:
            fileIds = self.split_list_sanitized(fileIds)
            for fileId in fileIds:
                data = urllib.urlencode({'fileId': fileId, 'format': 'cli'})
                response = urllib2.urlopen(self.serverLocation + "/file_interface/download", data)
                fileName = response.info()['Content-Disposition'].split('filename=')[1]
                if fileName[0]=='"' or fileName[0]=="'":
                    fileName = fileName[1:-1]
                if fileName is None:
                    fileName = fileId + ".file"
                fileSize = response.info()['Content-Length']
                if self.directory is not None:
                    filePath = os.path.join(self.directory, fileName)
                else:
                    filePath = os.path.join(os.getcwd(), fileName)
                thread = self.poll_download(fileName, filePath, fileSize)
                bytesRemaining = long(fileSize)
                f = open(filePath, "wb")
                while True:
                    if bytesRemaining >= CHUNK_SIZE:
                        block = response.read(CHUNK_SIZE)
                    else:
                        block = response.read(bytesRemaining)
                    f.write(block)
                    bytesRemaining -= CHUNK_SIZE
                    if bytesRemaining <= 0: 
                        f.close()
                        break
                thread.join()
                self.check_server_messages()
                try:
                    if os.stat(filePath)[stat.ST_SIZE]==long(fileSize):
                        self.cli_write("Downloaded succeeded for file %s", fileName)
                        logger.info("Downloaded succeeded for file %s", fileName)
                        self.headerMessages.append("Downloaded succeeded for file %s" % fileName)
                    else:
                        self.cli_write("Download failed (interrupted) for file %s", fileName)
                        logger.error("Download failed (interrupted) for file %s", fileName)
                        self.headerMessages.append("Download failed (interrupted) for file %s" % fileName)
                        os.remove(filePath)
                except:
                    raise
        except urllib2.HTTPError, he:
            if he.code==404:
                self.cli_write("The requested file (%s) was not found", fileId)
                logger.error("The requested file (%s) was not found (HTTP %s)" % (fileId, he.code))
                self.headerMessages.append("The requested file (%s) was not found" % fileId)
            else:
                self.cli_write("[Critical]: %s", str(he))
                logger.critical("HTTP %s: %s" % (he.code, str(he)))
                self.headerMessages.append("[Critical]: %s" % str(he))
        except OSError, oe:
            self.cli_write("Download failed (interrupted) for file %s", fileName)
            logger.error("Download failed (interrupted) for file %s", fileName)
            self.headerMessages.append("Download failed (interrupted) for file %s" % fileName)
        except Exception, e:
            self.cli_write("[Critical]: %s", str(e))
            logger.critical(str(e))
            sys.exit(0)
            
    def delete(self, fileIds):
        """Delete files from Filelocker
        
        This function iteratively deletes each file specified in a 
        comma-separated list of files.
        """
        data = urllib.urlencode({'fileIds': fileIds, 'format': 'cli'})
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/xml"}
        response = self.send_data("/file_interface/delete_files", data, headers)
        if len(response.sMessages) > 0:
            for sMessage in response.sMessages:
                self.cli_write(sMessage)
                self.headerMessages.append(sMessage)
        if len(response.fMessages) > 0:
            for fMessage in response.fMessages:
                self.cli_write(fMessage)
                logger.error(fMessage)
                self.headerMessages.append(fMessage)
            
    def show_files(self):
        """Display a list of a user's files on Filelocker
        
        This function requests the list of a user's files and builds a table that 
        shows the file ID, the file's size (with standard suffix), whether or not 
        the file has passed a virus scan on the Filelocker server, and the 
        file's name.
        """
        data = urllib.urlencode({'format': 'cli'})
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/xml"}
        response = self.send_data("/file_interface/get_user_file_list", data, headers)
        if len(response.sMessages) > 0:
            for sMessage in response.sMessages:
                self.cli_write(sMessage)
        if len(response.fMessages) > 0:
            for fMessage in response.fMessages:
                self.cli_write(fMessage)
                logger.error(fMessage)
        if len(response.data) > 0:
            self.myFileList = []
            self.cli_write("Your Files:\nID\tSize\tScan?\tName\n%s","-"*40)
            for myFile in response.data:
                fsSuffix = "B"
                fileSize = long(myFile['size'])
                if fileSize > 1024:
                    fileSize = fileSize / 1024
                    fsSuffix = "kB"
                    if fileSize > 1024:
                        fileSize = fileSize / 1024
                        fsSuffix = "MB" 
                        if fileSize > 1024:
                            fileSize = round(float(fileSize)/1024,2)
                            fsSuffix = "GB"
                scanned = "Yes" if bool(myFile['passedAvScan']) else "No"
                self.cli_write("%s\t%s\t%s\t%s" % (myFile['id'], "%s%s" % (fileSize, fsSuffix), scanned, myFile['name']))
                self.myFileList.append({'id': myFile['id']})
            self.cli_write("%s","-"*40) 
        else:
            self.cli_write("You have no files")
            sys.exit(0)
    
    def show_groups(self):
        """Display a list of a user's groups on Filelocker
        
        This function requests the list of a user's groups and builds a table that 
        shows the group ID and the group's name.
        """
        data = urllib.urlencode({'format': 'cli'})
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/xml"}
        response = self.send_data("/group_interface/get_groups", data, headers)
        if len(response.sMessages) > 0:
            for sMessage in response.sMessages:
                self.cli_write(sMessage)
        if len(response.fMessages) > 0:
            for fMessage in response.fMessages:
                self.cli_write(fMessage)
                logger.error(fMessage)
        if len(response.data) > 0:
            self.cli_write("Your Groups:\nID\tName\n%s","-"*40)
            for group in response.data:
                self.cli_write("%s\t%s" % (group['id'], group['name']))
            self.cli_write("%s","-"*40)
        else:
            self.cli_write("You have no groups")
            sys.exit(0)
    
# Helper Functions
    def send_data(self, path, data, headers):
        """Send a request to the specified Filelocker server
        
        This function handles the processing of requests to a Filelocker server.
        """
        try:
            request = urllib2.Request(self.serverLocation + path, data, headers)
            response = self.installedHandler.open(request)
            return self.parse_XML_response(response.read())
        #except IOError, ioe:
            #self.check_server_messages()
        except urllib2.HTTPError, he:
            self.cli_write("[Critical]: HTTP %s", he.code)
            logger.critical("HTTP %s", he.code)
            sys.exit(0)
        except urllib2.URLError, ue:
            self.cli_write("[Critical]: URL Error %s", ue.reason)
            logger.critical("HTTP %s: %s", ue.reason)
            sys.exit(0)
        except RuntimeError:
            self.cli_write("Unable to contact Filelocker server at %s" % self.serverLocation)
            logger.error("Unable to contact Filelocker server at %s" % self.serverLocation)
            sys.exit(0)
        except Exception, e:
            self.cli_write("[Critical]: %s", str(e))
            logger.critical(str(e))
            sys.exit(0)
    
    def check_server_messages(self):
        """Check for success and failure messages stored in the user's session
        
        This function checks the user's session for any success or failure 
        messages. Sometimes, these messages can not make it back to the client 
        so they are stored in the user's session for later retrieval.
        """
        data = urllib.urlencode({'format': 'cli'})
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/xml"}
        response = self.send_data("/get_server_messages", data, headers)
        if len(response.sMessages) > 0:
            for sMessage in response.sMessages:
                self.cli_write(sMessage)
                logger.info(sMessage)
                self.headerMessages.append(sMessage)
        if len(response.fMessages) > 0:
            for fMessage in response.fMessages:
                self.cli_write(fMessage)
                logger.error(fMessage)
                self.headerMessages.append(fMessage)
            sys.exit(0)
    
    def parse_XML_response(self, response):
        """Parse an XML response from the Filelocker server
        
        This function parses the Filelocker-standard format XML response that is 
        sent following every Filelocker action. This XML response contains success 
        messages, failure messages, and data.
        """
        rh = self.ResponseHandler()
        parseString(response, rh)
        return rh
    
    def md5_for_file(self, filePath):
        """Determine the MD5 hash for a given file
        
        This function reads a local file and determines its MD5 hash. This process 
        reconciles the differences between the "hashlib" and "md5" Python modules 
        as either one could be loaded depending on the environment.
        """
        if hashlibLoaded:
            md5File = hashlib.md5()
        if md5Loaded:
            md5File = md5.new()
        try:
            f = open(filePath, "rb")
            while True:
                block = f.read(CHUNK_SIZE)
                if not block: 
                    f.close()
                    break
                md5File.update(block)
            return md5File.hexdigest()
        except Exception,e:
            self.cli_write("[Critical]: %s", str(e))
            logger.critical(str(e))
    
    def redraw_header(self):
        """Determine the MD5 hash for a given file
        
        This function reads a local file and determines its MD5 hash. This process 
        reconciles the differences between the "hashlib" and "md5" Python modules 
        as either one could be loaded depending on the environment.
        """
        if self.clearScreen:
            if os.name == 'posix':
                os.system("clear")
            else:
                os.system("cls")
        while len(self.headerMessages) > 0:
            print self.headerMessages.pop(0)
        print "Welcome, %s, to the command line interface for Filelocker" % self.userId
    
    def async(fn):
        """Decorator that converts functions to run in a separate thread
        
        Author:    Jim Dalton
        Location:  http://forr.st/~1Y2
        I wanted to be able to easily make any function run asynchronously, 
        and reduce the acrobatics I was frequently performing to run unit 
        tests against the original function. So I came up with @async. The 
        @async decorator can be applied to any function to make it run 
        asynchronously (i.e. in a separate thread). The original function 
        is stored in the _original attribute of the new function, in case 
        you need to retrieve it (e.g. for testing purposes).
        """
        @wraps(fn)
        def asyncified(*args, **kwargs):
            thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
            thread.start()
            return thread
        asyncified._original = fn
        return asyncified
    
    @async
    def poll_upload(self, fileName):
        """Poll the Filelocker server for statistics about current uploads
        
        This function (meant to be ran in a separate thread) initiates a 
        request to Filelocker once per second to pull live statistics about 
        the uploads in progress. Each response is parsed and a progress bar 
        is generated and displayed to the user. Once the upload finishes, an 
        indeterminate progress indicator in the form of an ellipsis is 
        displayed while the file is being scanned and/or encrypted.
        """
        data = urllib.urlencode({'format': 'cli'})
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/xml"}
        time.sleep(2) # Let the file upload process begin so upload_stats has some data for us.
        alreadyEncrypting = False
        ellipsisCount = 3
        response = self.send_data("/file_interface/upload_stats", data, headers)
        if len(response.data) > 0:
            self.cli_write("Uploading %s...", fileName)
            logger.info("Uploading %s", fileName)
            while len(response.data) > 0:
                for statFile in response.data:
                    if statFile['fileName']==fileName:
                        if statFile['status']=="Uploading":
                            percent = float(statFile['transferredKB']) / float(statFile['sizeKB']) * 100
                            percent = int(percent)
                            half = percent/2
                            if half % 2==1:
                                half += 1
                            progBar = ("="*half) + (" "*(50-half))
                            self.cli_write("\r%s [%s]", (str(percent).zfill(2) + "%", progBar), True)
                        else:
                            if alreadyEncrypting==False:
                                progBar = "="*49
                                self.cli_write("\r%s [%s]", ("100%", progBar), True)
                                self.cli_write("")
                                alreadyEncrypting = True
                            ellipsis = ("."*(ellipsisCount%4)) + (" "*(4-ellipsisCount%4))
                            self.cli_write("\r%s %s%s", (statFile['status'], statFile['fileName'], ellipsis), True)
                            ellipsisCount += 1
                time.sleep(1)
                response = self.send_data("/file_interface/upload_stats", data, headers)
            self.cli_write("")
            
    @async
    def poll_download(self, fileName, filePath, fileSize):
        """Poll the Filelocker server for statistics about current downloads
        
        This function (meant to be ran in a separate thread) runs os.stat on a 
        local file that is being downloaded. The response is parsed and a 
        progress bar is generated and displayed to the user. If the download 
        is prematurely terminated, the user is notified.
        """
        self.cli_write("Downloading %s...", fileName)
        time.sleep(2) # Let the file download process begin so the OS has some data for us.
        try:
            fileSizeDownloaded = os.stat(filePath)[stat.ST_SIZE]
            while fileSizeDownloaded is not None:
                if fileSizeDownloaded==long(fileSize):
                    break
                percent = float(fileSizeDownloaded) / float(fileSize) * 100
                percent = int(percent)
                half = percent/2
                if half % 2==1:
                    half += 1
                progBar = ("="*half) + (" "*(50-half))
                self.cli_write("\r%s [%s]", (str(percent).zfill(2) + "%", progBar), True)
                time.sleep(1)
                fileSizeDownloaded = os.stat(filePath)[stat.ST_SIZE]
            progBar = "="*49
            self.cli_write("\r%s [%s]", ("100%", progBar), True)
            self.cli_write("")
        except OSError, oe:
            self.cli_write("")
            self.cli_write("Download interrupted, restarting...")
        
    def cli_write(self, output, format=None, useStdOut=False):
        """Display text to the user
        
        This function abstracts the various ways in which text can be 
        displayed to the user. Additionally, since every text display is 
        brokered through this function, it is only necessary to check for 
        "quiet mode" once in the entire program.
        """
        if self.isQuiet is False:
            if useStdOut:
                if format is not None:
                    sys.stdout.write(output % format)
                else:
                    sys.stdout.write(output)
                sys.stdout.flush()
            else:
                print output % format if format is not None else output
                    
    def split_list_sanitized(self, cs_list):
        """Filter out empty list items"""
        cleanList = []
        if cs_list is not None:
            for listItem in cs_list.split(','):
                if listItem is not None and listItem !="":
                    cleanList.append(listItem)
        return cleanList
    
    class ResponseHandler(handler.ContentHandler):
        """Override of XML.SAX's ContentHandler for parsing XML
        
        This class provides standard mechanisms for parsing the standard 
        Filelocker XML response.
        """
        def __init__(self):
            """Initialization function for ResponseHandler"""
            self.isInfoElement = False
            self.isErrorElement = False
            self.isUpFileElement = False
            self.isFileElement = False
            self.isGroupElement = False
            self.sMessages = []
            self.fMessages = []
            self.data = []
        def startElement(self, name, attrs):
            """Parsing mechanisms for the beginning of each XML element.
            
            This function saves data that is parsed from the standard 
            Filelocker XML response into class variables.
            """
            if name=="info":
                self.isInfoElement = True
            elif name=="error":
                self.isErrorElement = True
            elif name=="upFile":
                self.fileUploadStatus = attrs.get('status',"")
                self.fileUploadTransferredKB = attrs.get('transferredKB',"")
                self.fileUploadSizeKB = attrs.get('sizeKB',"")
                self.fileUploadFileName = attrs.get('fileName',"")
                self.fileUploadETA = attrs.get('eta',"")
                self.fileUploadSpeed = attrs.get('speed',"")
            elif name=="file":
                self.fileId = attrs.get('id', "")
                self.fileName = attrs.get('name',"")
                self.fileSize = attrs.get('size',"")
                self.filePassedAvScan = attrs.get('passedAvScan',"")
            elif name=="group":
                self.groupId = attrs.get('id', "")
                self.groupName = attrs.get('name',"")
            return
        def endElement(self, name):
            """Parsing mechanisms for the end of each XML element.
            
            This function saves data that is parsed from the standard 
            Filelocker XML response into class variables.
            """
            if name=="info":
                self.isInfoElement = False
            elif name=="error":
                self.isErrorElement = False
            elif name=="upFile":
                self.data.append({
                    "status": self.fileUploadStatus,
                    "transferredKB": self.fileUploadTransferredKB,
                    "sizeKB": self.fileUploadSizeKB,
                    "fileName": self.fileUploadFileName,
                    "eta": self.fileUploadETA,
                    "speed": self.fileUploadSpeed
                })
            elif name=="file":
                self.data.append({
                    "id": self.fileId,
                    "name": self.fileName,
                    "size": self.fileSize,
                    "passedAvScan": self.filePassedAvScan,
                })
            elif name=="group":
                self.data.append({
                    "id": self.groupId,
                    "name": self.groupName
                })
            return
        def characters(self, ch):
            """Parsing mechanisms for data between open and close tags
            
            This function saves data that is parsed from the standard 
            Filelocker XML response into class variables.
            """
            if(self.isInfoElement):
                self.sMessages.append(ch)
            if(self.isErrorElement):
                self.fMessages.append(ch)

if __name__=='__main__':
    def split_and_check(string, callback, scope=None):
        """Split a comma-separated list of IDs and make sure each is a digit"""
        for s in string.split(","):
            if s.isdigit() is False:
                return callback() if scope is None else callback(scope)
        return string
    def prompt_file_path():
        """Prompt for a file path and verify the input as a valid path"""
        s = raw_input("Enter a path to a file you wish to upload [q to quit]: ").strip()
        if s=="q":
            sys.exit(0)
        if s != "":
            if (s[:1]==s[-1:]=='"') or (s[:1]==s[-1:]=="'"):
                s = s[1:-1]
            if os.path.isfile(s)==False:
                print "This is not a valid file path."
                return prompt_file_path()
            return s
        else:
            return prompt_file_path()
    def prompt_file_id():
        """Prompt for a file ID and verify the input as a valid ID"""
        cfl.show_files()
        s = raw_input("Enter a file ID [q to quit]: ").strip().lower()
        if s=="q":
            sys.exit(0)
        return split_and_check(s, prompt_file_id)
    def prompt_target_id(scope):
        """Prompt for a target ID and verify the input as a valid ID"""
        if scope=="group":
            cfl.show_groups()
            s = raw_input("Enter a target group ID [q to quit]: ").strip().lower()
            if s=="q":
                sys.exit(0)
            return split_and_check(s, prompt_target_id, scope)
        elif scope=="user":
            s = raw_input("Enter a target user ID [q to quit]: ").strip().lower()
            if s=="q":
                sys.exit(0)
            return s if s != "" else prompt_target_id(scope)
        else:
            sys.exit(0)
    def prompt_user_id():
        """Prompt for a user ID and verify the input as a valid ID"""
        s = raw_input("Enter your user ID [q to quit]: ").strip().lower()
        if s=="q":
            sys.exit(0)
        return s if s != "" else prompt_user_id()
            
    cfl = None
    usage = "usage: %prog [-mqs] [-a action] [-c config] [-d directory]\n\t\t\t[-f file] [-i file_id1,file_id2...]\n\t\t\t[-t target_id1,target_id2...] [-u user_id]"
    description = "Filelocker is a web based secure file sharing application which facilitates easy file sharing between users at an organization and promotes secure data sharing habits. The command line interface to Filelocker offers advanced users a way to script standard Filelocker actions in a headless environment."
    epilog = "To begin using Filelocker CLI, log in to your organization's web interface for Filelocker. Click \"Account\" in the upper-right corner of the page. Choose \"Advanced\" and enter the IP address of the host from which you will be running Filelocker CLI. Click \"Generate CLI Key\" and click the Save/Download icon under \"Actions\" for the IP you just added. Download the resulting configuration file and copy it to the host you specified earlier. By default, Filelocker CLI will look in the current working directory for the configuration file, but you may specify an alternate location with -c."
    p = OptionParser(description=description, epilog=epilog, usage=usage, version="%prog " + __version__)
    
    p.add_option("-m", "--md5", action="store_true", dest="md5", default=False, help="Show MD5 hash values for uploaded files if the required libraries are loaded.")
    p.add_option("-q", "--quiet", action="store_true", dest="quiet", default=False, help="Quiet mode: disables all non-menu output (e.g. upload progress bars).")
    p.add_option("-s", "--scan", action="store_false", dest="scan", default=True, help="Disable virus scan for this file (default action is to conduct a scan).")
    
    p.add_option("-a", "--action", action="store", dest="action", help="Action to perform (upload, upload_and_share_user, upload_and_share_group, share_user, share_group, download, delete).")
    p.add_option("-c", "--config", action="store", dest="config", help="Specify the location of the config file. Defaults to filelocker_cli.conf in the current directory.")
    p.add_option("-d", "--directory", action="store", dest="directory", help="Local directory for downloaded files.")
    p.add_option("-f", "--file", action="store", dest="file", help="File path of file to be uploaded.")
    p.add_option("-i", "--fid", action="store", dest="file_id", help="File ID of file to be downloaded.  Comma-separated lists of IDs are allowed.")
    p.add_option("-t", "--tid", action="store", dest="target_id", help="User or group ID of the user or group with whom you are sharing a file.  Comma-separated lists of IDs are allowed.")
    p.add_option("-u", "--uid", action="store", dest="user_id", help="User ID associated with the CLI key in Filelocker_cli.conf.")
    options, args = p.parse_args()
    
    if options.user_id is None:
        if options.quiet is False:
            options.user_id = prompt_user_id()
        else:
            logger.error("Action failed: specify a user ID with -u")
            sys.exit(0)
    cfl = CLI_Filelocker(options.user_id, options.md5, options.quiet, options.scan, options.directory, options.config)
    if options.directory is not None:
        if os.path.isdir(options.directory):
            if options.directory[-1] == os.path.sep:
                cfl.directory = options.directory[:-1]
        else:
            print "The specified download directory is not a valid directory, defaulting to current directory..."
            logger.error("The specified download directory is not a valid directory, defaulting to current directory.")
            cfl.headerMessages.append("The specified download directory is not a valid directory, defaulting to current directory...")
            cfl.directory = None
    if options.action:
        options.action = options.action.lower()
        if options.action=="upload":
            if options.file is None:
                if options.quiet is False:
                    print "Upload failed: specify a file with -f"
                logger.error("Upload failed: specify a file with -f")
                sys.exit(0)
            cfl.upload(options.file)
        elif options.action=="upload_and_share_user":
            if options.file is None:
                if options.quiet is False:
                    print "Upload and share failed: specify a file with -f"
                logger.error("Upload and share failed: specify a file with -f")
                sys.exit(0)
            if options.target_id is None:
                if options.quiet is False:
                    print "Upload and share failed: specify a target user ID with -t"
                logger.error("Upload and share failed: specify a target user ID with -t")
                sys.exit(0)
            cfl.upload_and_share(options.file, options.target_id, "user")
        elif options.action=="upload_and_share_group":
            if options.file is None:
                if options.quiet is False:
                    print "Upload and share failed: specify a file with -f"
                logger.error("Upload and share failed: specify a file with -f")
                sys.exit(0)
            if options.target_id is None:
                if options.quiet is False:
                    print "Upload and share failed: specify a target group ID with -t"
                logger.error("Upload and share failed: specify a target group ID with -t")
                sys.exit(0)
            cfl.upload_and_share(options.file, options.target_id, "group")
        elif options.action=="share_user":
            if options.file_id is None:
                if options.quiet is False:
                    print "Share failed: specify a file ID with -i"
                logger.error("Share failed: specify a file ID with -i")
                sys.exit(0)
            if options.target_id is None:
                if options.quiet is False:
                    print "Share failed: specify a target user ID with -t"
                logger.error("Share failed: specify a target user ID with -t")
                sys.exit(0)
            cfl.share(options.file_id, options.target_id, "user")
        elif options.action=="share_group":
            if options.file_id is None:
                if options.quiet is False:
                    print "Share failed: specify a file ID with -i"
                logger.error("Share failed: specify a file ID with -i")
                sys.exit(0)
            if options.target_id is None:
                if options.quiet is False:
                    print "Share failed: specify a target group ID with -t"
                logger.error("Share failed: specify a target group ID with -t")
                sys.exit(0)
            cfl.share(options.file_id, options.target_id, "share")
        elif options.action=="download":
            if options.file_id is None:
                if options.quiet is False:
                    print "Download failed: specify a file ID with -i"
                logger.error("Download failed: specify a file ID with -i")
                sys.exit(0)
            cfl.download(options.file_id)
        elif options.action=="delete":
            if options.file_id is None:
                if options.quiet is False:
                    print "Delete failed: specify a file ID with -i"
                logger.error("Delete failed: specify a file ID with -i")
                sys.exit(0)
            cfl.delete(options.file_id)
        #elif options.action.encode('base64','strict')=="c3RvcA==\n":
            #f = lambda a: "".join(chr(int(str(s[0]),s[1])) for s in a)
            #print f([[20,36],[89,11],[74,15],[214,7],[203,7],[222,7],[24,14],[44,20],[63,17],[1231,4],[85,12]])
            #sys.exit(0)
        else:
            if options.quiet is False:
                print "Invalid action"
            logger.error("Invalid action")
            sys.exit(0)
    else:
        cfl.start_interactive(p)