#### create assignment locations from input layer

import csv
import argparse
import sys
import json
import getpass
import urllib

class User:

    def __init__(self, username, portal=None, password=None):
        if portal == None:
            self.portalUrl = 'https://www.arcgis.com'
        else:
            self.portalUrl = portal
        self.username = username
        if password == None:
            self.password = getpass.getpass()
        else:
            self.password = password
        self.token = self.__getToken__(self.portalUrl, self.username, self.password)

    def __getToken__(self, url, username, password):
        '''Retrieves a token to be used with future requests.'''
        parameters = urllib.urlencode({'username' : username,
                                       'password' : password,
                                       'client' : 'referer',
                                       'referer': url,
                                       'expiration': 60,
                                       'f' : 'json'})
        response = urllib.urlopen(url + '/sharing/rest/generateToken?', parameters).read()
        token = json.loads(response)['token']
        return token

    def __portalId__(self):
        '''Gets the ID for the organization/portal.'''
        parameters = urllib.urlencode({'token' : self.token,
                                       'f' : 'json'})
        response = urllib.urlopen(self.portalUrl + '/sharing/rest/portals/self?' + parameters).read()
        portalId = json.loads(response)['id']
        return portalId

class Admin:
  
    def __init__(self, username, portal=None, password=None):

        self.user = User(username, portal, password)

            
    def getLayerURL(self, layerId):
        sURL=None

        params = urllib.urlencode({'token' : self.user.token,
                            'f' : 'json'})
        #print 'Getting Info for: ' + webmapId
        #Get the item data
        
        reqUrl = self.user.portalUrl + '/sharing/rest/content/items/' + layerId  + "?" + params
        itemDataReq = urllib.urlopen(reqUrl).read()
        itemString = str(itemDataReq)

        pp=json.loads(itemString)

        sURL = pp["url"]
        l=sURL[len(sURL)-1]
        
        if (l.isnumeric()== False):
            #sURL = sURL + "/0"
            sURL = sURL + "/1"#SBTEST

        return sURL        
    

    def _addAssignmentsFromLayer(self,inputLayerURL,targetLayerURL):

        #get objectIDs
        parameters = urllib.urlencode({'token' : self.user.token})
        query = "/query?where={}&outFields=*&f=json".format("0=0")
        
        requestString = inputLayerURL + query
        
        try:
            print ("retrieving OBJECTIDs...")
            response = urllib.urlopen(requestString,parameters ).read()

            jresult = json.loads(response)
   
            #iterate through features
            for f in jresult.features:
              f2=f    
            
        except ee:
            e=ee
     

        return None

def _raw_input(prompt=None, stream=None, input=None):
    # A raw_input() replacement that doesn't save the string in the
    # GNU readline history.
    if not stream:
        stream = sys.stderr
    if not input:
        input = sys.stdin
    prompt = str(prompt)
    if prompt:
        stream.write(prompt)
        stream.flush()
    # NOTE: The Python C API calls flockfile() (and unlock) during readline.
    line = input.readline()
    if not line:
        raise EOFError
    if line[-1] == '\n':
        line = line[:-1]
    return line


parser = argparse.ArgumentParser()
parser.add_argument('-u', '--user')
parser.add_argument('-p', '--password')
parser.add_argument('-portal', '--portal')
parser.add_argument('-inputLayerID', '--inputLayerID')
parser.add_argument('-targetAssignmentLayerID', '--targetAssignmentLayerID')

args = parser.parse_args()

if args.user == None:
    args.user = _raw_input("Username:")

if args.portal == None:
    args.portal = _raw_input("Portal: ")

args.portal = str(args.portal).replace("http://","https://")

agoAdmin = Admin(args.user,args.portal,args.password)

if (args.inputLayerID==None):
    args.inputLayerID = _raw_input("Input Layer ID: ")

if (args.targetAssignmentLayerID==None):
    args.targetAssignmentLayerID = _raw_input("Target Assignment Layer ID: ")

inputLayerURL=agoAdmin.getLayerURL(args.inputLayerID)
print "Input Layer URL: " + str(inputLayerURL)

targetLayerURL=agoAdmin.getLayerURL(args.targetAssignmentLayerID)
print "Target Layer URL: " + str(targetLayerURL)

agoAdmin._addAssignmentsFromLayer(inputLayerURL,targetLayerURL)

