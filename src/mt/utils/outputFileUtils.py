"""
Created on Sep 29, 2016

@author: nikolas
"""
import os


def generate_dictionary_IfNotExists(directory):
    """Checks if the tree structure is in-place. If not creates the requested directory

    Args:
        directory (string): directory path
    """
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
        except:
            print("Path already exists (probably another thread generated it)")


def check_if_path_exists(fileName):
    """Checks if the requested path exists

    Args:
        fileName (string): path to check

    Returns:
        boolean: True if filename exists otherwise False
    """
    return os.path.exists(fileName)


def generateEmptyFileIfNotExists(fileName):
    if check_if_path_exists(fileName) == False:
        basedir = os.path.dirname(fileName)
        if not os.path.exists(basedir):
            os.makedirs(basedir)
        with open(fileName, "a"):
            os.utime(fileName, None)


def getFileID(lineDetails, filePath):
    """
    This method receives as input a filePath and a newLine
    Then it checks each line of the file and if the line is contained
    it returns the rowID of the line
    Otherwise it appends the lineDetails at the end of the file
    and returns the id of the new line
    
    Args:
        lineDetails(string): line to be appended
        fileName (string): path of the file to be updated

    Returns:
        int: The row identifier, equivalent with the total number of rows in the file.
    
    """
    lineDetails = lineDetails + "\n"
    rowID = 0
    with open(filePath) as fp:
        for line in fp:
            if line == lineDetails:
                return rowID
            if line != "":
                rowID += 1
    with open(filePath, "a") as file:
        file.write(lineDetails)
    return rowID


def getDataFileID(config, dirName):
    """Returns the file identifier equivalent to the maximum row number of the file.

    Args:
        config (_type_): _description_
        dirName (_type_): path to drirectory of indexes

    Returns:
        int: the file identifier.
    """
    generateEmptyFileIfNotExists(dirName + "/_indexes.txt")
    lineDetails = str(config)
    dataFileID = getFileID(lineDetails, dirName + "/_indexes.txt")
    return dataFileID
