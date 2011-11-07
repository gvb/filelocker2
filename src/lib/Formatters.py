import os
import re
import types
import datetime
import time
import json
import cherrypy
from lib.Models import *
JSON_WRITE = None

try: #This bit here is to handle backwards compatibility with python-json modules. The .write and .dumps methods work analagously as far as I can tell
    json.write("test")
    JSON_WRITE = json_parse
except AttributeError, ae:
    JSON_WRITE = json.dumps
__author__="wbdavis"
__date__ ="$Sep 25, 2011 10:44:58 PM$"

def get_template_file(fileName):
        filePath = None
        vault = cherrypy.request.app.config['filelocker']['vault']
        templatePath = os.path.join(cherrypy.request.app.config['filelocker']['root_path'], "view")
        if fileName.endswith(".css"):
            if os.path.exists(os.path.join(vault,"custom", "css",fileName)):
                filePath = os.path.join(vault,"custom", "css",fileName)
            else:
                filePath = os.path.join(templatePath, "css", fileName)
        elif os.path.exists(os.path.join(vault,"custom",fileName)):
            filePath = os.path.join(vault,"custom",fileName)
        else:
            filePath = os.path.join(templatePath, fileName)
        return filePath

class FL_Object_Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, User):
            return obj.get_dict()
        elif isinstance(obj, Group):
            return obj.get_dict()
        elif isinstance(obj, File):
            return obj.get_dict()
        return json.JSONEncoder.default(self, obj)

def fl_response(sMessages, fMessages, format, data=None):
    if format=="json":
        global JSON_WRITE
        jsonDict = {'sMessages': sMessages, 'fMessages': fMessages}
        if data is not None: jsonDict['data'] = data
        return str(JSON_WRITE(jsonDict, cls=FL_Object_Encoder))
    elif format=="autocomplete":
        pass
    elif format=="cli":
        tpl = str(Template(file=get_template_file('cli_response.tmpl'), searchList=[locals(),globals()]))
        return str(tpl)
    else:
        return "Successes: %s, Failures: %s" % (str(sMessages), str(fMessages))

def strip_tags(value, message=False):
    """Return the given HTML with all tags stripped."""
    if value is None:
        return None
    if message:
        p = re.compile(r'<.*?>')
        return p.sub('',value)
    else:
        cleanText = re.sub(r'[^a-zA-Z0-9\.@_+:;=,\s\'/\\\[\]-]', '', value)
        return cleanText if cleanText != "" else None

def tail( f, window=20 ):
    try:
        f.seek( 0, 2 )
        bytes= f.tell()
        size= window
        block= -1
        while size > 0 and bytes+block*1024  > 0:
            # If your OS is rude about small files, you need this check
            # If your OS does 'the right thing' then just f.seek( block*1024, 2 )
            # is sufficient
            if (bytes+block*1024 > 0):
                ##Seek back once more, if possible
                f.seek( block*1024, 2 )
            else:
                #Seek to the beginning
                f.seek(0, 0)
            data= f.read( 1024 )
            linesFound= data.count('\n')
            size -= linesFound
            block -= 1
        f.seek( block*1024, 2 )
        f.readline() # find a newline
        lastBlocks= list( f.readlines() )[-window:]
        return lastBlocks
    except IOError, ioe:
        try:
            f.seek(0)
            return list(f.readlines())
        except Exception, e:
            return ["Unable to read log file: %s" % str(e)]
    except Exception, e:
        return ["Unable to read log file: %s" % str(e)]

def split_list_sanitized(cs_list):
    cleanList = []
    if cs_list is not None:
        for listItem in cs_list.split(','):
            if listItem is not None and listItem !="":
                cleanList.append(strip_tags(listItem))
    return cleanList

def parse_date(stringDate, minDate=None, maxDate=None):
    if stringDate is None or stringDate == "" or stringDate.lower()=="never":
        return None
    try:
        parsedDate = datetime.datetime(*time.strptime(strip_tags(stringDate), "%m/%d/%Y")[0:5])
        if maxDate is not None and parsedDate > maxDate:
                raise Exception("Date cannot be after %s" % maxDate.strftime("%m/%d/%Y"))
        if minDate is not None and parsedDate < minDate:
            raise Exception("Date date cannot be before %s" % minDate.strftime("%m/%d/%Y"))
        return parsedDate
    except Exception, e:
        raise Exception("Invalid expiration date format. Date must be in mm/dd/yyyy format.: %s" % str(e))

def json_parse(obj):
    ty = type(obj)
    if ty is types.ListType or ty is types.TupleType:
        results = []
        for val in obj:
            if isinstance(val, User) or isinstance(val, Group) or isinstance(val, File):
                results.append(val.get_dict())
            else:
                results.append(val)
        json.write(results)
    else:
        json.write(obj)