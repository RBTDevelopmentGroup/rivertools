import os, xml, datetime, re
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from pprint import pformat

class _LoggerSingleton:
    instance = None

    class __Logger:

        def __init__(self):
            self.initialized = False
            self.verbose = False

        def setup(self, logRoot, xmlFilePath, config, verbose=False):
            self.initialized = True
            self.verbose = verbose
            self.logDir = os.path.join(logRoot, "logs")

            if not os.path.exists(self.logDir):
                os.makedirs(self.logDir)

            # We also write to a regular TXT log using python's standard library
            txtlogfile = os.path.splitext(xmlFilePath)[0] + '.txt'
            txtlogpath = os.path.join(self.logDir, txtlogfile)

            loglevel = logging.INFO if not verbose else logging.DEBUG

            self.logger = logging.getLogger()

            for hdlr in self.logger.handlers[:]:  # remove all old handlers
                self.logger.removeHandler(hdlr)

            logging.basicConfig(level=loglevel,
                                filemode='w',
                                format='%(asctime)s %(levelname)-8s [%(curmethod)-15s] %(message)s',
                                datefmt='%Y-%m-%d %H:%M:%S',
                                filename=txtlogpath)



            self.logFilePath = os.path.join(self.logDir, xmlFilePath)
            if not os.path.exists(self.logDir):
                os.makedirs(self.logDir)
            self.logTree = ET.ElementTree(ET.Element("sandbar"))

            # File exists. Delete it.
            if os.path.isfile(self.logFilePath):
                os.remove(self.logFilePath)
            if 'MetaData' in config:
                obj2XML("MetaData", config, self.logTree.getroot())
            self.write()

        def logprint(self, message, method="", severity="info", exception=None):
            """
            Logprint logs things 3 different ways: 1) stdout 2) log txt file 3) xml
            :param message:
            :param method:
            :param severity:
            :param exception:
            :return:
            """

            # Verbose logs don't get written until we ask for them
            if severity == 'debug' and not self.verbose:
                return

            dateStr = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S%z')

            if exception is not None:
                txtmsg = '{0}  Exception: {1}'.format(message, str(exception))
                msg = '[{0}] [{1}] {2} : {3}'.format(severity, method, message, str(exception))
            else:
                txtmsg = message
                msg = '[{0}] [{1}] {2}'.format(severity, method, message)

            # Print to stdout
            print msg

            # If we haven't set up a logger then we're done here. Don't write to any files
            if not self.initialized:
                return

            # Write to log file
            if severity == 'info':
                self.logger.info(txtmsg, extra={'curmethod': method})
            elif severity == 'warning':
                self.logger.warning(txtmsg, extra={'curmethod': method})
            elif severity == 'error':
                self.logger.error(txtmsg, extra={'curmethod': method})
            elif severity == 'critical':
                self.logger.critical(txtmsg, extra={'curmethod': method})
            if severity == 'debug':
                self.logger.debug(txtmsg, extra={'curmethod': method})


            # Now print to XML
            logNode = self.logTree.find("log")
            if logNode is None:
                logNode = ET.SubElement(self.logTree.getroot(), "log")

            messageNode = ET.SubElement(logNode, "message", severity=severity, time=dateStr, method=method)
            ET.SubElement(messageNode, "description").text = message
            if exception is not None:
                ET.SubElement(messageNode, "exception").text = str(exception)
            self.write()

        def write(self):
            """
            Return a pretty-printed XML string for the Element.
            """
            rough_string = ET.tostring(self.logTree.getroot(), 'utf-8')
            reparsed = minidom.parseString(rough_string)
            pretty = reparsed.toprettyxml(indent="\t")
            f = open(self.logFilePath, "wb")
            f.write(pretty)
            f.close()

    def __init__(self, **kwargs):
        if not _LoggerSingleton.instance:
            _LoggerSingleton.instance = _LoggerSingleton.__Logger(**kwargs)
    def __getattr__(self, name):
        return getattr(self.instance, name)


class Logger():
    """
    Think of this class like a light interface
    """

    def __init__(self, method=""):
        self.instance = _LoggerSingleton()
        self.method = method

    def setup(self, **kwargs):
        self.instance.setup(**kwargs)

    def print_(self, message, **kwargs):
        self.instance.logprint(message, **kwargs)

    def debug(self, *args):
        """
        This works a little differently. You can basically throw anything you want into it.
        :param message:
        :return:
        """
        msgarr =  []
        for arg in args:
            msgarr.append(pformat(arg))
        finalmessage = '\n'.join(msgarr).replace('\n', '\n              ')
        self.instance.logprint(finalmessage, self.method, "debug")

    def destroy(self):
        self.instance = None
        self.method = None

    def info(self, message):
        self.instance.logprint(message, self.method, "info")

    def error(self, message, exception=None):
        self.instance.logprint(message, self.method, "error", exception)

    def warning(self, message, exception=None):
        self.instance.logprint(message, self.method, "warning", exception)


"""
Static XML Helper Methods
"""

def SaniTag(string):
    return re.sub('[\W]+', '_', string).lower()


def getXML_XML(keyname, node, rootNode):
    elements = node.findall("*")
    for el in elements:
        rootNode.append(el)


def getXML_dict(keyname, indict, rootNode):
    node = ET.SubElement(rootNode, SaniTag(keyname))
    for k, v in indict.items():
        obj2XML(k, v, node)


def getXML_list(keyname, inlist, rootNode):
    node = ET.SubElement(rootNode, SaniTag(keyname))
    for i in inlist:
        obj2XML("value", i, node)


def obj2XML(keyname, obj, resultsNode):
    adapt = {
        dict: getXML_dict,
        list: getXML_list,
        tuple: getXML_list,
        xml.etree.ElementTree.Element: getXML_XML
    }
    if adapt.has_key(obj.__class__):
        adapt[obj.__class__](keyname, obj, resultsNode)
    else:
        node = ET.SubElement(resultsNode, SaniTag(keyname)).text = str(obj)