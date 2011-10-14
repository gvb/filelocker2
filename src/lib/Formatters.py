import os
import re
import json
import cherrypy
JSON_WRITE = None

try: #This bit here is to handle backwards compatibility with python-json modules. The .write and .dumps methods work analagously as far as I can tell
    json.write("test")
    JSON_WRITE = json.write
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

def fl_response(sMessages, fMessages, format, data=None):
    if format=="json":
        global JSON_WRITE
        jsonDict = {'sMessages': sMessages, 'fMessages': fMessages}
        if data is not None: jsonDict['data'] = data
        return str(JSON_WRITE(jsonDict))
    elif format=="autocomplete":
        pass
    elif format=="cli":
        fl = cherrypy.thread_data.flDict['app']
        tpl = str(Template(file=get_template_file('cli_response.tmpl'), searchList=[locals(),globals()]))
        return str(tpl)
    else:
        return "Successes: %s, Failures: %s" % (str(sMessages), str(fMessages))

def strip_tags(value, message=False):
    """Return the given HTML with all tags stripped."""
    if message:
        p = re.compile(r'<.*?>')
        return p.sub('',value)
    else:
        return re.sub(r'[^a-zA-Z0-9\.@_+:;=,\s\'/\\\[\]-]', '', value)

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