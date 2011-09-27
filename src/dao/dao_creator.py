# -*- coding: utf-8 -*-
from MySQLDAO import MySQLDAO
def get_dao(dbType, dbHost, dbUser, dbPassword, dbName):
    if str(dbType) == "mysql":
        return MySQLDAO(dbHost, dbUser, dbPassword, dbName)
    else:
        return None