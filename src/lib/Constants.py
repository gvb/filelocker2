
__author__="wbdavis"
__date__ ="$Jan 23, 2012 11:49:31 PM$"

class Actions:
    
    LOGIN = "Login"
    UPDATE_USER = "Update User"
    DELETE_USER = "Delete User"
    CREATE_USER = "Create User"

    CREATE_ROLE = "Create Role"
    UPDATE_ROLE = "Update Role"
    DELETE_ROLE = "Delete Role"

    CREATE_GROUP = "Create Group"
    UPDATE_GROUP = "Update Group"
    DELETE_GROUP = "Delete Group"

    CREATE_USER_SHARE = "Create User Share"
    DELETE_USER_SHARE = "Delete User Share"

    CREATE_GROUP_SHARE = "Create Group Share"
    DELETE_GROUP_SHARE = "Delete Group Share"

    CREATE_PUBLIC_SHARE = "Create Public Share"
    DELETE_PUBLIC_SHARE = "Delete Public Share"

    CREATE_UPLOAD_REQUEST = "Create Upload Request"
    DELETE_UPLOAD_REQUEST = "Delete Upload Request"

    DELETE_MESSAGE = "Delete Message"

    SEND_EMAIL = "Send Email"
    DELETE_FILE = "Delete File"
    DOWNLOAD = "Download File"
    UPLOAD = "Check In File"
    UPLOAD_REQUEST_FULFILLED = "Upload Requested File"

    ACTION_LIST = [LOGIN, UPDATE_USER,DELETE_USER,CREATE_USER,CREATE_ROLE,UPDATE_ROLE,DELETE_ROLE,
                    CREATE_GROUP,UPDATE_GROUP,DELETE_GROUP,CREATE_USER_SHARE,DELETE_USER_SHARE,
                    CREATE_GROUP_SHARE,DELETE_GROUP_SHARE,CREATE_PUBLIC_SHARE,DELETE_PUBLIC_SHARE,
                    CREATE_UPLOAD_REQUEST,DELETE_UPLOAD_REQUEST,DELETE_MESSAGE,SEND_EMAIL,DELETE_FILE,
                    DOWNLOAD,UPLOAD,UPLOAD_REQUEST_FULFILLED]