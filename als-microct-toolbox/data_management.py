import os
import sys
import time

import logging

logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(message)s')

import numpy as np  # fundamental numeric operations package
import tomopy  # tomographic reconstrcution package
import dxchange
import h5py

import glob

import getpass  # allows commandline password input

import requests  # tools for web requests/communication with online APIs


class SpotSession:
    """This class includes all functions for authenticating and communicating with SPOT API.

    Attributes
        ----------
        username : str
            SPOT username for authentication.

    """

    def __init__(self, username='default', password=None):
        """Creates SPOT session class.

        Parameters
        ----------
        username : str
            SPOT username for authentication.

        """

        if password is None:
            password = getpass.getpass()

        self.URL_authentication = "https://portal-auth.nersc.gov/als/auth"
        self.username = 'alvarorh'
        self.spot_username = username
        spot_password = password

        if username == 'default':  # if no additional usermane is given, spot username is stored to be used in file paths
            self.spot_username = self.username

        s = requests.Session()
        r = s.get(self.URL_authentication)
        r = s.post(self.URL_authentication, {"username": self.spot_username, "password": spot_password})
        self.session = s

    """
POST
URL:
https://portal-auth.nersc.gov/als/auth
EXAMPLE:
% curl -k -c cookies.txt -X POST -d "username=[your_username]&password=[your_password]" https://portal-auth.nersc.gov/als/auth
    """

    # =============================================================================
    # Check Authentication
    # tested, works properly

    def check_authentication(self):
        """Checks authentication of SPOT session.

        Returns
        ------
        JSON object
            Returns authorization entry of JSON list.
                True - SPOT session is authenticated.
                False - SPOT session is not authenticated.

        """

        r = self.session.get(self.URL_authentication)

        return r.json()['auth']

    def authentication(self):
        """Asks for SPOT credentials for authentication.

        Returns
        ------
        JSON object
            Returns authorization entry of JSON list.
                True - SPOT session is authenticated.
                False - SPOT session is not authenticated.

        """

        s = self.session
        r = s.get(self.URL_authentication)
        if r.json()['auth'] == False:
            print("Authentication required to start a new session")
            spot_username = input("username:")
            spot_password = getpass.getpass()
            s = requests.Session()
            r = s.post(self.URL_authentication, {"username": spot_username, "password": spot_password})
            self.session = s
        r = s.get(self.URL_authentication)
        return r.json()['auth']

    # =============================================================================
    # Close session
    # Under development (almost works)
    def close(self):
        """Closes SPOT session.

        Returns
        ------
        JSON object
            Returns readable JSON object with True/False depending if the session was successfully closed.

        """

        self.session.close()
        r = self.session.get(self.URL_authentication)
        return r.json()

    # =============================================================================
    # Search Datasets
    # tested, works properly, returns list of json oblejcts
    def search(self, search, limitnum=10, skipnum=0, sortterm="fs.stage_date", sorttype="desc"):
        """Searches for datasets matching the given input paramters.

        Parameters
        ----------
        search : str
            Query beamline or "end_station" (ex. "bl832")
        limitnum : int
            Number of results to show.
        skipnum: int
            Number of results to skip.
        sortterm: str
            Database field on which to sort (commonly fs.stage_date or appmetadata.sdate).
        sorttype: str
            desc or asc

        Returns
        ------
        JSON List
            List of datasets as JSON objects.

        """

        self.URL_search = "https://portal-auth.nersc.gov/als/hdf/search"
        self.PARAMS_search = {"limitnum": limitnum, "skipnum": skipnum, "sortterm": sortterm, "sorttype": sorttype,
                              "search": search}
        r = self.session.get(url=self.URL_search, params=self.PARAMS_search)
        return r.json()  # returns list of JSON objects containing search results

    """
GET
URL:
https://portal-auth.nersc.gov/als/hdf/search
Arguments:
limitnum: number of results to show
skipnum: number of results to skip
sortterm: database field on which to sort (commonly fs.stage_date or appmetadata.sdate)
sorttype: desc or asc
search: query
Result:
JSON List
EXAMPLE:
% curl -k -b cookies.txt -X GET "https://portal-auth.nersc.gov/als/hdf/search?skipnum=0&limitnum=10&sortterm=fs.stage_date&sorttype=desc&search=end_station=bl832"
    """

    # =============================================================================
    # Find Derived Datasets (norm, sino, gridrec, imgrec) from raw dataset
    # Tested, works properly, returns list of json objects

    def derived_datasets(self, dataset):
        """Find derived datasets (norm, sino, gridrec, imgrec) from raw dataset.

        Parameters
        ----------
        dataset : str
            The name of an existing dataset on SPOT.
        Returns
        ------
        JSON List
            List of derived datasets as JSON objects.

        """

        dataset = dataset.strip(".h5")

        self.URL_DerivedDatasets = "https://portal-auth.nersc.gov/als/hdf/dataset"
        self.PARAMS_DerivedDatasets = {"dataset": dataset}

        r = self.session.get(self.URL_DerivedDatasets, params=self.PARAMS_DerivedDatasets)

        return r.json()

    """
GET
URL:
https://portal-auth.nersc.gov/als/hdf/dataset
Arguments:
dataset: raw dataset
Result:
JSON List
EXAMPLE:
% curl -k -b cookies.txt -X GET "https://portal-auth.nersc.gov/als/hdf/dataset?dataset=20130713_185717_Chilarchaea_quellon_F_9053427_IKI_"
    """

    # =============================================================================
    # Takes dataset name and formats for use in API calls
    # tested, used in class methods that require [dataset] entry in URL

    def formatPath(self, dataset, username='default'):
        """Formats dataset path for use in other methods.

        Parameters
        ----------
        dataset : str
            The name of an existing dataset on SPOT.
        username: str
            Username associated with dataset.

        Returns
        ------
        filename
            Formatted filename for given dataset.
        username
            Username associated with dataset.

        """

        dataset = dataset.strip(".h5")

        if username == 'default' or username == None:
            username = self.spot_username
            filename = dataset

        elif "/" in dataset:  # determine if dataset contains username and splits
            # 'username/filename' becomes two separate strings: username and filename
            datasplit = dataset.split("/")
            username = datasplit[-2]
            filename = datasplit[-1]

        else:
            filename = dataset

        return filename, username

    # =============================================================================
    # View Attributes for Single Dataset and Image Within Dataset
    # Tested, works properly
    # Add single image functionality

    def attributes(self, dataset, username=None):
        """View attributes for single dataset and image within dataset

        Parameters
        ----------
        dataset : str
            The name of an existing dataset on SPOT.
        username: str
            Username associated with dataset.

        Returns
        ------
        JSON Array
            Dataset or image attributes.

        """

        self.URL_attributes = "https://portal-auth.nersc.gov/als/hdf/attributes/als/bl832/"

        dataset, username = self.formatPath(dataset, username=username)

        URLstring = self.URL_attributes + username + "/" + dataset + "/raw/" + dataset + ".h5"

        r = self.session.get(url=URLstring, params={"group": "/"})

        return r.json()

    """
GET
URL:
https://portal-auth.nersc.gov/als/hdf/attributes/[dataset]
Arguments:
group: path in hdf5 file. Set to "/" for overall attributes
Result:
JSON Array
EXAMPLE:
% curl -k -b cookies.txt -X GET "https://portal-auth.nersc.gov/als/hdf/attributes/als/bl832/hmwood/20130713_185717_Chilarchaea_quellon_F_9053427_IKI_/raw/20130713_185717_Chilarchaea_quellon_F_9053427_IKI_.h5?group=/"
    """

    # =============================================================================
    # List Images Within Dataset
    # Tested, works properly

    def list_images(self, dataset, username):
        """List Images within dataset.

        Parameters
        ----------
        dataset : str
            The name of an existing dataset on SPOT.
        username: str
            Username associated with dataset.

        Returns
        ------
        JSON List
            Paths to images within the HDF5 file.

        """

        dataset = dataset.strip(".h5")
        self.URL_listImages = "https://portal-auth.nersc.gov/als/hdf/listimages/als/bl832/"
        URLstring = self.URL_listImages + username + "/" + dataset + "/raw/" + dataset + ".h5"
        r = self.session.get(URLstring)
        return r.json()

    """
 GET
URL:
https://portal-auth.nersc.gov/als/hdf/listimages/[dataset]
Arguments:
None
Result:
JSON List (paths to images within the HDF5 file)
EXAMPLE:
% curl -k -b cookies.txt -X GET "https://portal-auth.nersc.gov/als/hdf/listimages/als/bl832/hmwood/20130713_185717_Chilarchaea_quellon_F_9053427_IKI_/raw/20130713_185717_Chilarchaea_quellon_F_9053427_IKI_.h5"
    """

    # =============================================================================
    # Stage Dataset From Tape to Disk if Required
    # 	NOT Tested
    # 	... Not sure how to figure figure out when staging is complete.
    def stage(self, dataset, username='default'):
        """Stage dataset from tape to disk if required.

        Parameters
        ----------
        dataset : str
            The name of an existing dataset on SPOT.
        username: str
            Username associated with dataset.

        Returns
        ------
        JSON Array
            Details of staging process.

        """

        fileName, username = self.formatPath(dataset, username)
        self.URL_stage = "https://portal-auth.nersc.gov/als/hdf/stageifneeded/als/bl832/"
        URL_string = self.URL_stage + username + "/" + fileName + "/raw/" + fileName + ".h5"
        r = self.session.get(url=URL_string)
        return r.json()

    """
 GET
URL:
https://portal-auth.nersc.gov/als/hdf/stageifneeded/[dataset]
Arguments:
None
Result:
JSON Array
EXAMPLE:
% curl -k -b cookies.txt -X GET "https://portal-auth.nersc.gov/als/hdf/stageifneeded/als/bl832/hmwood/20130713_185717_Chilarchaea_quellon_F_9053427_IKI_/raw/20130713_185717_Chilarchaea_quellon_F_9053427_IKI_.h5"
    """

    # =============================================================================
    # Download Dataset
    # Tested, works properly

    def download(self, dataset, username='default', downloadPath='default', downloadName='default'):
        """Downloads dataset (HDF5 file)

        Parameters
        ----------
        dataset : str
            The name of an existing dataset on SPOT.
        username: str
            Username associated with dataset.
        downloadPath : str
            Directory where to write file to.
        downloadName : str
            Name of file in specified directory.

        Returns
        ------
        fileLocation
            Where the downloaded dataset is located.

        """

        filename, username = self.formatPath(dataset, username=username)  # process input path
        downloadName = downloadName.strip('.h5')  # remove .h5 from output file name

        self.URL_download = "https://portal-auth.nersc.gov/als/hdf/download/als/bl832/"

        if downloadPath == 'default':
            downloadPath = "./"

        if downloadName == 'default':
            downloadName = filename

        if downloadPath[-1] != "/":  # add "/" to output path if it is not included
            downloadPath = downloadPath + "/"

        URL_string = self.URL_download + username + "/" + filename + "/raw/" + filename + ".h5"

        r = self.session.get(URL_string)

        fileLocation = downloadPath + downloadName + ".h5"

        location = open(fileLocation, "wb")

        for chunk in r.iter_content(chunk_size=512):
            if chunk:
                location.write(chunk)

        print('download  complete: ' + fileLocation)

        return fileLocation

    """
 GET
URL:
https://portal-auth.nersc.gov/als/hdf/download/[dataset]
Arguments:
None
Result:
H5 File
EXAMPLE:
% curl -k -b cookies.txt -X GET "https://portal-auth.nersc.gov/als/hdf/download/als/bl832/hmwood/20130713_185717_Chilarchaea_quellon_F_9053427_IKI_/raw/20130713_185717_Chilarchaea_quellon_F_9053427_IKI_.h" > file.h5
    """

    # =============================================================================
    # Download Rawdata For Individual Image
    # *** NOT TESTED ***

    def download_image(self, dataset, username='default', kind='raw', number=0, downloadPath='default', downloadName='default'):
        """Download rawdata for individual image.

        Parameters
        ----------
        dataset : str
            The name of an existing dataset on SPOT.
        username: str
            Username associated with dataset.
        kind : str
            Type of data (norm, sino, gridrec, imgrec, etc).
        number : int
            Specific image number in list of images for the dataset.
        downloadPath : str
            Directory where to write file to.
        downloadName : str
            Name of file in specified directory.

        Returns
        ------
        filelocation
            Where the downloaded dataset is located.

        """

        filename, username = self.formatPath(dataset, username=username)

        URL_download = "https://portal-auth.nersc.gov/als/hdf/rawdata"

        data_paths = self.derived_datasets(filename)

        for i in range(data_paths.__len__()):
            path = data_paths[i]['path']

            if path.find(kind) != -1:
                break

        image_list = self.list_images(filename, username)
        image = image_list[number]

        if downloadPath == 'default':
            downloadPath = "./"

        if downloadName == 'default':
            downloadName = filename

        if downloadPath[-1] != "/":  # add "/" to output path if it is not included
            downloadPath = downloadPath + "/"

        URLstring = URL_download + path

        r = self.session.get(url=URLstring, params={"group": "/" + image})

        fileLocation = downloadPath + downloadName + '.tif'

        location = open(fileLocation, "wb")

        for chunk in r.iter_content(chunk_size=512):
            if chunk:
                location.write(chunk)

        print('download  complete: ' + fileLocation)

        return fileLocation


    """
 GET
URL:
https://portal-auth.nersc.gov/als/hdf/rawdata/[dataset]
Arguments:
group: path in HDF5 file to image
Result:
JSON Array
EXAMPLE:
% curl -k -b cookies.txt -X GET "https://portal-auth.nersc.gov/als/hdf/rawdata/als/bl832/hmwood/20130713_185717_Chilarchaea_quellon_F_9053427_IKI_/norm/20130713_185717_Chilarchaea_quellon_F_9053427_IKI_-norm-20130714_192637.h5?group=/20130713_185717_Chilarchaea_quellon_F_9053427_IKI_/20130713_185717_Chilarchaea_quellon_F_9053427_IKI__0000_0640.tif"
    """

    # =============================================================================
    # Get Download URLs for .tif and .png files for individual image
    # TESTED, works properly.

    def download_URLS(self, dataset, username='default', kind='raw', number=0):
        """Get download URLs for .tif and .png files for individual image.

        Parameters
        ----------
        dataset : str
            The name of an existing dataset on SPOT.
        username: str
            Username associated with dataset.
        kind : str
            Type of data (norm, sino, gridrec, imgrec, etc).
        number : int
            Specific image number in list of images for the dataset.

        Returns
        ------
        JSON Array
            Download URLs as JSON objects.

        """

        filename, username = self.formatPath(dataset, username=username)

        URL_download = "https://portal-auth.nersc.gov/als/hdf/image"

        data_paths = self.derived_datasets(filename)

        for i in range(data_paths.__len__()):
            path = data_paths[i]['path']

            if path.find(kind) != -1:
                break

        image_list = self.list_images(filename, username)
        image = image_list[number]

        URLstring = URL_download + path

        r = self.session.get(url=URLstring, params={"group": "/" + image})

        return r.json()

    """
 GET
URL:
https://portal-auth.nersc.gov/als/hdf/image/[dataset]
Arguments:
group: path in HDF5 file to image
Result:
JSON Array
EXAMPLE:
% curl -k -b cookies.txt -X GET "https://portal-auth.nersc.gov/als/hdf/image/als/bl832/hmwood/20130713_185717_Chilarchaea_quellon_F_9053427_IKI_/norm/20130713_185717_Chilarchaea_quellon_F_9053427_IKI_-norm-20130714_192637.h5?group=/20130713_185717_Chilarchaea_quellon_F_9053427_IKI_/20130713_185717_Chilarchaea_quellon_F_9053427_IKI__0000_0640.tif"
    """

    # =============================================================================
    # Run TomoPy on an existing dataset
    # *** NOT TESTED ***

    def run_TomoPy(self, raw_dataset):
        """Runs TomoPy on an existing dataset.

        Parameters
        ----------
        raw_dataset : str
            The name of an existing dataset on SPOT.

        Returns
        ------
        JSON List
            Indormation of TomoPy execution.


        """

        raw_dataset = raw_dataset.strip('.h5')
        raw_dataset = raw_dataset.strip('/')

        URL_download = "https://portal-auth.nersc.gov/als/hdf/tomopyjob"

        r = self.session.get(url=URL_download, params={"dataset": raw_dataset})

        return r.json()

    """
 GET
URL:
https://portal-auth.nersc.gov/als/hdf/tomopyjob
Arguments:
dataset: raw dataset
Result:
JSON List
EXAMPLE:
% curl -k -b cookies.txt -X GET "https://portal-auth.nersc.gov/als/hdf/tomopyjob?dataset=20130713_185717_Chilarchaea_quellon_F_9053427_IKI_"
    """


# =============================================================================
#

"""
Functions for NERSC
"""


# =============================================================================

def list_from_txt(TextFilePath='../filepath/UnformatedFileList_Test.txt', comment='#'):
    """
    Converts unformatted .txt file with \n separated file names into python list
    """

    if '.py' in TextFilePath:  # if file path is actually a python script, run script instead
        execfile(TextFilePath)
    else:
        textFile = open(TextFilePath, 'r')  # open text file
        data = textFile.readlines()  # read lines of text into list of strings
        fileList = []
        for i in range(len(data)):
            data[i] = data[i].strip(" ")  # remove spaces
            data[i] = data[i].strip("\n")  # remove returns
            if data[i][0] != comment:
                fileList.append(data[i])  # keep lines that are not commented
        return (fileList)


# =============================================================================

def list_h5_files(searchDir):
    """
    Finds all .h5 files in the search directory
    """
    if searchDir[-1] != '/':
        searchDir = searchDir + "/"

    h5_list = glob.glob(searchDir + "*.h5")
    return (h5_list)


# =============================================================================
NERSC_DefaultPath = "/global/project/projectdirs/als/spade/warehouse/als/bl832/"
userDefault = "hsbarnard"


def NERSC_ArchivePath(filename, useraccount=userDefault, archivepath=NERSC_DefaultPath):
    '''
    Generates path to raw tomography projection data in NERSC Archives
    Input list of file names, returns list of NERSC paths
    '''
    # Convert filename to list type if only one file name is given
    if type(filename) != list:
        filename = [filename]

    # Generate list of NERSC Paths from fileList
    pathOut = []
    for i in range(len(filename)):
        # pathOut.append( archivepath +useraccount+ "/" + filename[i] + "/raw/" + filename[i]+".h5" )
        pathOut.append(archivepath + useraccount + "/" + filename[i] + "/raw/")
    print(pathOut)
    return pathOut


# =============================================================================

def NERSC_StageData(filename, username='default'):
    '''
    curl command sent to spot.nersc to stage data if stored on tape
    requires credentials. Run the following command
    > curl -k -c cookies.txt -X POST -d "username=[your_username]&password=[your_password]" https://portal-auth.nersc.gov/als/auth
    for more info: http://spot.nersc.gov/api.php
    '''
    # Prompts user for username and password

    URL_authentication = "https://portal-auth.nersc.gov/als/auth"
    spot_username = input("username:")
    spot_password = getpass.getpass()

    if username == 'default':  # if no additional usermane is given, spot username is stored to be used in file paths
        username = spot_username

    s = requests.Session()
    r = s.post(URL_authentication, {"username": spot_username, "password": spot_password})

    # Convert filename to list type if only one file name is given
    if type(filename) != list:
        filename = [filename]

    baseURL = "https://portal-auth.nersc.gov/als/hdf/stageifneeded/als/bl832/"

    r_list = []
    for i in range(len(filename)):
        r = s.get(baseURL + useraccount + "/" + filename[i] + "/raw/" + filename[i] + ".h5")
        print(command_string)
        r_list.append(r.json())

    return r_list  # return json


# =============================================================================

def NERSC_RetreiveData(filename,
                       username,
                       destinationpath,
                       archivepath=NERSC_DefaultPath):
    '''
    Downloads raw tomography projection data in NERSC from NERSC Archives
    for a list of file names
    '''

    # Convert filename to list type if only one file name is given
    if type(filename) != list:
        filename = [filename]

    # Generate file paths and destination paths
    filePathIn = []
    filePathOut = []
    for i in range(len(filename)):
        print(archivepath, useraccount, filename[i])
        filePathIn.append(archivepath + useraccount + "/" + filename[i] + "/raw/" + filename[i] + ".h5")
        filePathOut.append(destinationpath + filename[i] + ".h5")
    logging.info("file path list complete");
    print(filePathIn)
    logging.info("destination path list complete");
    print(filePathOut)

    # Copy Files to desintation
    for i in range(len(filename)):
        logging.info("begin transfer: " + filePathIn[i])
        os.system("cp " + filePathIn[i] + " " + filePathOut[i])
        logging.info("transfer complete: ")

