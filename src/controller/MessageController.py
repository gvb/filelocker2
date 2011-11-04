import cherrypy
import logging
import cgi
from Cheetah.Template import Template
from lib.SQLAlchemyTool import session
from sqlalchemy import *

import AccountController
from lib.Formatters import *
from lib.Models import *
__author__="wbdavis"
__date__ ="$Sep 25, 2011 9:32:23 PM$"

class MessageController:
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def send_message(self, subject, body, recipientIds, expiration, format="json", **kwargs):
        user, sMessages, fMessages = cherrypy.session.get("user"), [], []
        try:
            maxExpiration = datetime.datetime.today() + datetime.timedelta(days=cherrypy.request.app.config['filelocker']['max_file_life_days'])
            expiration = datetime.datetime(*time.strptime(strip_tags(expiration), "%m/%d/%Y")[0:5]) if (kwargs.has_key('expiration') and strip_tags(expiration) is not None and expiration.lower() != "never") else None
            recipientIdList = split_list_sanitized(recipientIds)
            subject= strip_tags(subject)
            #Process the expiration data for the file
            if expiration is None and (AccountController.user_has_permission(user, "expiration_exempt") == False and AccountController.user_has_permission(user, "admin")==False): #Check permission before allowing a non-expiring upload
                expiration = maxExpiration
            else:
                if maxExpiration < expiration and AccountController.user_has_permission(user, "expiration_exempt")==False:
                    raise Exception("Expiration date must be between now and %s." % maxExpiration.strftime("%m/%d/%Y"))
            newMessage = Message(subject=subject, body=body, date_sent=datetime.datetime.now(), owner_id=user.id, date_expires=expiration)
            session.add(newMessage)
            session.commit()
            encrypt_message(newMessage)
            for recipientId in recipientIdList:
                rUser = AccountController.get_user(recipientId)
                if rUser is not None:
                    session.add(ReceivedMessage(message_id=newMessage.id, recipient_id=rUser))
                else:
                    fMessages.append("Could not send to user with ID:%s - Invalid user ID" % str(recipientId))
            session.commit()
            sMessages.append("Message \"%s\" sent." % subject)
        except ValueError:
            fMessages.append("Invalid expiration date format. Date must be in mm/dd/yyyy format.")
        except Exception, e:
            fMessages.append("Could not send message: %s" % str(e))
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_new_message_count(self, format="json", **kwargs):
        user, sMessages, fMessages, newMessageCount = cherrypy.session.get("user"), [], [], []
        try:
            newMessageCount = session.query(func.count(ReceivedMessage.message_id), ReceivedMessage.recipient_id,).filter(ReceivedMessage.recipient_id==user.id).scalar()
        except Exception,e :
            fMessages.append(str(e))
        return fl_response(sMessages, fMessages, format, data=newMessageCount)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_messages(self, format="json", **kwargs):
        user, sMessages, fMessages = cherrypy.session.get("user"), [], []
        messagesList, recvMessagesList, sentMessagesList  = [], [], [] 
        try:
            recvMessages = session.query(ReceivedMessage).filter(ReceivedMessage.recipient_id==user.id).all()
            sentMessages = session.query(Message).filter(Message.owner_id==user.id).all()
            for message in recvMessages:
                messageDict = message.get_dict()
                messageBody = strip_tags(cgi.escape(decrypt_message(message)), True)
                messageDict['body'] = str(Template("$messageBody", searchList=[locals()], filter=WebSafe))
                recvMessagesList.append(messageDict)

            for message in sentMessages:
                messageDict = message.get_dict()
                messageBody = strip_tags(cgi.escape(decrypt_message(message)), True)
                messageDict['body'] = str(Template("$messageBody", searchList=[locals()], filter=WebSafe))
                sentMessagesList.append(messageDict)
            messagesList.append(recvMessagesList)
            messagesList.append(sentMessagesList)
        except Exception, e:
            fMessages.append("Error while retrieving messages: %s" % str(e))
        return fl_response(sMessages, fMessages, format, data=messagesList)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def read_message(self, messageId, format="json", **kwargs):
        user, sMessages, fMessages = cherrypy.session.get("user"), [], []
        try:
            message = session.query(ReceivedMessage).filter(ReceivedMessage.message_id == messageId).one()
            if message.recipient_id == user.id:
                message.date_viewed = datetime.datetime.now()
            else:
                fMessages.append("You do not have permission to read this message")
            session.commit()
        except sqlalchemy.exc.orm.NoResultFound, nrf:
            fMessages.append("Invalid message id")
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def delete_messages(self, messageIds, format="json", **kwargs):
        user, sMessages, fMessages = cherrypy.session.get("user"), [], []
        try:
            #Todo
            messageIdList = split_list_sanitized(messageIds)
            for messageId in messageIdList:
                fl.delete_message(user, messageId)
            sMessages.append("Message(s) deleted")
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)

def decrypt_message(message):
    config = cherrypy.request.app.config['filelocker']
    messageBody = ""
    try:
        path = os.path.join(config['vault'],"m"+str(message.id))
        bodyfile = open(path, 'rb')
        salt = bodyfile.read(16)
        decrypter = Encryption.new_decrypter(message.encryption_key, salt)
        endOfFile = False
        readData = bodyfile.read(1024 * 8)
        data = decrypter.decrypt(readData)
        #If the data is less than one block long, just process it and send it out
        if len(data) < (1024*8):
            padding = int(str(data[-1:]),16) 
            #A 0 represents that the file had a multiple of 16 bytes, and 16 bytes of padding were added
            if padding==0: 
                padding=16
            endOfFile = True
            messageBody += data[:len(data)-padding]
        else:
            #For multiblock files
            while True:
                if endOfFile:
                    break
                next_data = decrypter.decrypt(dFile.read(1024*8))
                if (next_data is not None and next_data != "") and not len(next_data)<(1024*8):
                    yData = data
                    data = next_data
                    messageBody += yData
                #This prevents padding going across block boundaries by aggregating the last two blocks and processing
                #as a whole if the next block is less than a full block (signifying end of file)
                else:
                    data = data + next_data
                    padding = int(str(data[-1:]),16) 
                    #A 0 represents that the file had a multiple of 16 bytes, and 16 bytes of padding were added
                    if padding==0: 
                        padding=16
                    endOfFile = True
                    messageBody += data[:len(data)-padding]
        return messageBody
    except Exception, e:
        raise Exception("Couldn't decrypt message body: %s" % str(e))

def encrypt_message(message):
    config = cherrypy.request.app.config['filelocker']
    try:
        message.encryption_key = Encryption.generatePassword()
        f = open(os.path.join(config['vault'],"m"+str(message.id)), "wb")
        encrypter, salt = Encryption.new_encrypter(message.encryption_key)
        padding, endOfFile = (0, False)
        newFile = StringIO.StringIO(message.body)
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
    except IOError, ioe:
        logging.critical("[%s] [encrypt_message] [There was an IOError while checking in new file: %s]" % (message.owner_id,str(ioe)))
        raise Exception("There was an IO error while uploading: %s. The administrator has been notified of this error." % str(ioe))

if __name__ == "__main__":
    print "Hello";