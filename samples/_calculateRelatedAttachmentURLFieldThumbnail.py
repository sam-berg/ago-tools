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
    

    def _calculateRelatedAttachmentURL(self,layerURL,htmlField,oidField):
        #(args.layerURL,args.urlField,sOIDField,sThumbnailField,args.webDir)

        relLayerURL='http://services1.arcgis.com/9lDFdeC4JIBgML6L/arcgis/rest/services/NNIS_Monitor5/FeatureServer/1'

        #get objectIDs
        parameters = urllib.urlencode({'token' : self.user.token})
        query = "/query?where={}&returnIdsOnly=false&outFields=*&f=json".format("0=0")
        
        requestString = layerURL + query
        
        try:
            print ("retrieving OBJECTIDs...")
            responseOID = urllib.urlopen(requestString,parameters ).read()

            jresult = json.loads(responseOID)
            oidList=jresult["features"]
            
            #iterate through features
            for f in oidList:
                
                #get related records
                #query
                relQuery= "/query?where={}&returnIdsOnly=true&f=json".format(str("RelLink") + "= '" + str(f["attributes"]["GlobalID"]) + "'")
                relQuery=relLayerURL + relQuery
                responseRelated = urllib.urlopen(relQuery,parameters ).read()
                jRelResult = json.loads(responseRelated)
                relCount = len(jRelResult["objectIds"])

                for oid2 in jRelResult["objectIds"]:

                  aQuery=relLayerURL + "/"+str(oid2) + "/attachments?f=json"

                  #determine attachment count
                  responseAttachments = urllib.urlopen(aQuery,parameters ).read()
                  print "reading attachments for feature " + str(oid2)
                
                  jAttachresult = json.loads(responseAttachments)
                  aCount = len(jAttachresult["attachmentInfos"])
                  bHasAttachments=False
                  firstAttachmentURL=''

                  if(aCount>0):
                      bHasAttachments=True
                      firstAttachmentURL=relLayerURL + "/"+str(oid2) + "/attachments" + "/" + str(jAttachresult['attachmentInfos'][0]['id'])
                      #thumbnailPath = webDir + str(jAttachresult['attachmentInfos'][0]['name'])

                  if( bHasAttachments):
                      sPost = '[{"attributes":{"' + oidField +'":' + str(f["attributes"][oidField]) + ',"' + htmlField + '":"' + firstAttachmentURL + '"}}]'
                      updateFeaturesRequest=layerURL + "/updateFeatures"

                      parametersUpdate = urllib.urlencode({'f':'json','token' : self.user.token,'features':sPost})
       
                      print "writing attachment url for feature " + str(f["attributes"][oidField])

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
parser.add_argument('-htmlField', '--htmlField')
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

if (args.htmlField==None):
    args.htmlField = _raw_input("HTML Fieldname: ")

sOIDField="OBJECTID"
if (args.OIDField!=None):
    sOIDField = args.OIDField

args.layerURL=agoAdmin.getLayerURL(args.layerID)
print "layerURL: " + str(args.layerURL)


agoAdmin._calculateRelatedAttachmentURL(args.layerURL,args.htmlField,sOIDField)

