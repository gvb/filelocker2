from lib.SQLAlchemyTool import session
import lib.Encryption
__author__="wbdavis"
__date__ ="$Oct 5, 2011 2:09:08 AM$"

class LocalDirectory(object):


    def lookup_user(self, userId):
        return session.query(User).filter(User.id == userid).one()

    def authenticate(self, userId, password):
        #We have to support real-time conversion from less-secure MD5 hashed passwords
        passwordHash = session.query(User.password).filter(User.id == userId).scalar()
        return lib.Encryption.compare_password_hash(password, passwordHash

    def get_user_matches(self, firstName=None, lastName=None, userId=None):
        query = session.query(User)
        if userId is not None:
            query.filter(User.id.like("%"+userid+"%"))
        elif firstName is not None and lastName is not None:
            query.filter(User.first_name.like("%"+firstName+"%"))
            query.filter(User.last_name.like("%"+lastName+"%"))
        elif firstName is None and lastName is not None:
            query.filter(User.first_name.like("%"+lastName+"%"))
            query.filter(User.last_name.like("%"+lastName+"%"))
        elif firstName is not None and lastName is None:
            query.filter(User.first_name.like("%"+firstName+"%"))
        return query.order_by(User.last_name)


