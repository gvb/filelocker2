# -*- coding: utf-8 -*-
from smtplib import SMTP
import cherrypy
from Cheetah.Template import Template
from lib.SQLAlchemyTool import session
from Models import *
from lib.Formatters import get_config_dict_from_objects

#Recipients must be a list object
def get_mail_config():
    config = {}
    mailConfigObjects = session.query(ConfigParameter).filter(ConfigParameter.name.like('smtp_%')).all()
    return get_config_dict_from_objects(mailConfigObjects)

def get_server(config):
    cherrypy.log.error("============SMPT CONFIG===========\n%s" % str(config))
    if config['smtp_server'] is None or config['smtp_server'] == "":
        raise Exception("Failed to send email notification - this server has not been configured for email.")
    server = SMTP(config['smtp_server'], config['smtp_port'] if config['smtp_port'] != "" else 25 )
    if config['smtp_start_tls']:
        server.ehlo()
        server.starttls()
        server.ehlo()
    if config['smtp_auth_required']:
        server.login(config['smtp_user'], config['smtp_pass'] )
    return server

def notify(template, varDict={}):
    config = cherrypy.request.app.config['filelocker']
    mailConfig = get_mail_config()
    if varDict.has_key("recipient") and varDict['recipient'] is not None and varDict['recipient'] != "":
        linksObscured = False
        if mailConfig.has_key("smtp_obscure_links") and mailConfig['smtp_obscure_links']:
            linksObscured = True
            if varDict.has_key("filelockerURL"):
                varDict['filelockerURL'] = make_unclickable(config['root_url'])
        server = get_server(mailConfig)
        sender = mailConfig['smtp_sender']
        tpl = Template(file=template, searchList=[locals(),globals()])
        try:
            smtpresult = server.sendmail(mailConfig['smtp_sender'], varDict['recipient'], str(tpl))
            server.close()
        except Exception, e:
            server.close()
            cherrypy.log.error("[admin] [notify] [Unable to send email to %s: %s]" % (varDict['recipient'],str(e)))
            raise Exception("Mail server failed to send email to %s. Administrator has been notified." % varDict['recipient'])
        

def make_unclickable(link):
    return link.replace(".", " . ").replace("http://", "").replace("https://", "")