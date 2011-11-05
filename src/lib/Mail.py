# -*- coding: utf-8 -*-
from smtplib import SMTP
import cherrypy
from Cheetah.Template import Template
import logging
from Models import *

#Recipients must be a list object
        
def get_server(config):
    server = SMTP(config['smtp_server'], config['smtp_port'] )
    if config['smtp_start_tls']:
        server.ehlo(config['smtp_sender'])
        server.starttls()
        server.ehlo(config['smtp_sender'])
    if config['smtp_auth_required']:
        server.login(config['smtp_user'], config['smtp_pass'] )
    return server

def notify(template, varDict={}):
    config = cherrypy.request.app.config['filelocker']
    if varDict.has_key("recipient") and varDict['recipient'] is not None and varDict['recipient'] != "":
        linksObscured = False
        if config.has_key("smtp_obscure_links") and config['smtp_obscure_links']:
            linksObscured = True
            if varDict.has_key("filelockerURL"):
                varDict['filelockerURL'] = make_unclickable(config['root_url'])
        server = get_server(config)
        sender = config['smtp_sender']
        tpl = Template(file=template, searchList=[locals(),globals()])
        smtpresult = server.sendmail(config['smtp_sender'], varDict['recipient'], str(tpl))
        server.close()

def make_unclickable(link):
    return link.replace(".", " . ").replace("http://", "").replace("https://", "")