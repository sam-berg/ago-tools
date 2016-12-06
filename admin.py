﻿#!/usr/bin/env python

import urllib
import json
import csv
import time
import random

from datetime import date, timedelta
from collections import namedtuple

class Admin:
    '''A class of tools for administering AGO Orgs or Portals'''
    def __init__(self, username, portal=None, password=None):
        from . import User
        self.user = User(username, portal, password)

    def __users__(self, start=0):
        '''Retrieve a single page of users.'''
        parameters = urllib.urlencode({'token' : self.user.token,
                                       'f' : 'json',
                                       'start' : start,
                                       'num' : 100})
        portalId = self.user.__portalId__()
        response = urllib.urlopen(self.user.portalUrl + '/sharing/rest/portals/' + portalId + '/users?' + parameters).read()
        users = json.loads(response)
        return users

    def getUsers(self, roles=None, daysToCheck=10000):
        '''
        Returns a list of all users in the organization (requires admin access).
        Optionally provide a list of roles to filter the results (e.g. ['org_publisher']).
        Optionally provide a number to include only accounts created in the last x number of days.
        '''
        if not roles:
            roles = ['org_admin', 'org_publisher', 'org_user']
            #roles = ['org_admin', 'org_publisher', 'org_author', 'org_viewer'] # new roles to support Dec 2013 update
        allUsers = []
        users = self.__users__()
        for user in users['users']:
            if user['role'] in roles and date.fromtimestamp(float(user['created'])/1000) > date.today()-timedelta(days=daysToCheck):
                allUsers.append(user)
        while users['nextStart'] > 0:
            users = self.__users__(users['nextStart'])
            for user in users['users']:
                if user['role'] in roles and date.fromtimestamp(float(user['created'])/1000) > date.today()-timedelta(days=daysToCheck):
                    allUsers.append(user)
        return allUsers

    def addUsersToGroups(self, users, groups):
        '''
        REQUIRES ADMIN ACCESS
        Add organization users to multiple groups and return a list of the status
        '''
        # Provide one or more usernames in a list.
        # e.g. ['user_1', 'user_2']
        # Provide one or more group IDs in a list.
        # e.g. ['d93aabd856f8459a8905a5bd434d4d4a', 'f84c841a3dfc4591b1ff83281ea5025f']

        toolSummary = []

        # Assign users to the specified group(s).
        parameters = urllib.urlencode({'token': self.user.token, 'f': 'json'})
        for group in groups:
            # Add Users - REQUIRES POST method (undocumented operation as of 2013-11-12).
            response = urllib.urlopen(self.user.portalUrl + '/sharing/rest/community/groups/' + group + '/addUsers?', 'users=' + ','.join(users) + "&" + parameters).read()
            # Users not added will be reported back with each group.
            toolSummary.append({group: json.loads(response)})

        return toolSummary

    def reassignAllUser1ItemsToUser2(self, userFrom, userTo):
        '''
        REQUIRES ADMIN ACCESS
        Transfers ownership of all items in userFrom/User1's account to userTo/User2's account, keeping same folder names.
        - Does not check for existing folders in userTo's account.
        - Does not delete content from userFrom's account.
        '''

        # request user content for userFrom
        # response contains list of items in root folder and list of all folders
        parameters = urllib.urlencode({'token': self.user.token, 'f': 'json'})
        request = self.user.portalUrl + '/sharing/rest/content/users/' + userFrom + '?' + parameters
        userContent = json.loads(urllib.urlopen(request).read())

        # create same folders in userTo's account like those in userFrom's account
        for folder in userContent['folders']:
            parameters2 = urllib.urlencode({'title' : folder['title'], 'token': self.user.token, 'f': 'json'})
            request2 = self.user.portalUrl + '/sharing/rest/content/users/' + userTo + '/createFolder?'
            response2 = urllib.urlopen(request2, parameters2).read()   # requires POST

        # keep track of items and folders
        numberOfItems = 0
        numberOfFolders = 1

        # change ownership of items in ROOT folder
        for item in userContent['items']:
            parameters3 = urllib.urlencode({'targetUsername' : userTo, 'targetFoldername' : '/', 'token': self.user.token, 'f': 'json'})
            request3 = self.user.portalUrl + '/sharing/rest/content/users/' + userFrom + '/items/' + item['id'] + '/reassign?'
            response3 = urllib.urlopen(request3, parameters3).read()   # requires POST
            if 'success' in response3:
                numberOfItems += 1

        ### change ownership of items in SUBFOLDERS (nested loop)
        # request content in current folder
        for folder in userContent['folders']:
            parameters4 = urllib.urlencode({'token': self.user.token, 'f': 'json'})
            request4 = self.user.portalUrl + '/sharing/rest/content/users/' + userFrom + '/' + folder['id'] + '?' + parameters4
            folderContent = json.loads(urllib.urlopen(request4).read())
            numberOfFolders += 1

            # change ownership of items in CURRENT folder to userTo and put in correct folder
            for item in folderContent['items']:
                parameters5 = urllib.urlencode({'targetUsername' : userTo, 'targetFoldername' : folder['title'], 'token': self.user.token, 'f': 'pjson'})
                request5 = self.user.portalUrl + '/sharing/rest/content/users/' + userFrom + '/' + folder['id'] + '/items/' + item['id'] + '/reassign?'
                response5 = urllib.urlopen(request5, parameters5).read()   # requires POST
                numberOfItems += 1

        # summarize results
        print '    ' + str(numberOfItems) + ' ITEMS in ' + str(numberOfFolders) + ' FOLDERS (incl. Home folder) copied'
        print '        from USER ' + userFrom + ' to USER ' + userTo

        return

    def reassignAllGroupOwnership(self, userFrom, userTo):
        '''
        REQUIRES ADMIN ACCESS
        Reassigns ownership of all groups between a pair of accounts.
        '''
        groups = 0
        groupsReassigned = 0

        # Get list of userFrom's groups
        print 'Requesting ' + userFrom + "'s group info from ArcGIS Online...",
        parameters = urllib.urlencode({'token': self.user.token, 'f': 'pjson'})
        request = self.user.portalUrl + '/sharing/rest/community/users/' + userFrom + '?' + parameters
        response = urllib.urlopen(request).read()
        userFromContent = json.loads(response)
        print 'RECEIVED!'

        # Determine if userFrom is group owner and, if so, transfer ownership to userTo
        print 'Checking groups...',
        for group in userFromContent['groups']:
            print '.',
            groups += 1
            if group['owner'] == userFrom:
                parameters = urllib.urlencode({'targetUsername' : userTo, 'token': self.user.token, 'f': 'pjson'})
                request = self.user.portalUrl + '/sharing/rest/community/groups/' + group['id'] + '/reassign?'
                response = urllib.urlopen(request, parameters).read()   # requires POST
                if 'success' in response:
                    groupsReassigned += 1

        # Report results
        print
        print '    CHECKED ' + str(groups) + ' groups ASSOCIATED with ' + userFrom + '.'
        print '       REASSIGNED ' + str(groupsReassigned) + ' groups OWNED by ' + userFrom + ' to ' + userTo + '.'

        return

    def addUser2ToAllUser1Groups(self, userFrom, userTo):
        '''
        REQUIRES ADMIN ACCESS
        Adds userTo/User2 to all groups that userFrom/User1 is a member
        '''

        groups = 0
        groupsOwned = 0
        groupsAdded = 0

        # Get list of userFrom's groups
        parameters = urllib.urlencode({'token': self.user.token, 'f': 'pjson'})
        request = self.user.portalUrl + '/sharing/rest/community/users/' + userFrom + '?' + parameters
        response = urllib.urlopen(request).read()
        userFromContent = json.loads(response)

        # Add userTo to each group that userFrom's is a member, but not an owner
        for group in userFromContent['groups']:
            groups += 1
            if group['owner'] == userFrom:
                groupsOwned += 1
            else:
                parameters = urllib.urlencode({'users' : userTo, 'token': self.user.token, 'f': 'pjson'})
                request = self.user.portalUrl + '/sharing/rest/community/groups/' + group['id'] + '/addUsers?'
                response = urllib.urlopen(request, parameters).read()   # requires POST
                if '[]' in response:   # This currently undocumented operation does not correctly return "success"
                    groupsAdded += 1

        print '    CHECKED ' + str(groups) + ' groups associated with ' + userFrom + ':'
        print '        ' + userFrom +  ' OWNS ' + str(groupsOwned) + ' groups (' + userTo + ' NOT added).'
        print '        ' + userTo + ' is already a MEMBER of ' + str(groups-groupsOwned-groupsAdded) + ' groups.'
        print '        ' + userTo + ' was ADDED to ' + str(groupsAdded) + ' groups.'

        return

    def migrateAccount(self, userFrom, userTo):
        '''
        REQUIRES ADMIN ACCESS
        Reassigns ownership of all content items and groups from userFrom to userTo.
        Also adds userTo to all groups which userFrom is a member.
        '''

        print 'Copying all items from ' + userFrom + ' to ' + userTo + '...'
        self.reassignAllUser1ItemsToUser2(self, userFrom, userTo)
        print

        print 'Reassigning groups owned by ' + userFrom + ' to ' + userTo + '...'
        self.reassignAllGroupOwnership(self, userFrom, userTo)
        print

        print 'Adding ' + userTo + ' as a member of ' + userFrom + "'s groups..."
        self.addUser2ToAllUser1Groups(self, userFrom, userTo)
        return

    def migrateAccounts(self, pathUserMappingCSV):
        '''
        REQUIRES ADMIN ACCESS
        Reassigns ownership of all content items and groups between pairs of accounts specified in a CSV file.
        Also adds userTo to all groups which userFrom is a member.
        This function batches migrateAccount using a CSV to feed in the accounts to migrate from/to,
        the CSV should have two columns (no column headers/labels): col1=userFrom, col2=userTo)
        '''

        with open(pathUserMappingCSV, 'rb') as userMappingCSV:
            userMapping = csv.reader(userMappingCSV)
            for user in userMapping:
                userFrom = user[0]
                userTo = user[1]

                print '=========='
                print 'Copying all items from ' + userFrom + ' to ' + userTo + '...'
                self.reassignAllUser1ItemsToUser2(self, userFrom, userTo)
                print

                print 'Reassigning groups owned by ' + userFrom + ' to ' + userTo + '...'
                self.reassignAllGroupOwnership(self, userFrom, userTo)
                print

                print 'Adding ' + userTo + ' as a member of ' + userFrom + "'s groups..."
                self.addUser2ToAllUser1Groups(self, userFrom, userTo)
                print '=========='
        return

    def updateServiceItemsThumbnail(self, folder=None):
        '''
        Fetches catalog of items in portal. If there is no thumbnail, assigns the default.
        '''
        if(folder!=None):
            catalog = self.AGOLUserCatalog(folder,False)
        else:
            catalog=self.AGOLCatalog(None)

        for r in catalog:
            if(r.thumbnail==None):
                parameters = urllib.urlencode({'thumbnailURL' : 'http://static.arcgis.com/images/desktopapp.png', 'token' : self.user.token, 'f' : 'json'})

                requestToUpdate = self.user.portalUrl + '/sharing/rest/content/users/' + self.user.username  + '/items/' +r.id + '/update'

                try:
                    print ("updating " + r.title + " with thumbnail.")
                    response = urllib.urlopen(requestToUpdate, parameters ).read()

                    jresult = json.loads(response)
                except:
                    e=1

        return None

    #calculateAttachmentCount(args.layerURL,args.flagField)
    def calculateAttachmentCount(self,layerURL, flagField):

        #get objectIDs
        #http://services.arcgis.com/XWaQZrOGjgrsZ6Cu/arcgis/rest/services/CambridgeAssetInspections/FeatureServer/0/query?where=0%3D0&returnIdsOnly=true&f=json
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
                aQuery=layerURL + "/"+str(oid) + "/attachments?f=json"

                #determine attachment count
                responseAttachments = urllib.urlopen(aQuery,parameters ).read()
                print "reading attachments for feature " + str(oid)
                
                jAttachresult = json.loads(responseAttachments)
                aCount = len(jAttachresult["attachmentInfos"])
                bHasAttachments=False
                if(aCount>0):
                    bHasAttachments=True

                #write attachment count
                #sPost = '[{"attributes":{"OBJECTID":' + str(oid) + ',"NUMATTACHMENTS":' + str(aCount) +"}}]"
                #sPost = '[{"attributes":{"OBJECTID":' + str(oid) + ',"' + flagField + '":' + str(aCount) +"}}]"
                sPost = '[{"attributes":{"OBJECTID":' + str(oid) + ',"' + flagField + '":"' + str(bHasAttachments) +'"}}]'
                updateFeaturesRequest=layerURL + "/updateFeatures"

                parametersUpdate = urllib.urlencode({'f':'json','token' : self.user.token,'features':sPost})
       
                print "writing " + str(aCount) + " attachment count for feature " + str(oid)

                responseUpdate = urllib.urlopen(updateFeaturesRequest,parametersUpdate ).read()
                a=responseUpdate

        except:
            e=1

        

            

            

        return None

    def shareItems (self, items,groupid):
        '''
        http://www.arcgis.com/sharing/rest/content/users/jsmith/shareItems
        everyone: false
        items=93b54c8930ae46d9a00a7820cb3ebbd1,bb8e3d443ab44878ab8315b00b0612ca
        groups=4774c1c2b79046f285b2e86e5a20319e,cc5f73ab367544d6b954d82cc9c6dab7

        http://www.arcgis.com/sharing/rest/content/items/af01df44bf36437fa8daed01407138ab/share

        '''

        #requestToShare= self.user.portalUrl + '/sharing/rest/content/users/' + self.user.username + '/shareItems'
        #requestToShare= self.user.portalUrl + '/sharing/rest/content/items/shareItems'

        '''
        parameters = urllib.urlencode({'token' : self.user.token,
                                       'items' : sWebMapIDs,
                                       'everyone' : False,
                                       'groups' : groupid,
                                        'f' : 'json'})

        response = urllib.urlopen(requestToShare, parameters ).read()

        jresult = json.loads(response)
        '''

        sWebMapIDs=''
        i=0
        for v in items:
            i = i +1
            sWebMapIDs = sWebMapIDs + v.id
            if (i < len(items)): 
                sWebMapIDs = sWebMapIDs + ","
         
            v.sharedgroups=self._getSharing(v)

            #todo...
            groups=v.sharedgroups
            groupids=''
            for group in groups:
                groupids += str(group) +"," 
            groupids += groupid

            requestToShare= self.user.portalUrl + '/sharing/rest/content/items/' + v.id + '/share' 
            parameters = urllib.urlencode({'token' : self.user.token,
                                           'everyone':True,
                                           'groups' : groupids,
                                            'f' : 'json'})

            response = urllib.urlopen(requestToShare, parameters ).read()

            jresult = json.loads(response)

            l = len(jresult['notSharedWith'])
            bSuccess=True
            if(l==0):
                bSuccess=True
            else:
                bSuccess=False

            if(bSuccess):
                print str(i)  + ') ' + v.title + " (" + jresult["itemId"] + ") was shared."
            else:
                print str(i)  + ') ' + v.title + " (" + jresult["itemId"] + ") could not be shared, or was already shared with this group." 
   
        return
        
    def deleteItems (self, items):

        sWebMapIDs=''
        i=0
        for v in items:
            i = i +1
            sWebMapIDs = sWebMapIDs + v.id
            if (i < len(items)): 
                sWebMapIDs = sWebMapIDs + ","

            #requestToDelete = self.user.portalUrl + '/sharing/rest/content/users/' + v.owner + '/items/' +  v.id + '/delete'

            #have to get ownerFolder
            parameters = urllib.urlencode({'token' : self.user.token, 'f': 'json'})
            requestForInfo = self.user.portalUrl + '/sharing/rest/content/items/' + v.id
 
            response = urllib.urlopen(requestForInfo, parameters ).read()

            jResult = json.loads(response)

            if('error' in jResult):
                print str(i)  + ') ' + v.title + " (" + v.id + ") was not found and will be skipped." 
            else:

                folderID=str(jResult['ownerFolder'])

                requestToDelete = self.user.portalUrl + '/sharing/rest/content/users/' + v.owner + '/' + folderID + '/items/' + v.id + '/delete'
            


                #parameters = urllib.urlencode({'token' : self.user.token, 'f': 'json'})
                parameters = urllib.urlencode({'token' : self.user.token, 'f': 'json','items':v.id})
 
 
                response = urllib.urlopen(requestToDelete, parameters ).read()

                jResult = json.loads(response)

                bSuccess=False
                try:
                    if('success' in jResult):
                        bSuccess=True
                except:
                    bSuccess=False

                if(bSuccess):
                    print str(i)  + ') ' + v.title + " (" + v.id + ") was deleted."
                else:
                    print str(i)  + ') ' + v.title + " (" + v.id + ") could not be deleted, or was already unaccessible." 
    
       
    def registerItems (self, mapservices, folder=''):
        '''
        Given a set of AGOL items, register them to the portal,
        optionally to a specific folder.
        '''
        self.servicesToRegister=mapservices
        allresults=[]
        if folder==None:
            folder=''

        icount=0
        i=0
        for ms in self.servicesToRegister.service_list:
            i = i +1

            sURL=ms.url
            sTitle=ms.title
            if ms.thumbnailUrl==None:
                sThumbnail ='http://static.arcgis.com/images/desktopapp.png' 
            elif ms.thumbnailUrl != None:
                sThumbnail=ms.thumbnailUrl
            elif ms.id !=None:
                sThumbnail ="http://www.arcgis.com/sharing/content/items/" + ms.id + "/info/" + ms.thumbnail
            else:
                sThumbnail='http://static.arcgis.com/images/desktopapp.png' 

            #todo, handle map service exports

            sTags = 'mapping' if ms.tags==None else ms.tags
            sType= 'Map Service' if ms.type==None else ms.type
            sDescription = '' if ms.description==None else ms.description
            sSnippet = '' if ms.snippet ==None else ms.snippet
            sExtent = '' if ms.extent==None else ms.extent
            sSpatialReference='' if ms.spatialReference==None else ms.spatialReference
            sAccessInfo='' if ms.accessInformation==None else ms.accessInformation
            sLicenseInfo='' if ms.licenseInfo==None else ms.licenseInfo
            sCulture='' if ms.culture == None else ms.culture

            parameters = urllib.urlencode({'URL' : sURL,
                                           'title' : sTitle,
                                           'thumbnailurl' : sThumbnail,
                                           'tags' : sTags, 
                                           'description' : sDescription,
                                           'snippet': sSnippet,
                                           'extent':sExtent,
                                           'overwrite':True,
                                           'spatialReference':sSpatialReference,
                                           'accessInformation': sAccessInfo,
                                           'licenseInfo': sLicenseInfo,
                                           'culture': sCulture,
                                           'type' : sType,
                                           'token' : self.user.token,
                                           'f' : 'json'})
            #todo- use export map on map service items for thumbnail

            requestToAdd = self.user.portalUrl + '/sharing/rest/content/users/' + self.user.username + folder + '/addItem'

            try:
                if(sType.find('Service')>=0 or sType.find('Web Mapping Application')>=0):
                    response = urllib.urlopen(requestToAdd, parameters ).read()

                    jresult = json.loads(response)
                    print str(i) + ") " + ms.title + ": success= " + str(jresult["success"]) + "," + ms.url + ", " + "(" + jresult["id"] + ")"

                    if jresult["success"]:
                        icount=icount+1
                        ms.id=jresult["id"]
                        ms.ownerFolder=jresult["folder"]
                        allresults.append(ms)

            except:
                print str(i) + ") "  + ms.title + ':error!'

        print str(icount) + " item(s) added."
        return allresults

    def getFolderID(self, folderName):
        '''
        Return the ID of the folder with the given name.
        '''
        folders = self._getUserFolders()

        for f in folders:
            if str(f['title']) == folderName:
                return str(f['id'])

        return ''

    def _getUserFolders(self):
        '''
        Return all folder objects.
        '''
        requestToAdd = self.user.portalUrl + '/sharing/rest/content/users/' + self.user.username +  '?f=json&token=' + self.user.token;
        response = urllib.urlopen(requestToAdd).read()

        jresult = json.loads(response)        
        return jresult["folders"]

    def randomizeToGroup(self,query,num,groupid):

        catalog=self.AGOLCatalog(query)

        random.shuffle(catalog)
        num=int(num)
        gallery=[]
        i=0
        for r in catalog:
            i=i+1
            gallery.append(r)
            if i>=num:
                break

            
        self.clearGroup(groupid)
        self.shareItems(gallery,groupid)

        return None

    def clearGroup(self, groupid):
        '''
        Unshare all content from the specified group.
        CAUTION
        '''
        groupcatalog = self.AGOLGroupCatalog(groupid)

        for f in groupcatalog:
            requestToDelete = self.user.portalUrl + '/sharing/rest/content/items/' + f.id + "/unshare?groups=" + groupid

            parameters = urllib.urlencode({
                'token' : self.user.token,
                'f' : 'json'})
            print "Unsharing " + f.title

            response = urllib.urlopen(requestToDelete,parameters).read()

            jresult = json.loads(response)     

        print "Complete."
        return None



        #sItems=''
        #for f in groupcatalog:
        #    sItems=sItems + f.id + "," 

        #l=len(sItems)-1
        #sItems=sItems[:l]
        #requestToDelete = self.user.portalUrl + '/sharing/rest/content/users/' + self.user.username + "/unshareItems"
        #parameters = urllib.urlencode({
        #        'token' : self.user.token,
        #        'groups' : groupid,
        #        'items' : sItems,
        #        'f' : 'json'})
        
           
        #print "Unsharing items..."

        #response = urllib.urlopen(requestToDelete,parameters).read()

        #jresult = json.loads(response)     

        #print "Complete."
        return None

    def clearFolder(self, folderid):
        '''
        Delete all content from the specified folder.
        CAUTION
        '''
        foldercatalog = self.AGOLUserCatalog(folderid)
        sItems=''
        for f in foldercatalog:
            sItems+= f.id + ","

        if len(sItems)>0: sItems=sItems[:-1]

        requestToDelete = self.user.portalUrl + '/sharing/rest/content/users/' + self.user.username + "/deleteItems" 

        parameters = urllib.urlencode({'items':sItems,
                                       'token' : self.user.token,
                                       'f' : 'json'})

        print "Deleting " + str(len(foldercatalog)) + " items..."
        response = urllib.urlopen(requestToDelete,parameters).read()

        jresult = json.loads(response)     
        print "Complete."
        return None

    def AGOLGroupCatalog(self, groupid):
        '''
        Return the catalog of items in desiginated group.
        '''
        sCatalogURL=self.user.portalUrl + "/sharing/rest/search?q=%20group%3A" + groupid + "%20-type:%22Code%20Attachment%22%20-type:%22Featured%20Items%22%20-type:%22Symbol%20Set%22%20-type:%22Color%20Set%22%20-type:%22Windows%20Viewer%20Add%20In%22%20-type:%22Windows%20Viewer%20Configuration%22%20%20-type:%22Code%20Attachment%22%20-type:%22Featured%20Items%22%20-type:%22Symbol%20Set%22%20-type:%22Color%20Set%22%20-type:%22Windows%20Viewer%20Add%20In%22%20-type:%22Windows%20Viewer%20Configuration%22%20&num=100&sortField=title&sortOrder=asc"

        return self.AGOLCatalog(None,None,sCatalogURL)

    def findWebmapService(self, webmapId, oldUrl, folderID=None):
        try:
            params = urllib.urlencode({'token' : self.user.token,
                                       'f' : 'json'})
            #print 'Getting Info for: ' + webmapId
            #Get the item data
            reqUrl = self.user.portalUrl + '/sharing/content/items/' + webmapId + '/data?' + params
            itemDataReq = urllib.urlopen(reqUrl).read()
            itemString = str(itemDataReq)

            #See if it needs to be updated
            if itemString.find(oldUrl) > -1:
                return True
            else:
                #print 'Didn\'t find any services for ' + oldUrl
                return False

        except ValueError as e:
            print 'Error - no web maps specified'
        except AGOPostError as e:
            print 'Error updating web map ' + e.webmap + ": " + e.msg

    def findItemUrl(self, item, oldUrl, folderID=None):
        '''
        Use this to find the URL for items such as Map Services.
        This can also find part of a URL. The text of oldUrl is replaced with the text of newUrl. For example you could change just the host name of your URLs.
        '''
        try:

            if item.url == None:
                #print item.title + ' doesn\'t have a url property'
                return False

            # Double check that the existing URL matches the provided URL
            if item.url.find(oldUrl) > -1:
                return True
            else:
                #print 'Didn\'t find the specified old URL: ' + oldUrl
                return False
        except ValueError as e:
            print e
            return False

    def __decode_dict__(self, dct):
        newdict = {}
        for k, v in dct.iteritems():
            k = self.__safeValue__(k)
            v = self.__safeValue__(v)
            newdict[k] = v
        return newdict

    def __safeValue__(self, inVal):
        outVal = inVal
        if isinstance(inVal, unicode):
            outVal = inVal.encode('utf-8')
        elif isinstance(inVal, list):
            outVal = self.__decode_list__(inVal)
        return outVal

    def __decode_list__(self, lst):
        newList = []
        for i in lst:
            i = self.__safeValue__(i)
            newList.append(i)
        return newList

    def json_to_obj(self,s):
        def h2o(x):
            if isinstance(x, dict):
                return type('jo', (), {k: h2o(v) for k, v in x.iteritems()})
            else:
                return x
        return h2o(json.loads(s))



    def addBookmarksToWebMap(self,pBookmarks,webmapId):
        '''
        update the designated webmap with the list of bookmark objects
        '''

        #read webmap json
        try:
            params = urllib.urlencode({'token' : self.user.token,
                                       'f' : 'json'})

            print 'Getting Info for: ' + webmapId
            #Get the item data
            reqUrl = self.user.portalUrl + '/sharing/content/items/' + webmapId + '/data?' + params
            itemDataReq = urllib.urlopen(reqUrl).read()
            itemData = json.loads(itemDataReq, object_hook=self.__decode_dict__)
                        
            #add bookmarks into object list
            itemData['bookmarks']=pBookmarks

            #convert the updated json object back to string
            sItemDataText=json.dumps(itemData, separators=(',',':'))

            #get original item definition for update
            itemInfoReq = urllib.urlopen(self.user.portalUrl + '/sharing/content/items/' + webmapId + '?' + params)
            itemInfo = json.loads(itemInfoReq.read(), object_hook=self.__decode_dict__)
            
            #write original back as test
            outParamObj = {
                'extent' : ', '.join([str(itemInfo['extent'][0][0]), str(itemInfo['extent'][0][1]), str(itemInfo['extent'][1][0]), str(itemInfo['extent'][1][1])]),
                'type' : itemInfo['type'],
                'item' : itemInfo['item'],
                'title' : itemInfo['title'],
                'overwrite' : 'true',
                'tags' : ','.join(itemInfo['tags']),
                'text' : sItemDataText
            }
            # Get the item folder.
            if itemInfo['ownerFolder']:
                folderID = itemInfo['ownerFolder']
            else:
                folderID = ''

            nBookmarksCount=str(len(pBookmarks))
            print "Updating Webmap with " + nBookmarksCount + " bookmarks..."

            #Post back the changes overwriting the old map
            modRequest = urllib.urlopen(self.user.portalUrl + '/sharing/content/users/' + self.user.username + '/' + folderID + '/addItem?' + params , urllib.urlencode(outParamObj))
            
            #Evaluate the results to make sure it happened
            modResponse = json.loads(modRequest.read())
            if modResponse["success"]!=True:
                print "The update was NOT successful."
            else:
                print "The update WAS successful."

            return None


        except ValueError as e:
            print 'Error:'+ e.message


        return None

    def readBookmarksFromFeatureClass(self,path,labelfield):
        
        import arcpy

        bmarks=[]
        fieldnames = [labelfield,"SHAPE@"]
        wkid = "4326" 
        myCursor = arcpy.da.SearchCursor(path,fieldnames,"",wkid)
        for row in myCursor:
            bm = bookmark()
            extent = row[1].extent
            bm.extent.xmin = extent.lowerLeft.X
            bm.extent.ymin = extent.lowerLeft.Y
            bm.extent.xmax = extent.upperRight.X
            bm.extent.ymax = extent.upperRight.Y
            bm.extent.SpatialReference.wkid = wkid
            bm.name=row[0].title()

            bmarks.append(bm.to_JSON2())

        return bmarks

    def createBookmarksFromLayer(self, url,labelfield):

        import arcpy

        bmarks=[]
        try:
            
            where = '1=1'
            fields ='*'

            token = ''
            #SBTEST when to use token?
            if(url.find("arcgis.com")>0):
                token = self.user.token
 
            #The above variables construct the query
            query = "/query?where={}&outFields={}&returnGeometry=true&f=json&token={}".format(where, fields, token)
        
            fsURL = url + query
 
            fs = arcpy.FeatureSet()
            fs.load(fsURL)
            fieldnames = [labelfield,"SHAPE@"]

            wkid = "4326"   #use geographic for bookmarks, easier to confirm
            myCursor = arcpy.da.SearchCursor(fs,fieldnames,"",wkid)

            for row in myCursor:
                bm = bookmark()
                extent = row[1].extent

                #handle points
                if extent.lowerLeft.X == extent.upperRight.X:
                    myX=extent.lowerLeft.X
                    myY=extent.lowerLeft.Y 
                    nTol=.05
                    myLL = arcpy.Point(myX-nTol,myY-nTol)
                    myUR = arcpy.Point(myX+nTol,myY+nTol)

                    bm.extent.xmin = myLL.X
                    bm.extent.ymin = myLL.Y
                    bm.extent.xmax = myUR.X
                    bm.extent.ymax = myUR.Y

                else:
                    bm.extent.xmin = extent.lowerLeft.X
                    bm.extent.ymin = extent.lowerLeft.Y
                    bm.extent.xmax = extent.upperRight.X
                    bm.extent.ymax = extent.upperRight.Y

                bm.extent.SpatialReference.wkid = wkid
                bm.name=row[0].title()

                bmarks.append(bm.to_JSON2())


        except ValueError as e:
            print 'Error: ' +e.message

        return bmarks


    def readBookmarksFromFile(self,inputfile):
        with open(inputfile) as input:
            data = json.load(input)
            return data["bookmarks"]
    
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
    
    def readBookmarksFromFeatureCollection(self,fcId,labelfield):
        pBookmarks=[]

        #    def readBookmarksFromFeatureClass(self,path,labelfield):
        #bmarks=[]
        #fieldnames = [labelfield,"SHAPE@"]
        #wkid = "4326" 
        #myCursor = arcpy.da.SearchCursor(path,fieldnames,"",wkid)
        #for row in myCursor:
        #    bm = bookmark()
        #    extent = row[1].extent
        #    bm.extent.xmin = extent.lowerLeft.X
        #    bm.extent.ymin = extent.lowerLeft.Y
        #    bm.extent.xmax = extent.upperRight.X
        #    bm.extent.ymax = extent.upperRight.Y
        #    bm.extent.SpatialReference.wkid = wkid
        #    bm.name=row[0].title()

        #    bmarks.append(bm.to_JSON2())


        params = urllib.urlencode({'token' : self.user.token,
                            'f' : 'json'})
        #print 'Getting Info for: ' + webmapId
        #Get the item data
        reqUrl = self.user.portalUrl + '/sharing/content/items/' + fcId + '/data?' + params
        itemDataReq = urllib.urlopen(reqUrl).read()
        itemString = str(itemDataReq)

        pp=json.loads(itemString)
        
        for f in pp["layers"][0]["featureSet"]["features"]:
            
            x=f["geometry"]["x"];
            y=f["geometry"]["y"];
            bmark=bookmark()
            bmark.extent.xmin=x-10000
            bmark.extent.xmax=x+10000
            bmark.extent.ymin=y-10000
            bmark.extent.ymax=y+10000
            bmark.name=f["attributes"][labelfield]

            pBookmarks.append(bmark.to_JSON3("102100"))

        return pBookmarks
    def findItemsWithURLs(self, oldUrl,folder):
        
        if(folder!=None):
            catalog = self.AGOLUserCatalog(folder,False)
        else:
            catalog=self.AGOLCatalog(None)

        allResults = []

        '''
        Find the URL or URL part for all URLs in a list of AGOL items.
        This works for all item types that store a URL. (e.g. web maps, map services, applications, etc.)
        oldUrl -- All or part of a URL to search for.
        newUrl -- The text that will be used to replace the current "oldUrl" text.
        '''
        countWebMaps=0
        countServicesOrApps=0
        i=0
        iLength=len(catalog)
        for item in catalog:
            i=i+1
            print str(i) + '/' + str(iLength)
            if item.type == 'Web Map':
                v=self.findWebmapService(item.id, oldUrl)
                if v==True:
                    dosomething=True
                    countWebMaps=countWebMaps+1
                    allResults.append(item)
            else:
                if not item.url == None:
                    v=self.findItemUrl(item, oldUrl)
                    if v==True:
                        dosomething=True
                        countServicesOrApps=countServicesOrApps+1
                        allResults.append(item)

        count=countServicesOrApps + countWebMaps
        return allResults


    def AGOLUserCatalog(self, folder, includeSize=False):
        '''
        Return the catalog of CURRENT USER's items from portal, optionally from only a folder.
        '''
        sCatalogURL = self.user.portalUrl + "/sharing/rest/content/users/" + self.user.username + folder
        return self.AGOLCatalog(None,None,sCatalogURL)

    def AGOLCatalog(self, query=None, includeSize=False, sCatalogURL=None, bRestrictToOrg=True):
        '''
        Return all items from all users in a portal, optionally matching a 
        specified query.
        optionally make the additional requests for SIZE.
        sCatalogURL can be specified to use a specific folder
        '''

        resultCount = 0
        searchURL = ""
        viewURL = ""
        orgID = ""
        self.sFullSearch = ""
        self.bIncludeSize=includeSize

        if bRestrictToOrg:
            self.orgID = self._getOrgID()
        else:
            self.orgID=None

        self.catalogURL=sCatalogURL #for cataloging folders

        if self.user.portalUrl != None:
            self.searchURL = self.user.portalUrl  + "/sharing/rest" 
            self.viewURL = self.user.portalUrl  + "/home/item.html?id="

        query=str(query).replace('&quot','"')
        self.query = query

        pList=[]
        allResults = []

        sQuery=self._getCatalogQuery(1,100)#get first batch

        print("fetching records 1-100...")

        response = urllib.urlopen(sQuery).read()
        jresult=json.loads(response)

        nextRecord = jresult['nextStart']
        totalRecords = jresult['total']
        num = jresult['num']
        start =jresult['start']

        #if this is a folder catalog, use items, not results
        sItemsProperty = 'results'
        if self.catalogURL!=None and str(self.catalogURL).find("/sharing/rest/content/users/")>0: sItemsProperty='items'

        pList = AGOLItems( jresult[sItemsProperty])

        for r in pList.AGOLItems_list:
            r.itemURL = self.viewURL + r.id
            r.created = time.strftime("%Y-%m-%d",time.gmtime(r.created/1000))
            r.modified = time.strftime("%Y-%m-%d",time.gmtime(r.modified/1000))
            if r.size== -1:
                r.size=0
            r.size = self._getSize(r)
            
            r.thumbnailUrl = self._fixThumbnail(r)

            r.myRowID = len(allResults) + 1;
            allResults.append(r)

        if (nextRecord>0):
            while(nextRecord>0):
                sQuery = self._getCatalogQuery(nextRecord, 100)
                print("fetching records " + str(nextRecord) + "-" + str(nextRecord+100) + "...")

                response = urllib.urlopen(sQuery).read()
                jresult=json.loads(response)

                nextRecord = jresult['nextStart']
                totalRecords = jresult['total']
                num = jresult['num']
                start =jresult['start']

                pList = AGOLItems( jresult[sItemsProperty])
                for r in pList.AGOLItems_list:
                    r.itemURL = self.viewURL + r.id
                    r.created = time.strftime("%Y-%m-%d",time.gmtime(r.created/1000))
                    r.modified = time.strftime("%Y-%m-%d",time.gmtime(r.modified/1000))
                    if r.size== -1:
                        r.size=0
                        r.size = self._getSize(r)
                    r.myRowID = len(allResults) + 1;
                    r.thumbnailUrl = self._fixThumbnail(r)
                    allResults.append(r)

        return allResults

    def _fixThumbnail(self,r):
        
        #self.user.portalUrl
        #+/sharing/rest/content/items
        #+/id
        #+/info/thumbnail/
        #+thumbnail
        if(r==None):
          return ''

        r2=''
        
        if(r.id and r.thumbnail):
          r2=self.user.portalUrl + "/sharing/rest/content/items/" + r.id + "/info/" + r.thumbnail
        #SBTEST r2=r2 + "?token=" + self.user.token

         
        return r2

    def _getSize(self, r):
        '''
        Issue query for item size.
        '''
        try:
          if(self.bIncludeSize != True):
              return 0

          if(r.title and r.type):
            print ("now fetching size for " + r.title + " (" + r.type + ")")

          result=0
          sURL = self.searchURL + "/content/items/" + str(r.id) + "?f=json&token=" + self.user.token;

          response = urllib.urlopen(sURL).read()
          result = json.loads(response)['size']
          if(result>0):
              result = result/1024
          else:
              result=0

          return result

        except Exception as e:
          print("_getSize error: " + e.message)
          return 0

    def _getSharing(self, v):
        '''
        Issue query for item sharing.
        '''

        print ("fetching sharing for " + v.title + " (" + v.type + ")")

          #have to get ownerFolder
        parameters = urllib.urlencode({'token' : self.user.token, 'f': 'json'})
        requestForInfo = self.user.portalUrl + '/sharing/rest/content/items/' + v.id
 
        response = urllib.urlopen(requestForInfo, parameters ).read()

        jResult = json.loads(response)

        if('error' in jResult):
            print str(i)  + ') ' + v.title + " (" + v.id + ") was not found and will be skipped." 
        else:
            if jResult['ownerFolder']:
                folderID = jResult['ownerFolder']
            else:
                folderID = ''
        sUser=v.owner
        sUser=self.user.username

        requestForInfo2 = self.user.portalUrl + '/sharing/rest/content/users/' + sUser + '/' + folderID + '/items/' + v.id 
        response2 = urllib.urlopen(requestForInfo2, parameters ).read()
        jResult2 = json.loads(response2)

        return jResult2["sharing"]["groups"]


    def _getOrgID(self):
        '''
        Return the organization's ID.
        '''
        sURL = self.user.portalUrl + "/sharing/rest/portals/self?f=json&token=" + self.user.token

        response = urllib.urlopen(sURL).read()

        return str(json.loads(response)['id'])

    def _getCatalogQuery(self, start, num):
        '''
        Format a content query from specified start and number of records.
        '''
        sQuery=None
        if self.query != None:
            sQuery = self.query
        else:
            sQuery = self.sFullSearch

        if(self.catalogURL==None):
            sCatalogQuery = self.searchURL + "/search?q=" + sQuery
            if self.orgID != None:
                sCatalogQuery += " orgid:" + self.orgID
        else:
            #check to ensure ? vs &
            if(str(self.catalogURL).find('?')<0):
                char="?"
            else:
                char="&"

            sCatalogQuery = self.catalogURL + char + "ts=1" 

        sCatalogQuery += "&f=json&num="+ str(num) + "&start=" + str(start)
        sCatalogQuery += "&token=" + self.user.token

        return sCatalogQuery

    def updateUserRoles(self, users):
        self.usersToUpdate=users

        requestToUpdate= self.user.portalUrl + '/sharing/rest/portals/self/updateuserrole'

        for u in self.usersToUpdate.user_list:
            parameters = urllib.urlencode({'user':u.Username,
                                           'role':u.Role,
                                           'token' : self.user.token,
                                           'f' : 'json'})

            print "Updating Role for " + u.Username + " to " + u.Role + "..."
            response = urllib.urlopen(requestToUpdate,parameters).read()
            jresult = json.loads(response)     
            success= str(jresult["success"])
            print "Success: " + success

        print "Complete."
        return None

    
#collection of AGOLItem
class AGOLItems:
    def __init__ (self, item_list):
        self.AGOLItems_list=[]
        for item in item_list:
            self.AGOLItems_list.append(AGOLItem(item))

#AGOL item
class AGOLItem:
    def __init__(self, item_attributes):
        for k, v in item_attributes.items():
            setattr(self, k, v)

#collection of Map Services
class MapServices:
    def __init__ (self, import_list):
        self.service_list=[]
        for service in import_list:
            self.service_list.append(MapService(service))

#Map Service
class MapService:
    def __init__(self, service_attributes):
        for k, v in service_attributes.items():
            setattr(self, k, v)

#Collection of Usernames and roles
class UsersAttributes:
    def __init__ (self, import_list):
        self.user_list=[]
        for user in import_list:
            self.user_list.append(UserAttributes(user))

class UserAttributes:
    def __init__(self, user_attributes):
        for k, v in user_attributes.items():
            setattr(self, k, v)



class bookmark(object):

    def __init__(self):
        self.name = None
        self.extent = self.bb()

    def to_JSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=2,separators=(',',':'))

    def to_JSON2(self):
                #     extent = row[1].extent
                #bm.extent.xmin = extent.lowerLeft.X
                #bm.extent.ymin = extent.lowerLeft.Y
                #bm.extent.xmax = extent.upperRight.X
                #bm.extent.ymax = extent.upperRight.Y
                #bm.extent.SpatialReference.wkid = wkid
                #bm.name=row[0].title()
        #s='{"extent":{"SpatialReference":{"wkid":"4326"},"xmax":-77.58890542503474,"xmin":-77.66083839947551,"ymax":42.58041413631198,"ymin":42.549020481314585},"name":"Wayland 200"}'#.format(self.extent.xmin,self.extent.xmax,self.extent.ymin,self.extent.ymax,self.name)
        s='{"extent":{"SpatialReference":{"wkid":"4326"},"xmax":' + str(self.extent.xmax) +',"xmin":' + str(self.extent.xmin) + ',"ymax":' + str(self.extent.ymax) +',"ymin":' + str(self.extent.ymin) + '},"name":"' + self.name + '"}'
        #.format(self.extent.xmin,self.extent.xmax,self.extent.ymin,self.extent.ymax,self.name)
        
        return json.loads(s)

    def to_JSON3(self,wkid):
                #     extent = row[1].extent
                #bm.extent.xmin = extent.lowerLeft.X
                #bm.extent.ymin = extent.lowerLeft.Y
                #bm.extent.xmax = extent.upperRight.X
                #bm.extent.ymax = extent.upperRight.Y
                #bm.extent.SpatialReference.wkid = wkid
                #bm.name=row[0].title()
        #s='{"extent":{"SpatialReference":{"wkid":"4326"},"xmax":-77.58890542503474,"xmin":-77.66083839947551,"ymax":42.58041413631198,"ymin":42.549020481314585},"name":"Wayland 200"}'#.format(self.extent.xmin,self.extent.xmax,self.extent.ymin,self.extent.ymax,self.name)
        #SBTEST s='{"extent":{"SpatialReference":{"wkid":'  + wkid  +  '},"xmax":' + str(self.extent.xmax) +',"xmin":' + str(self.extent.xmin) + ',"ymax":' + str(self.extent.ymax) +',"ymin":' + str(self.extent.ymin) + '},"name":"' + self.name + '"}'
        s='{"extent":{"SpatialReference":{"wkid":'  + wkid  +  '},"xmin":' + str(self.extent.xmin) +',"ymin":' + str(self.extent.ymin) + ',"xmax":' + str(self.extent.xmax) +',"ymax":' + str(self.extent.ymax) + '},"name":"' + self.name + '"}'
        
        #.format(self.extent.xmin,self.extent.xmax,self.extent.ymin,self.extent.ymax,self.name)
        
        return json.loads(s)

    class bb(object):
        def __init__(self):
            self.SpatialReference = self.sr()
            self.xmax = 0.0
            self.ymax = 0.0
            self.xmin = 0.0
            self.ymin = 0.0

        class sr(object):
            def __init__(self):
                self.wkid = ""
