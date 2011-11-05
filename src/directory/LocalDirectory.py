from lib.SQLAlchemyTool import session
import lib.Encryption
from lib.Models import *
__author__="wbdavis"
__date__ ="$Oct 5, 2011 2:09:08 AM$"

class LocalDirectory(object):

    def lookup_user(self, userId):
        return session.query(User).filter(User.id == userId).one()

    def authenticate(self, userId, password):
        #We have to support real-time conversion from less-secure MD5 hashed passwords
        passwordHash = session.query(User.password).filter(User.id == userId).scalar()
        print "Retrieved password: %s" % str(passwordHash)
        isValid = lib.Encryption.compare_password_hash(password, passwordHash)
        if isValid and len(passwordHash) == 32:
            newHash = lib.Encryption.hash_password(password)
            user = session.query(User).filter(User.id==userId).one()
            user.password = newHash
            session.commit() #New has stored in the db
        return isValid

    def get_user_matches(self, firstName=None, lastName=None, userId=None):
        query = session.query(User)
        if userId is not None:
            query.filter(User.id.like("%"+userId+"%"))
        elif firstName is not None and lastName is not None:
            query.filter(User.first_name.like("%"+firstName+"%"))
            query.filter(User.last_name.like("%"+lastName+"%"))
        elif firstName is None and lastName is not None:
            query.filter(User.first_name.like("%"+lastName+"%"))
            query.filter(User.last_name.like("%"+lastName+"%"))
        elif firstName is not None and lastName is None:
            query.filter(User.first_name.like("%"+firstName+"%"))
        return query.order_by(User.last_name)


