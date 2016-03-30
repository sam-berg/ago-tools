#### Register items listed in an input CSV to the organization
#### Optionally place the items into a specific folder under My Content
#### The required fields in the CSV are:
#### title,url 
#### The following fields will be honored if present, otherwise default values will be used:
#### thumbnail,tags,type,description,snipppet,extent,spatialReference,accessInformation,licenseInfo,culture
#### Note that 'tags' if not specified will be Mapping and 'type' if not specified will be 'Map Service' 
#### Example:
#### registerItems.py -u myuser -p mypassword -folder MyNewItems -portal https://esri.maps.arcgis.com -file c:\temp\agolinput.csv

import csv
import argparse
import sys

from agoTools.admin import Admin
from agoTools.admin import MapService
from agoTools.admin import MapServices

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

# return value with quotes around it always
def getResultValueWithQuotes(s):
    if (s==None):
        return ''
    try:
        sResult = str(s)
        if (sResult.find("\"")>0):
            sResult = sResult.replace("\"","\"\"")
        return "\"" + str(sResult) + "\""

    except:
        return ''

# return value with quotes if needed
def getResultValue(s):
    if (s==None):
        return ''
    try:
        sResult = str(s)
        if(sResult.find(",")>0 or sResult.find("\r\n")>0):
            sResult = sResult.replace("\"", "\"\"")
            return "\"" + str(sResult) + "\""
        else:
            return str(sResult)
    except:
        return ''

parser = argparse.ArgumentParser()
parser.add_argument('-u', '--user')
parser.add_argument('-p', '--password')
parser.add_argument('-folder', '--folder')
parser.add_argument('-file', '--file')
parser.add_argument('-outfile', '--outfile')
parser.add_argument('-portal', '--portal')

args = parser.parse_args()
inputFile = ''

if args.file == None:
    args.file = _raw_input("CSV path: ")

if args.user == None:
    args.user = _raw_input("Username:")

if args.portal == None:
    args.portal = _raw_input("Portal: ")

#if args.folder == None:
#    args.folder = _raw_input("Folder (optional): ")

args.portal = str(args.portal).replace("http://","https://")

agoAdmin = Admin(args.user,args.portal,args.password)

folderid=None
if args.folder!= None:
    fid = agoAdmin.getFolderID(args.folder)
    args.folder=fid
    folderid = '/' + args.folder

if args.file != None:
    inputFile=args.file

with open(inputFile) as input:
    dataReader = csv.DictReader(input)
    mapServices=MapServices(dataReader)

catalog = agoAdmin.registerItems(mapServices,folderid)

if args.outfile!=None and catalog !=None:
    #write
    with open(args.outfile, 'wb') as output:
        # Write header row.
        output.write("id,owner,created,modified,name,title,type,typeKeywords,description,tags,snippet,thumbnail,extent,spatialReference,accessInformation,licenseInfo,culture,url,access,size,listed,numComments,numRatings,avgRatings,numViews,itemURL,thumbnailUrl\n")
        # Write item data.
        for r in catalog:
            s=''
            s += getResultValue(r.id) + ","
            s += getResultValue(r.owner) + ","
            s += getResultValue(r.created) + ","
            s += getResultValue(r.modified) + ","
            s += getResultValueWithQuotes(r.name) + ","
            s += getResultValueWithQuotes(r.title) + ","
            s += getResultValue(r.type) + ","

            sKeyWords = ""
            for sKW in r.typeKeywords:
                sKeyWords += sKW + ","

            if (len(sKeyWords)> 0 and sKeyWords.endswith(",")):
                sKeyWords = sKeyWords[:-1]

            s += getResultValue(sKeyWords) + ","
            s += getResultValueWithQuotes(r.description) + ","

            sTags = ""
            for sKW in r.tags:
                sTags += sKW + ","

            if (len(sTags)> 0 and sTags.endswith(",")):
                sTags = sTags[:-1]

            s += getResultValue(sTags) + ","
            s += getResultValueWithQuotes(r.snippet) + ","
            s += getResultValue(r.thumbnail) + ","
            s += "" + ","

            s += getResultValue(r.spatialReference) + ","
            s += getResultValue(r.accessInformation) + ","
            s += getResultValue(r.licenseInfo) + ","
            s += getResultValue(r.culture) + ","

            s += getResultValue(r.url) + ","
            s += getResultValue(r.access) + ","
            s += getResultValue(r.size) + ","

            s += getResultValue(r.listed) + ","
            s += getResultValue(r.numComments) + ","
            s += getResultValue(r.numRatings) + ","
            s += getResultValue('') + ","
            s += getResultValue('') + ","


            s += getResultValue('') + ",";
            s += getResultValue('');
            s+="\n"

            output.writelines(s)

        print (args.outfile + " written.")
