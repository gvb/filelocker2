# -*- coding: utf-8 -*-
def check_modules():
    try:
        from ConfigParser import ConfigParser
        import cherrypy
        import cgi
        import logging
        import mimetypes
        import os
        import re
        import random
        import signal, errno
        import sys
        import subprocess
        import shutil
        from subprocess import call
        import StringIO
        import stat
        import urllib
        import subprocess
        from Cheetah.Template import Template
        import tempfile
        import datetime,time
        import json
        import getpass
        from twisted.plugin import getPlugins, IPlugin
        try: #This bit here is to handle backwards compatibility with python-json modules. The .write and .dumps methods work analagously as far as I can tell
            json.write("test")
        except AttributeError, ae:
            json.dumps("test")
        try:
            from hashlib import md5
        except ImportError, ie:
            from md5 import md5
        return True
    except Exception, e:
        import sys
        print "You are missing a requisite package: %s." % str(e)
        sys.exit(0)
        
def get_previous_value(section, item, datatype=None):
    try:
        if datatype is None:
            previousValue = preConfig.get(section, item).replace("\"","")
        elif datatype == "int":
            previousValue = preConfig.getint(section, item)
        elif datatype == "boolean":
            previousValue = preConfig.getboolean(section, item)
    except Exception, e:
        print "No previous config entry for %s. Default will be \"%s\"." % (item, defaultValues[item])
        previousValue = defaultValues[item]
    return previousValue

if __name__=='__main__':
    check_modules()
    import ConfigParser
    from getpass import getpass
    import os
    import sys
    defaultValues = {}
    defaultValues['dbtype'] = "mysql"
    defaultValues['dbuser'] = "filelocker"
    defaultValues['dbpassword'] = "none set"
    defaultValues['dbhost'] = "localhost"
    defaultValues['dbname'] = "filelocker"
    defaultValues['vault'] = os.path.join(os.getcwd(), "vault")
    defaultValues['rooturl'] = "http://localhost:8080"
    defaultValues['rootpath'] = os.getcwd()
    defaultValues['log.access_file'] = os.getcwd()
    defaultValues['log.error_file'] = os.getcwd()
    defaultValues['server.socket_port'] = 8080
    defaultValues['tools.sessions.secure'] = False
    defaultValues['server.socket_host'] = "0.0.0.0"
    defaultValues['tools.sessions.storage_type'] = "ram"
    defaultValues['tools.staticdir.on'] = False
    configDict = {}
    configDict['database'] = {}
    configDict['filelocker'] = {}
    configDict['global'] = {}
    supportedDBs = ["mysql",]
    supportedDirectories = ["ldap", "local"]
    supportedAuthentication = ["cas", "ldap", "local"]
    
    # Filelocker Configuration
    print "===== Filelocker Configuration Wizard ====="
    configFile = raw_input("Where would you like to save the config file? [%s%sconf%sfilelocker.conf]: " % (os.getcwd(), os.path.sep, os.path.sep))
    if configFile is None or configFile == "":
        configFile = "%s%sconf%sfilelocker.conf" % (os.getcwd(), os.path.sep, os.path.sep)
    preConfig = None
    if os.path.exists(configFile):
        try:
            preConfig = ConfigParser.RawConfigParser()
            preConfig.read(configFile)
            print "Found existing configuration file, loading previous values as defaults."
        except Exception, e:
            print "Found existing configuration file, but there were problems importing the data. Creating config from scratch."
    
    # Database Setup
    tryDatabaseConfig = True
    previousValue = None
    while tryDatabaseConfig:
        # Database Type
        previousValue = get_previous_value("database", "dbtype")
        dbType = raw_input("What kind of database will you be using (mysql)? [%s]: " % previousValue)
        if dbType is None or dbType == "":
            dbType = previousValue
        while dbType not in supportedDBs:
            dbType=raw_input("Invalid database type. (t)ry again or (e)xit?: ")
            if dbType == "e":
                sys.exit(0) #Exit point if they don't have any supported databases
        # Database User
        previousValue = get_previous_value("database", "dbuser")
        dbUser = raw_input("Database user? [%s]: " % previousValue)
        if dbUser is None or dbUser == "":
            dbUser = previousValue
        dbPassword = None
        # Database Password
        previousValue = get_previous_value("database", "dbpassword")
        while dbPassword == None or dbPassword == "":
            dbPassword = getpass("Database password? [%s]: " % previousValue)
            if (dbPassword == None or dbPassword == "") and previousValue == "none set":
                print "Database password cannot be blank."
            elif (dbPassword == None or dbPassword == "") and previousValue != "none set":
                dbPassword = previousValue
        # Database Host
        dbHost = None
        while dbHost == None:
            previousValue = get_previous_value("database", "dbhost")
            dbHost = raw_input("Database host? [%s]: " % previousValue)
            if dbHost == None or dbHost == "":
                dbHost = previousValue
        # Database Name
        previousValue = get_previous_value("database", "dbname")
        dbName = raw_input("Database name? [%s]: " % previousValue)
        if dbName is None or dbName == "":
            dbName = previousValue
        # Database Connection Test
        connection = None
        try:
            if dbType == "mysql":
                import MySQLdb, warnings
                warnings.filterwarnings("ignore", "Unknown table.*")
                from core.dao.MySQLDAO import INIT_TABLE_DELETE_SQL, INIT_TABLE_CREATE_SQL, INIT_DATA_SQL
                connection = MySQLdb.connect(dbHost,  dbUser, dbPassword, dbName)
                print "Database connection successful."
            else:
                print "Unsupported database type specified."
                sys.exit(0)
            initializeDB = raw_input("Would you like to initialize the database (y/n) WARNING: if the database already exists, all data will be lost)? [n]: ")
            if initializeDB == "y" or initializeDB == "yes":
                cursor = connection.cursor(cursorclass=MySQLdb.cursors.DictCursor)
                for query in INIT_TABLE_DELETE_SQL:
                    cursor.execute(query, None)
                for query in INIT_TABLE_CREATE_SQL:
                    cursor.execute(query, None)
                for query in INIT_DATA_SQL:
                    cursor.execute(query, None)
                cursor.close()
                cursor = None
            connection.close()
            tryDatabaseConfig = False
        except Exception, e:
            print "Unable to connect to MySQL database: %s" % str(e)
            resp = raw_input("Try database setup again? [y/n]: ")
            if resp == "y" or resp=="yes":
                tryDatabaseConfig = True
            else:
                sys.exit(0)
        configDict['database']['dbtype'] = dbType
        configDict['database']['dbhost'] = dbHost
        configDict['database']['dbuser'] = dbUser
        configDict['database']['dbpassword'] = dbPassword
        configDict['database']['dbname'] = dbName
    # End Database Setup
    
    # Vault Setup
    tryVaultLocation = True
    while tryVaultLocation:
        print "The vault is the folder where you want Filelocker to store all of the uploaded files and messages."
        print "This folder should not have any other contents besides files managed by Filelocker, as Filelocker will consider them to be orphaned files and will purge them."
        previousValue = get_previous_value("filelocker", "vault")
        vaultLocation = raw_input("Where should Filelocker store uploaded files (the 'vault')? [%s]: " % previousValue)
        if vaultLocation == "exit":
            sys.exit(0)
        if vaultLocation == None or vaultLocation == "":
            vaultLocation = previousValue
        if os.path.exists(vaultLocation):
            try:
                if vaultLocation.endswith(os.path.sep):
                    vaultLocation = vaultLocation[:-1]
                f = open("%s%stest.txt" % (vaultLocation, os.path.sep), "w")
                f.write("test")
                f.close()
                os.remove("%s%stest.txt" % (vaultLocation, os.path.sep))
                print "File creation and deletion test successful."
                tryVaultLocation = False
            except Exception, e:
                print "Filelocker could not write a file to this location as the current user (Error: %s)." % str(e)
                print "If Filelocker is going to be run under a different user account than the one being used to run this setup program, this may not be a problem."
                resp = raw_input("If you would like to specify a new location, please enter it here. Otherwise, just hit Enter to continue: ")
                if resp != None and resp != "":
                    tryVaultLocation = True
                else:
                    tryVaultLocation = False
            configDict['filelocker']['vault'] = vaultLocation
        else:
            print "This path does not exist or is not readable. Please try another path or type \"exit\" to quit."
            tryVaultLocation = True
    # End Vault Setup
    
    # Location Setup
    previousValue = get_previous_value("filelocker", "rooturl")
    filelockerURL = raw_input("What is the URL that people will use to access Filelocker? [%s]: " % previousValue)
    if filelockerURL == None or filelockerURL == "":
        filelockerURL = previousValue
    configDict['filelocker']['rooturl'] = filelockerURL
    previousValue = get_previous_value("filelocker", "rootpath")
    filelockerPath = raw_input("Where will Filelocker be installed? [%s]: " % previousValue)
    if filelockerPath is None or filelockerPath == "":
        filelockerPath = previousValue
    configDict['filelocker']['rootpath'] = filelockerPath
    # End Location Setup

    # Logging Setup
    tryLogLocation = True
    while tryLogLocation:
        logFile = get_previous_value("global", "log.error_file").split(os.path.sep)[-1]
        previousValue = get_previous_value("global", "log.error_file").replace(logFile, "")
        logLocation = raw_input("Where should Filelocker store its error and access logs? [%s]: " % previousValue)
        if logLocation is None or logLocation == "":
            logLocation = previousValue
        if os.path.exists(logLocation):
            try:
                if logLocation.endswith(os.path.sep):
                    logLocation = logLocation[:-1]
                f = open("%s%stest.txt" % (logLocation, os.path.sep), "w")
                f.write("test")
                f.close()
                os.remove("%s%stest.txt" % (logLocation, os.path.sep))
                print "File creation and deletion test successful."
                tryLogLocation = False
            except Exception, e:
                print "Filelocker could not write a file to this location as the current user (Error: %s)." % str(e)
                print "If Filelocker is going to be run under a different user account than the one being used to run this setup program, this may not be a problem."
                resp = raw_input("If you'd like to specifify a new location, please enter it here. Otherwise, just hit Enter to continue: ")
                if resp != None and resp != "":
                    tryLogLocation = True
                else:
                    tryLogLocation = False
            configDict['global']['log.access_file'] = "%s%sfilelocker.access.log" % (logLocation, os.path.sep)
            configDict['global']['log.error_file'] = "%s%sfilelocker.error.log" % (logLocation, os.path.sep)
        else:
            print "This path does not exist or is not readable. Please try another path or type \"exit\" to quit."
            tryLogLocation = True
    # End Logging Setup
    
    # Bootstrap Filelocker application
    print "Trying to bootstrap Filelocker..."
    fl = None
    from core.dao.models.FLError import FLError
    try:
        from core.Filelocker import Filelocker
        from core.dao.models.User import User
        fl = Filelocker(configDict)
        print "Filelocker successfully loaded."
        #Set up admin user
        resp = raw_input("Would you like to set up an admin user? (You should have at least 1 admin) [y/n]: ")
        if resp == "y" or resp == "yes":
            userId = raw_input("   Username for admin user: ")
            firstName = raw_input("   First Name: ")
            lastName = raw_input("   Last Name: ")
            email = raw_input("   Email: ")
            password, confPassword, continueSetup = "a", "b", True
            while password != confPassword and continueSetup:
                password = getpass("   Password: ")
                confPassword = getpass("   Confirm Password: ")
                if password != confPassword:
                    resp = raw_input("Passwords do not match! Try again? [y/n]: ")
                    if resp != "y" and resp != "yes":
                        continueSetup = False
            adminUser = User(firstName, lastName, email, 1024, None, None, userId)
            fl.db.createUser(adminUser, password)
            fl.db.grantUserPermission(adminUser.userId, "admin")
        print "Local authentication can be used in cases where external authentication is not working properly by directing a web browser to %s/local" % configDict['filelocker']['rooturl']
        #End Admin user setup
    except FLError, fle:
        print "Problems when executing Filelocker functions: %s" % str(fle)
    except Exception, e:
        print "Could not bootstrap Filelocker: %s. Please run setup again." % str(e)
        sys.exit(0)
    # End Bootstrap Filelocker Application
    # End Filelocker Configuration
    
    # CherryPy Configuration
    print "====CherryPy Webserver Config Wizard===="
    # CherryPy Port
    configPort = True
    while configPort:
        previousValue = get_previous_value("global", "server.socket_port", "int")
        port = raw_input("What port will the application server run on? [%s]: " % previousValue)
        if port is None or port == "":
            port = previousValue
            configPort = False
        elif int(port) >0 and int(port) < 65536:
            port = int(port)
            configPort = False
        else:
            resp =  "Invalid port. Must be between 1 and 65536. Try again? [y/n]: "
            if resp == "yes" or resp == "y":
                configPort = True
        configDict['global']['server.socket_port']=port
    # CherryPy Secure Session
    configSecureSession = True
    while configSecureSession:
        print "In a production environment, session cookies should be set to secure. This means that the cookies will not be sent over a non-secured (HTTP as opposed to HTTPS) connection. However, if you are troubleshooting or running a dev instance over a non-encrypted connection, cookies will not work with this attribute set."
        previousValue = "n"
        secure = get_previous_value("global", "tools.sessions.secure", "boolean")
        if secure:
            previousValue = "y"
        resp = raw_input("Would you like to enable secure session cookies(y/n)? [%s]: " % previousValue)
        if resp is None or resp =="":
            resp = previousValue
        if resp == "yes" or resp=="y":
            configDict['global']['tools.sessions.secure']=True
            configSecureSession = False
        else:
            print "WARNING: Session cookies have not been set to secure. This value can be reset by editing the config file directly and restarting the server."
            configDict['global']['tools.sessions.secure']=False
            configSecureSession = False
    # CherryPy Socket Host
    configSocketHost = True
    while configSocketHost:
        previousValue = get_previous_value("global", "server.socket_host")
        socketHost = raw_input("If you would like the server to only respond to requests on a certain IP address, please enter it here. Hit enter to accept requests on all interfaces and IPs [%s]: " % previousValue)
        if socketHost is None or socketHost =="":
            configDict['global']['server.socket_host']=previousValue
            configSocketHost = False
        else:
            configDict['global']['server.socket_host']=socketHost
            configSocketHost = False
    # CherryPy Session Type
    configSessionType = True
    while configSessionType:
        print "If you only plan to run one Filelocker application server, you should set your session type to \"ram\""
        print "However, if you are setting up multiple servers in a load balanced cluster, you should save session info in the database by typing \"db\""
        previousValue = get_previous_value("global", "tools.sessions.storage_type")
        resp = raw_input("How would you like to save session data? [%s]: " % previousValue)
        if resp is None or resp == "":
            resp = previousValue
        if resp.lower() != "ram" and resp.lower() != "db":
            print "Please choose between \"ram\" or \"db\" for your session type."
        else:
            configDict['global']['tools.sessions.storage_type'] = resp
            configSessionType = False
    if resp == "db":
        clusterQuestions = True
        while clusterQuestions:
            cluster = raw_input("You've selected to store sessions in a database. Would you like this server to be part of a cluster? [y/n]: ")
            if cluster.lower() == "y" or cluster.lower() == "yes":
                clusterMaster = raw_input("You need exactly one cluster master to perform maintenance functions for the cluster. Will this server be the cluster master? [y/n]: ")
                if clusterMaster.lower() == "y" or clusterMaster.lower() == "yes":
                    configDict["filelocker"]["clustermaster"] = True
                    configDict["filelocker"]["clustermemberid"]= 0
                    clusterQuestions = False
                else:
                    print "Since this is not the cluster master, this node will need a unique cluster member id. This should be a positive integer greater than 0"
                    clusterMemberId = raw_input("What should the cluster member ID for this node be?: ")
                    while clusterMemberId.isnumeric() != False or clusterMemberId == "0" or clusterMemberId == 0:
                        print "Your response \"%s\" was not a valid number, please enter a positive integer greater than 0 for cluster ID that is unique from all other cluster members!" % clusterMemberId
                        clusterMemberId = raw_input("What should the cluster member ID for this node be?: ")
                    clusterMemberId = int(clusterMemberId)
                    configDict["filelocker"]["clustermaster"] = False
                    configDict["filelocker"]["clustermemberid"] = clusterMemberId
                    clusterQuestions = False
            else:
                configDict["filelocker"]["clustermaster"] = True
                configDict["filelocker"]["clustermemberid"]= 0
                clusterQuestions = False
    # Additional CherryPy Configuration Parameters
    configDict['global']['server.reverse_dns'] = False
    configDict['global']['server.thread_pool'] = 20
    configDict['global']['server.environment'] = "production"
    configDict['global']['engine.autoreload.on'] = False
    configDict['global']['tools.sessions.on'] = True
    configDict['global']['tools.sessions.name'] = "filelocker"
    configDict['global']['tools.sessions.timeout'] = 15
    configDict['global']['log.screen'] = False
    configDict['global']['tools.gzip.mime_types'] = ['text/html', 'text/css', 'image/jpeg', 'image/gif', 'text/javascript', 'image/png']
    configDict['global']['tools.gzip.on'] = True
    
    # CherryPy or Apache Static
    if get_previous_value("/static", "tools.staticdir.on", "boolean"):
        previousValue = "y"
    else:
        previousValue = "n"
    apacheProxy = raw_input("Will Apache be serving the static content for Filelocker (y/n)? [%s]: " % previousValue)
    if apacheProxy is None or apacheProxy == "":
        apacheProxy = previousValue
    if apacheProxy == "n":
        configDict['/static'] = {}
        configDict['/static']['tools.staticdir.root'] = configDict['filelocker']['rootpath']
        configDict['/static']['tools.staticdir.on'] = True
        configDict['/static']['tools.staticdir.dir'] = "static"
    else:
        configDict['global']['tools.proxy.on'] = True
    # End CherryPy Configuration
    
    # Configuration File Creation
    configFileStream = open(configFile, "w")
    for section in configDict:
        configFileStream.write("[%s]\n" % str(section))
        for entry in configDict[section]:
            if isinstance(configDict[section][entry], str):
                configFileStream.write("%s=\"%s\"\n" % (entry, configDict[section][entry]))
            else:
                configFileStream.write("%s=%s\n" % (entry, configDict[section][entry]))
        configFileStream.write("\n")
    configFileStream.close()
    print "Filelocker allows you to reconfigure the authentication, mail settings, directory, and various utility commands on the fly. However, these settings should probably be set before the server starts."
    runSetup = raw_input("Would you like to run the setup script for these settings now (y/n)? [y]: ")
    if runSetup == "y" or runSetup == "yes":
        import webFilelocker2
        webFilelocker2.reconfig(configFile)
    
    print "Finished. To start Filelocker 2 in daemonized mode, type 'python webFilelocker2.py -d -c %s' " % configFile