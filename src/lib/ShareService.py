from lib.SQLAlchemyTool import session
from lib.Formatters import *
from lib.Models import *
__author__="wbdavis"
__date__ ="$Jan 31, 2012 3:56:45 AM$"

def get_files_shared_with_user(user):
    sharedFiles = []
    attachedUser = session.query(User).filter(User.id == user.id).one()
    hiddenFileIds = []
    hiddenShares = session.query(HiddenShare).filter(HiddenShare.owner_id == user.id).all()
    for hiddenShare in hiddenShares:
        hiddenFileIds.append(hiddenShare.file_id)
    for share in attachedUser.user_shares:
        if (share.flFile.id not in hiddenFileIds):
            sharedFiles.append(share.flFile)
    for group in attachedUser.groups:
        for share in group.group_shares:
            if (share.flFile.id not in hiddenFileIds):
                sharedFiles.append(share.flFile)
    return sharedFiles

def get_files_shared_with_user_by_attribute(user):
    """Builds a dictionary keyed by attribute id with values that are lists of files shared by this attribute"""
    attributeShareDictionary = {}
    for attributeId in user.attributes:
        attribute = session.query(Attribute).filter(Attribute.id==attributeId).scalar() #Do this to ensure this attribute is even recognized by the system
        if attribute is not None:
            for attributeShare in session.query(AttributeShare).filter(AttributeShare.attribute_id==attribute.id).all():
                if attributeShareDictionary.has_key(attributeShare.attribute_id)==False:
                    attributeShareDictionary[attributeShare.attribute_id] = []
                attributeShareDictionary[attributeShare.attribute_id].append(attributeShare.flFile)
    return attributeShareDictionary