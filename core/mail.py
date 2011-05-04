# -*- coding: utf-8 -*-
from smtplib import SMTP
from Cheetah.Template import Template
import logging
from dao.models.UploadTicket import UploadTicket

#Recipients must be a list object
class Mail:
    def __init__(self, mailConfig):
        self.config = mailConfig
        
    def get_server(self):
        server = SMTP(self.config['smtpServer'], self.config['smtpPort'] )
        if self.config['smtpStartTLS']:
            server.ehlo(self.config['smtpSender'])
            server.starttls()
            server.ehlo(self.config['smtpSender'])
        if self.config['smtpAuthRequired']:
            server.login(self.config['smtpUser'], self.config['smtpPass'] )
        return server
    
    def notify(self, template, varDict={}):
        if varDict.has_key("recipient") and varDict['recipient'] is not None and varDict['recipient'] != "":
            linksObscured = False
            if self.config.has_key("smtpObscureLinks") and self.config['smtpObscureLinks']:
                linksObscured = True
                if varDict.has_key("filelockerURL"):
                    varDict['filelockerURL'] = self.make_unclickable(varDict['filelockerURL'])
            server = self.get_server()
            sender = self.config['smtpSender']
            tpl = Template(file=template, searchList=[locals(),globals()])
            smtpresult = server.sendmail(self.config['smtpSender'], varDict['recipient'], str(tpl))
            server.close()
        
    def make_unclickable(self, link):
        return link.replace(".", " . ").replace("http://", "").replace("https://", "")