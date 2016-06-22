#### calculate URL to attachment field

args={}
args["portal"]='http://arcgis.com'
args["picURLField"]= 'PIC_URL'
args["thumbURLField"]= 'THUMB_URL'
args["layerID"]=''
args["user"] =''
args["password"] =''

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
    

    def _calculateAttachmentURL(self,layerURL,urlField,urlField2):

        #get objectIDs
        parameters = urllib.urlencode({'token' : self.user.token})
        query = "/query?where={}&returnIdsOnly=true&f=json".format("0=0")
        
        requestString = layerURL + query
        
        try:
            print ("retrieving OBJECTIDs...")
            responseOID = urllib.urlopen(requestString,parameters ).read()

            jresult = json.loads(responseOID)
            oidList=jresult["objectIds"]
            
            #iterate through features
            for oid in oidList:
                aQuery=layerURL + "/" + str(oid) + "/attachments?f=json"

                #determine attachment count
                responseAttachments = urllib.urlopen(aQuery,parameters ).read()
                print "reading attachments for feature " + str(oid)
                
                jAttachresult = json.loads(responseAttachments)
                aCount = len(jAttachresult["attachmentInfos"])
                bHasAttachments=False
                firstAttachmentURL=''

                if(aCount>0):
                    bHasAttachments=True
                    firstAttachmentURL=layerURL + "/" + str(oid) + "/attachments" + "/" + str(jAttachresult['attachmentInfos'][0]['id'])

                #write attachment count

                if( bHasAttachments):
                    #sPost = '[{"attributes":{"OBJECTID":' + str(oid) + ',"' + urlField + '":"' + firstAttachmentURL + '"}}]'
                    sPost = '[{"attributes":{"OBJECTID":' + str(oid) + ',"' + urlField + '":"' + firstAttachmentURL + '","' + urlField2 + '":"' + firstAttachmentURL + '"}}]'
                
                    updateFeaturesRequest=layerURL + "/updateFeatures"

                    parametersUpdate = urllib.urlencode({'f':'json','token' : self.user.token,'features':sPost})
       
                    print "writing attachment url for feature " + str(oid)

                    responseUpdate = urllib.urlopen(updateFeaturesRequest,parametersUpdate ).read()
                    a=responseUpdate

        except ValueError, e:
            e2=e;
     

        return None






args["portal"] = str(args["portal"]).replace("http://","https://")

agoAdmin = Admin(args["user"],args["portal"],args["password"])

args["layerURL"]=agoAdmin.getLayerURL(args["layerID"])

agoAdmin._calculateAttachmentURL(args["layerURL"],args["picURLField"],args["thumbURLField"])

