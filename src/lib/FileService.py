# -*- coding: utf-8 -*-
import os
from stat import ST_SIZE
import random
import cherrypy
import subprocess
from lib.SQLAlchemyTool import session
from lib.Models import *
import os
import subprocess
from lib.SQLAlchemyTool import session
from sqlalchemy import *
from lib.Models import *
from lib.Formatters import *
from lib import Mail
from lib import Encryption
__author__="wbdavis"
__date__ ="$Jan 31, 2012 3:13:19 AM$"


def file_download_complete(user, fileId, publicShareId=None):
    config = cherrypy.request.app.config['filelocker']
    try:
        role = None
        if cherrypy.session.has_key("current_role"):
            role = cherrypy.session.get("current_role")
        flFile = session.query(File).filter(File.id==fileId).one()
        if ((role is not None and flFile.role_owner_id != role.id) or user == None or user.id != flFile.owner_id) and flFile.notify_on_download:
            try:
                owner = None
                if role is not None: owner = session.query(User).filter(User.id==flFile.role_owner_id).one()
                else: owner = session.query(User).filter(User.id==flFile.owner_id).one()
                if owner.email is not None and owner.email != "":
                    orgConfig = get_config_dict_from_objects(session.query(ConfigParameter).filter(ConfigParameter.name.like('org_%')).all())
                    Mail.notify(get_template_file('download_notification.tmpl'),{'sender': None, 'recipient': owner.email, 'fileName': flFile.name, 'downloadUserId': user.id, 'downloadUserName': user.display_name, 'filelockerURL': config['root_url'], 'org_url': orgConfig['org_url'], 'org_name': orgConfig['org_name']})
            except Exception, e:
                cherrypy.log.error("[%s] [file_download_complete] [(1)Unable to notify user %s of download completion: %s]" % (user.id, owner.id, str(e)))

        if publicShareId is not None:
            publicShare = session.query(PublicShare).filter(PublicShare.id == publicShareId).one()
            session.add(AuditLog(flFile.owner_id, "Download File", "File %s downloaded via Public Share. " % str(flFile.name), None, flFile.role_owner_id, flFile.id))
            if flFile.notify_on_download:
                try:
                    owner = None
                    if role is not None: owner = session.query(User).filter(User.id==flFile.role_owner_id).one()
                    else: owner = session.query(User).filter(User.id==flFile.owner_id).one()
                    if owner.email is not None and owner.email != "":
                        orgConfig = get_config_dict_from_objects(session.query(ConfigParameter).filter(ConfigParameter.name.like('org_%')).all())
                        Mail.notify(get_template_file('public_download_notification.tmpl'),{'sender': None, 'recipient': owner.email, 'fileName': flFile.name, 'filelockerURL': config['root_url'], 'org_url': orgConfig['org_url'], 'org_name': orgConfig['org_name']})
                except Exception, e:
                    cherrypy.log.error("[%s] [file_download_complete] [(2)Unable to notify user %s of download completion: %s]" % ("admin", owner.id, str(e)))
            if publicShare.reuse == "single":
                publicShare.files.remove(flFile)
                session.commit()
                publicShare = session.query(PublicShare).filter(PublicShare.id == publicShare.id).one()
                if len(publicShare.files) == 0:
                    session.delete(publicShare)
                    session.add(AuditLog(flFile.owner_id, "Delete Public Share", "File %s (%s) downloaded via single use public share. File is no longer publicly shared." % (flFile.name, flFile.id), None, flFile.role_owner_id, flFile.id))
                    session.commit()
        else:
            log = AuditLog(user.id, "Download File", "File %s downloaded by user %s." % (flFile.name, user.id), flFile.owner_id, role.id if role is not None else None, flFile.id)
            session.add(log)
        session.commit()
    except Exception, e:
        cherrypy.log.error("[%s] [file_download_complete] [Unable to finish download completion: %s]" % ("admin", str(e)))

def get_upload_ticket_by_password(ticketId, password):
    uploadRequest = session.query(UploadRequest).filter(UploadRequest.id == ticketId)
    if uploadRequest is None:
        raise Exception("Invalid Upload Request ID")
    if password == None and uploadRequest.password == None:
        return uploadRequest
    else:
        isValid = lib.Encryption.compare_password_hash(password, uploadRequest.password)
        if isValid and len(uploadRequest.password) == 32:
            newHash = lib.Encryption.hash_password(password)
            uploadRequest.password = newHash
            session.commit() #New has stored in the db
            return uploadRequest
        else:
            raise Exception("You must enter the correct password to access this upload request.")

def get_temp_file():
    config = cherrypy.request.app.config['filelocker']
    fileList, filePrefix, fileSuffix = os.listdir(config['vault']), "[%s]fltmp" % str(config['cluster_member_id']), ".tmp"
    randomNumber = random.randint(1, 1000000)
    tempFileName = os.path.join(config['vault'], filePrefix + str(randomNumber) + fileSuffix)
    while tempFileName in fileList:
        randomNumber = random.randint(1, 1000000)
        tempFileName = os.path.join(config['vault'], filePrefix + str(randomNumber) + fileSuffix)
    file_object = open(tempFileName, "wb")
    return file_object

def check_in_file(tempFileName, flFile):
    config = cherrypy.request.app.config['filelocker']
    filePath = os.path.join(config['vault'], tempFileName)
    #Virus scanning if requested
    avCommand =  session.query(ConfigParameter).filter(ConfigParameter.name=="antivirus_command").one().value
    avCommandList = avCommand.split(" ")
    avCommandList.append(filePath)
    try:
        p = subprocess.Popen(avCommandList, stdout=subprocess.PIPE)
        output = p.communicate()[0]
        if(p.returncode != 0):
            cherrypy.log.error("[%s] [check_in_file] [File %s did not pass requested virus scan, return code: %s, output: %s]" % (flFile.owner_id, flFile.name, p.returncode, output))
            queue_for_deletion(tempFileName)
            flFile.passed_avscan = False
        else:
            flFile.passed_avscan = True
    except OSError, oe:
        cherrypy.log.error("[%s] [check_in_file] [AVSCAN execution failed: %s]" % (flFile.owner_id, str(oe)))
        flFile.passed_avscan = False

    md5sum = None
    try:
        p = subprocess.Popen(["md5sum",filePath], stdout=subprocess.PIPE)
        md5sum = p.communicate()[0].split(" ")[0]
    except Exception, e:
        cherrypy.log.error("Couldn't calculate file md5sum: %s" % str(e))
    flFile.md5 = md5sum
    #Determine file size and check against quota
    try:
        flFile.size = os.stat(filePath)[ST_SIZE]
        if (flFile.owner_id != "system"):
            user = session.query(User).filter(User.id == flFile.owner_id).one()
            if (get_user_quota_usage_bytes(user.id) + flFile.size) >= (user.quota*1024*1024):
                cherrypy.log.error("[%s] [check_in_file] [User has insufficient quota space remaining to check in file: %s]" % (user.id, flFile.name))
                raise Exception("You may not upload this file as doing so would exceed your quota")
    except Exception, e:
        cherrypy.log.error("[%s] [check_in_file] [Couldn't determine file size, using one set from content-length: %s]" % (flFile.owner_id, str(e)))

    #determine file type
    flFile.type = "Unknown"
    try:
        fileCommand = session.query(ConfigParameter).filter(ConfigParameter.name=="file_command").one().value
        fileres = os.popen("%s %s" % (fileCommand, filePath), "r")
        data = fileres.read().strip()
        fileres.close()
        if data.find(";") >= 0:
            (ftype, lo) = data.split(";")
            del(lo)
            flFile.fileType = ftype.strip()
        else:
            flFile.fileType = data.strip()
    except Exception, e:
        cherrypy.log.error("[%s] [checkInFile] [Unable to determine file type: %s]" % (user.id, str(e)))

    #Logic is a little strange here - if the user supplied an encryptionKey, then don't save it with the file
    encryptionKey = None
    flFile.encryption_key = Encryption.generatePassword()
    encryptionKey = flFile.encryption_key
    os.umask(077)
    newFile = open(filePath, "rb")
    f = open(os.path.join(config['vault'], str(flFile.id)), "wb")
    encrypter, salt = Encryption.new_encrypter(encryptionKey)
    padding, endOfFile = (0, False)
    f.write(salt)
    data = newFile.read(1024*8)
    #If File is only one block long, handle it here
    if len(data) < (1024*8):
        padding = 16-(len(data)%16)
        if padding == 16:
            paddingByte = "%X" % 0
        else:
            paddingByte = "%X" % padding
        for i in range(padding): data+=paddingByte
        f.write(encrypter.encrypt(data))
    else:
        while 1:
            if endOfFile: break
            else:
                next_data = newFile.read(1024*8)
                #this only happens if we are at the end, meaning the next block is the last
                #so we have to handle the padding by aggregating the two blocks and determining pad
                if len(next_data) < (1024*8):
                    data+=next_data
                    padding = 16-(len(data)%16)
                    if padding == 16: paddingByte = "%X" % 0
                    else: paddingByte = "%X" % padding
                    for i in range(padding): data+=paddingByte
                    endOfFile = True
            f.write(encrypter.encrypt(data))
            data = next_data

        newFile.close()
        f.close()
        flFile.status = "Checked In"

def clean_temp_files(config, validTempFiles):
    vaultFileList = os.listdir(config['filelocker']['vault'])
    for fileName in vaultFileList:
        try:
            if fileName.endswith(".tmp") and fileName.startswith("[%s]" % config['filelocker']['cluster_member_id']): #This is a temp file and made by this cluster member
                if fileName not in validTempFiles:
                    queue_for_deletion(fileName)
        except Exception, e:
            cherrypy.log.error("[system] [cleanTempFiles] [There was a problem while trying to clean a stale temp file %s: %s]" % (str(fileName), str(e)))

def queue_for_deletion(filePath):
    try:
        if session.query(DeletedFile).filter(DeletedFile.file_name==filePath).scalar() == None:
            session.add(DeletedFile(file_name=filePath))
            session.commit()
    except Exception, e:
        cherrypy.log.error("Unable to queue file for deletion: %s" % str(e))

def process_deletion_queue(config):
    vault = config['filelocker']['vault']
    fileRows = session.query(DeletedFile.file_name).all()
    for fileRow in fileRows:
        try:
            if os.path.isfile(os.path.join(vault, fileRow.file_name)):
                secure_delete(config, fileRow.file_name)
                if os.path.isfile(os.path.join(vault,fileRow.file_name))==False:
                    deletedFile = session.query(DeletedFile).filter(DeletedFile.file_name==fileRow.file_name).scalar()
                    if deletedFile is not None:
                        session.delete(deletedFile)
                        session.commit()
                else:
                    pass
                    #This isn't necessarily an error, it just means that the file finally got deleted
            else:
                deletedFile = session.query(DeletedFile).filter(DeletedFile.file_name==fileRow.file_name).scalar()
                if deletedFile is not None:
                    session.delete(deletedFile)
                    session.commit()
        except Exception, e:
            cherrypy.log.error("[system] [processDeletionQueue] [Couldn't delete file in deletion queue: %s]" % str(e))


def secure_delete(config, fileName):
    import errno
    vault = config['filelocker']['vault']
    deleteConfig = get_config_dict_from_objects(session.query(ConfigParameter).filter(ConfigParameter.name.like('delete_%')).all())
    deleteCommand = deleteConfig['delete_command']
    deleteArguments = deleteConfig['delete_arguments']
    deleteList = []
    deleteList.append(deleteCommand)
    for argument in deleteArguments.split(" "):
        deleteList.append(argument)
    deleteList.append(os.path.join(vault,fileName))
    try:
        p = subprocess.Popen(deleteList, stdout=subprocess.PIPE)
        output = p.communicate()[0]
        if(p.returncode != 0):
            cherrypy.log.error("[%s] [secure_delete] [The command to delete the file returned a failure code of %s: %s]" % ("admin", p.returncode, output))
        else:
            deletedFile = session.query(DeletedFile).filter(DeletedFile.file_name==fileName).scalar()
            if deletedFile is not None:
                session.delete(deletedFile)
                session.commit()
    except OSError, oe:
        if oe.errno == errno.ENOENT:
            cherrypy.log.error("[admin] [secure_delete] [Couldn't delete because the file was not found (dequeing): %s]" % str(oe))
            deletedFile = session.query(DeletedFile).filter(DeletedFile.file_name==fileName).scalar()
            if deletedFile is not None:
                session.delete(deletedFile)
                session.commit()
        else:
            cherrypy.log.error("[admin] [secure_delete] [Generic system error while deleting file: %s" % str(oe))
    except Exception, e:
       cherrypy.log.error("[admin] [secure_delete] [Couldn't securely delete file: %s]" % str(e))

def get_vault_usage():
    s = os.statvfs(cherrypy.request.app.config['filelocker']['vault'])
    freeSpaceMB = int((s.f_bavail * s.f_frsize) / 1024 / 1024)
    totalSizeMB = int((s.f_blocks * s.f_frsize) / 1024 / 1024 )
    return freeSpaceMB, totalSizeMB

def get_user_quota_usage_bytes(userId):
    usage = session.query(func.sum(File.size)).filter(File.owner_id==userId).scalar()
    if usage is None:
        return 0
    else:
        return int(usage)

def get_role_quota_usage_bytes(roleId):
    usage = session.query(func.sum(File.size)).filter(File.role_owner_id==roleId).scalar()
    if usage is None:
        return 0
    else:
        return int(usage)