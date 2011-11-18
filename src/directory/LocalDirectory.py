from lib.SQLAlchemyTool import session
import lib.Encryption
from lib.Models import *
import logging
import sqlalchemy
__author__="wbdavis"
__date__ ="$Oct 5, 2011 2:09:08 AM$"

class LocalDirectory(object):

    def lookup_user(self, userId):
        return session.query(User).filter(User.id == userId).one()

    def authenticate(self, userId, password):
        #We have to support real-time conversion from less-secure MD5 hashed passwords
        isValid = False
        try:
            passwordHash = session.query(User.password).filter(User.id == userId).one()
            if password is not None and password != "":
                isValid = lib.Encryption.compare_password_hash(password, passwordHash)
                if isValid and len(passwordHash) == 32:
                    newHash = lib.Encryption.hash_password(password)
                    user = session.query(User).filter(User.id==userId).one()
                    user.password = newHash
                    session.commit() #New has stored in the db
            else:
                isValid = False
        except sqlalchemy.orm.exc.NoResultFound:
            isValid = False
        except Exception, e:
            logging.error("[system] [authenticat] [Problem authenticating user: %s" % str(e))
            isValid = False
        return isValid

    def get_user_matches(self, firstName=None, lastName=None, userId=None):
        query = session.query(User)
        if userId is not None:
            query = query.filter(User.id.like("%s%%"%userId))
        elif firstName is not None and lastName is not None:
            query = query.filter(User.first_name.like("%%%s%%" % firstName)).filter(User.last_name.like("%%%s%%" % lastName))
        elif firstName is None and lastName is not None:
            query = query.filter(or_(User.first_name.like("%%%s%%" % lastName), User.last_name.like("%%%s%%" % lastName)))
        elif firstName is not None and lastName is None:
            query = query.filter(User.first_name.like("%%%s%%" % firstName))
        return query.order_by(User.last_name).all()


