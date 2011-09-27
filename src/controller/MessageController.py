import cherrypy
import logging
from Cheetah.Template import Template
__author__="wbdavis"
__date__ ="$Sep 25, 2011 9:32:23 PM$"

class MessageController:
    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def send_message(self, subject, body, recipientIds, expiration, format="json", **kwargs):
        fl, user, sMessages, fMessages = cherrypy.thread_data.flDict['app'], cherrypy.session.get("user"), [], []
        try:
            recipientIdList = split_list_sanitized(recipientIds)
            subject= strip_tags(subject)
            if kwargs.has_key("expiration"):
                expiration = kwargs['expiration']
            #Process the expiration data for the file
            maxExpiration = datetime.datetime.today() + datetime.timedelta(days=fl.maxFileLifeDays)
            if (expiration is None or expiration == "" or expiration.lower() == "never"):
                if fl.check_permission(user, "expiration_exempt") or fl.check_admin(user): #Check permission before allowing a non-expiring upload
                    expiration = None
                else:
                    expiration = maxExpiration
            else:
                expiration = datetime.datetime(*time.strptime(strip_tags(expiration), "%m/%d/%Y")[0:5])
                if maxExpiration < expiration and fl.check_permission(user, "expiration_exempt")==False:
                    raise FLError(False, ["Expiration date must be between now and %s." % maxExpiration.strftime("%m/%d/%Y")])
            newMessage = Message(subject, body, datetime.datetime.now(), user.userId, expiration, recipientIdList)
            fl.send_message(user, newMessage)
            sMessages.append("Message \"%s\" sent." % subject)
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        except Exception, e:
            fMessages.append("Invalid expiration date format. Date must be in mm/dd/yyyy format.")
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_new_message_count(self, format="json", **kwargs):
        fl, user, sMessages, fMessages, newMessageCount = cherrypy.thread_data.flDict['app'], cherrypy.session.get("user"), [], [], []
        try:
            newMessageCount = fl.get_new_message_count(user)
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format, data=newMessageCount)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def get_messages(self, format="json", **kwargs):
        fl, user, sMessages, fMessages = cherrypy.thread_data.flDict['app'], cherrypy.session.get("user"), [], []
        messagesList, recvMessagesList, sentMessagesList, messageIdList = [], [], [], None
        try:
            if kwargs.has_key("messageIds"):
                messageIdList = split_list_sanitized(kwargs['messageIds'])
            recvMessages = fl.get_received_messages(user, user.userId, messageIdList)
            sentMessages = fl.get_sent_messages(user, user.userId, messageIdList)
            for message in recvMessages:
                messageDict = message.get_dict()
                messageBody = strip_tags(cgi.escape(messageDict['body']), True)
                messageDict['body'] = str(Template("$messageBody", searchList=[locals()], filter=WebSafe))
                recvMessagesList.append(messageDict)

            for message in sentMessages:
                messageDict = message.get_dict()
                messageBody = strip_tags(cgi.escape(messageDict['body']), True)
                messageDict['body'] = str(Template("$messageBody", searchList=[locals()], filter=WebSafe))
                sentMessagesList.append(messageDict)
            messagesList.append(recvMessagesList)
            messagesList.append(sentMessagesList)
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format, data=messagesList)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def read_message(self, messageId, format="json", **kwargs):
        fl, user, sMessages, fMessages = cherrypy.thread_data.flDict['app'], cherrypy.session.get("user"), [], []
        try:
            fl.read_message(user, messageId)
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)

    @cherrypy.expose
    @cherrypy.tools.requires_login()
    def delete_messages(self, messageIds, format="json", **kwargs):
        fl, user, sMessages, fMessages = cherrypy.thread_data.flDict['app'], cherrypy.session.get("user"), [], []
        try:
            messageIdList = split_list_sanitized(messageIds)
            for messageId in messageIdList:
                fl.delete_message(user, messageId)
            sMessages.append("Message(s) deleted")
        except FLError, fle:
            sMessages.extend(fle.successMessages)
            fMessages.extend(fle.failureMessages)
        return fl_response(sMessages, fMessages, format)
    
if __name__ == "__main__":
    print "Hello";