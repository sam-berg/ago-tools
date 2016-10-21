#### calculate URL to attachment field

#### example:
####  -u <username> -p <password> -urlField URL -layerID 3233sdf2334334ff -portal http://yourorg.maps.arcgis.com

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
            sURL = sURL + "/0"

        return sURL        
    

    def _calculateAttachmentURL(self,layerURL,urlField,oidField,thumbnailField,Query):
        #(args.layerURL,args.urlField,sOIDField,sThumbnailField,args.webDir)

        #get objectIDs
        parameters = urllib.urlencode({'token' : self.user.token})
        query = "/query?where={}&returnIdsOnly=true&f=json".format(Query)
        
        requestString = layerURL + query
        
        try:
            print ("retrieving OBJECTIDs...")
            responseOID = urllib.urlopen(requestString,parameters ).read()

            jresult = json.loads(responseOID)
            oidList=jresult["objectIds"]
            
            #iterate through features
            for oid in oidList:
                aQuery=layerURL + "/"+str(oid) + "/attachments?f=json"

                #determine attachment count
                responseAttachments = urllib.urlopen(aQuery,parameters ).read()
                print "reading attachments for feature " + str(oid)
                
                jAttachresult = json.loads(responseAttachments)
                aCount = len(jAttachresult["attachmentInfos"])
                bHasAttachments=False
                firstAttachmentURL=''
                secondAttachmentURL=''

                if(aCount>=2):
                  #use first two attachments
                    bHasAttachments=True
                    firstAttachmentURL=layerURL + "/"+str(oid) + "/attachments" + "/" + str(jAttachresult['attachmentInfos'][0]['id'])
                    secondAttachmentURL = layerURL + "/"+str(oid) + "/attachments" + "/" + str(jAttachresult['attachmentInfos'][1]['id'])

                if( bHasAttachments):
                    sPost = '[{"attributes":{"' + oidField +'":' + str(oid) + ',"' + urlField + '":"' + firstAttachmentURL + '","' + thumbnailField + '":"' + secondAttachmentURL +  '"}}]'
                    updateFeaturesRequest=layerURL + "/updateFeatures"

                    parametersUpdate = urllib.urlencode({'f':'json','token' : self.user.token,'features':sPost})
       
                    print "writing attachment url for feature " + str(oid)

                    responseUpdate = urllib.urlopen(updateFeaturesRequest,parametersUpdate ).read()

                    a=responseUpdate
                    print str(a)

        except :
            e=sys.exc_info()[0]
            print str(e)

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
parser.add_argument('-layerID', '--layerID')
parser.add_argument('-urlField', '--urlField')
parser.add_argument('-thumbnailField', '--thumbnailField')
parser.add_argument('-query', '--query')
parser.add_argument('-OIDField', '--OIDField')

args = parser.parse_args()

if args.user == None:
    args.user = _raw_input("Username:")

if args.portal == None:
    args.portal = _raw_input("Portal: ")

args.portal = str(args.portal).replace("http://","https://")

agoAdmin = Admin(args.user,args.portal,args.password)

if (args.layerID==None):
    args.layerID = _raw_input("layerID: ")

if (args.urlField==None):
    args.urlField = _raw_input("URL Fieldname: ")

if (args.query==None):
    args.query = _raw_input("Query: ")

sOIDField="OBJECTID"
if (args.OIDField!=None):
    sOIDField = args.OIDField

args.layerURL=agoAdmin.getLayerURL(args.layerID)
print "layerURL: " + str(args.layerURL)

sThumbnailField = "thumb_url"
if (args.thumbnailField!=None):
    sThumbnailField = args.thumbnailField


agoAdmin._calculateAttachmentURL(args.layerURL,args.urlField,sOIDField,sThumbnailField,args.query)

