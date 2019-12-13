from arcgis.gis import *
from datetime import datetime
import os
import traceback

# Logging config
txtFile = open("C:\\Users\\Lucas.Piedrahita\\OneDrive - Wake County\\LP\\JupyterNotebooks\\agol_content_migration\\migrate_user.txt", "w")
txtFile.write("New execution of migrate_user.py started at {0}\n".format(datetime.now().strftime("%m/%d/%Y, %H:%M:%S")))

# Define functions
def createNewUser(gis, olduser, newuser_username):
    """ Create a new user, making sure to use `provider='enterprise'` if Web Tier 
    Authentication is going to be used.  If moving user accounts from one userid 
    to another, make sure that a proper password is used that meets 
    security requirements. 
    This function not complete yet. Need to figure out how to set up 
    account/password for AD auth use. """
    # newuser = gis.users.create(username = newuser_username,
    #                             password = "pwdNotUsed",
    #                             firstname = olduser.firstName,
    #                             lastname = olduser.lastName,
    #                             email = olduser.email,
    #                             description = olduser.description,
    #                             thumbnail = olduser.thumbnail,
    #                             role = olduser.role,
    #                             provider = 'enterprise',
    #                             idp_username=None,
    #                             level = olduser.level)
    # return(newuser)
    pass

def reassignGroups(gis, olduser, newuser):
    """ Reassign group ownership and group membership from the old user to the 
    new user """
    olduser_groups = olduser["groups"]
    olduser_username = olduser.username
    newuser_username = newuser.username
    for group in olduser_groups:
        grp = gis.groups.get(group["id"])
        if (grp.owner == olduser_username):
            try:
                grp.reassign_to(newuser_username)
            except:
                txtFile.write("\t\tUnable to reassign the group, {0}, from {1} to {2}:\n".format(grp.title, olduser_username, newuser_username))
                traceback.print_exc(file=txtFile)
        else:
            try:
                grp.add_users(newuser_username)
                grp.remove_users(olduser_username)
            except:
                txtFile.write("\t\tUnable to add {0} to or remove {1} from the group, {2}\n".format(newuser_username, olduser_username, grp.title))
                traceback.print_exc(file=txtFile)
    # verifyGroupReassignment(gis, olduser_groups, newuser["groups"])

def verifyGroupReassignment(gis, olduser_groups, newuser_groups):
    """ Take the groups object of the old user (before reassignment) and the groups 
    object of the new user (after reassignment) and check that the new user has all 
    of the same permissions to all of the same groups that the old user had.
    Return true if succesffully verified and false if not.
    """
    pass

def reassignItem(item, newuser_username, target_folder=None):
    """ Unshares the item, reassigns ownership to new_user (maintaining folder 
    structure), and reshares the item with groups it was previously shared with. 
    This is necessary for items that are shared with a special group, such as one 
    that allows editing, which blocks the item from being reassigned while shared.
    """
    if item.access == 'private':
        item.reassign_to(newuser_username, target_folder=target_folder)
    else:
        shared_settings = [item.shared_with['everyone'], item.shared_with['org'], item.shared_with['groups']]
        item.unshare(shared_settings[2])
        item.reassign_to(newuser_username, target_folder=target_folder)
        item.share(everyone=shared_settings[0], org=shared_settings[1], groups=shared_settings[2], allow_members_to_edit=True)

def reassignContent(gis, olduser, newuser):
    """ Reassign all the original user's content to the new user. 
    This happens in 2 passes. First, reassign everything on the root folder of 
    'My Contents'. Then, loop over each folder, create the same folder in the new 
    user account, and reassign items in each folder to the new user in the correct 
    folder. """
    newuser_username = newuser.username
    olduser_content = olduser.items()
    olduser_folders = olduser.folders
    txtFile.write("\t\tMoving items in root folder...\n")
    for item in olduser_content:
        try:
            reassignItem(item, newuser_username)
        except Exception as e:
            txtFile.write("\t\tAn error occured trying to reassign the item.\nItem: {0}\nError: {1}\n".format(item, e))
            traceback.print_exc(file=txtFile)

    for folder in olduser_folders:
        txtFile.write("\t\tMoving items in '{0}' folder...\n".format(folder['title']))
        gis.content.create_folder(folder['title'], newuser_username)
        folderitems = olduser.items(folder=folder['title'])
        for item in folderitems:
            try:
                reassignItem(item, newuser_username, target_folder=folder['title'])
            except Exception as e:
                txtFile.write("\t\tAn error occured trying to reassign the item.\nItem: {0}\nError: {1}\n".format(item, e))
                traceback.print_exc(file=txtFile)
                break
        else:
            txtFile.write("\t\t\tItems successfully moved. Now Deleting folder...\n")
            folderEmpty = olduser.items(folder=folder['title']) == []
            if folderEmpty:
                gis.content.delete_folder(folder=folder['title'], owner=olduser.username)
                txtFile.write("\t\t{0}'s '{1}' folder deleted.\n".format(olduser.username, folder['title']))
            else:
                txtFile.write("\t\tFolder not empty.\n")

def migrateUser(gis, olduser_username, newuser_username):
    txtFile.write("Migrating {0} to {1}...\n".format(olduser_username, newuser_username))
    olduser = gis.users.get(olduser_username)
    # newuser = createNewUser(gis, olduser, newuser_username)
    newuser = gis.users.get(newuser_username)
    txtFile.write("\tReassigning groups...\n")
    try:
        reassignGroups(gis, olduser, newuser)
    except Exception as e:
        txtFile.write("\t\tAn error occured trying to reassign groups.\n\t\tError: {0}\n".format(e))
        traceback.print_exc(file=txtFile)
    txtFile.write("\tReassigning content...\n")
    try:
        reassignContent(gis, olduser, newuser)
    except Exception as e:
        txtFile.write("\t\tAn error occured trying to reassign content.\n\t\tError: {0}\n".format(e))
        traceback.print_exc(file=txtFile)


# Connect to AGOL
try:
    gis = GIS("https://waketest.maps.arcgis.com", os.environ.get("AGOL_TEST_USER"), os.environ.get("AGOL_TEST_PASS"))
    if "user" not in gis.properties: # This only occurs if os.environ.get() is None
        gis = GIS("https://waketest.maps.arcgis.com", input("Username: "), input("Password: "))
    txtFile.write("Connected to {0} as {1}\n".format(gis.url, gis.properties["user"]["username"]))
except:
    txtFile.write("An error occurred while connecting to waketest.maps.arcgis.com:\n")
    traceback.print_exc(file=txtFile)

# Migrate user
try:
    olduser_username = "lpiedrahita"
    newuser_username = "benstrausstest"
    # olduser_username, newuser_username = newuser_username, olduser_username
    migrateUser(gis, olduser_username, newuser_username) 
except:
    txtFile.write("\tAn error occurred while migrating {0} to {1}:\n".format(olduser_username, newuser_username))
    traceback.print_exc(file=txtFile)    

txtFile.write("Execution of migrate_user.py completed at {0}\n".format(datetime.now().strftime("%m/%d/%Y, %H:%M:%S")))
txtFile.close()
