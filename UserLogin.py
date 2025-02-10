class UserLogin():

    def fromDB(self, user_id, db):
        self.__user = db.getUser(user_id)
        return self  

    def create(self, user):    
        self.__user = user
        return self          

    def is_authenticated(self):
        return True
    
    def is_active(self):
        return True
    
    def is_anonymus(self):
        return False
    
    def get_id(self):
        return str(self.__user['id'])
    
    def get_username(self):
        return str(self.__user['username'])
    
    def get_status(self):
        return str(self.__user['status'])
    
    def get_email(self):
        return str(self.__user['email'])
