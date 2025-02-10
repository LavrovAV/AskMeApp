import sqlite3
from datetime import datetime, timezone

class FDataBase:
    def __init__(self, db):
        self.__db = db
        self.__cur = db.cursor()

    def getMenu(self):
        sql = '''SELECT * FROM menu'''
        try:
            self.__cur.execute(sql)
            res = self.__cur.fetchall()
            if res: return res
        except:
            print("Error reading data from database")
        return []

    def addUser(self, status, username, email, hash):
        try:
            email = email.upper().strip()
            self.__cur.execute("SELECT COUNT(*) AS 'count' FROM user WHERE email = ?", (email,))
            res = self.__cur.fetchone()
            if res['count'] > 0:
                return False
            username=username.upper().strip()
            self.__cur.execute("SELECT COUNT(*) AS 'count' FROM user WHERE username = ?", (username,))
            res = self.__cur.fetchone()
            if res['count'] > 0:
                return False
            current_utc_datetime = datetime.now(timezone.utc)
            info_for_insert = (current_utc_datetime, status, username, email, hash)
            self.__cur.execute("INSERT INTO user(datetime_user_registration, status, username, email, hash) VALUES (?, ?, ?, ?, ?);", info_for_insert)
            self.__db.commit()
        except sqlite3.Error as e :
            print("Error adding data to database "+str(e))
            return False
        return True
    
    def deleteViewer(self, viewer_id):
        try:
            query = f"""BEGIN TRANSACTION;\
                        DELETE FROM question WHERE user_id={viewer_id};\
                        DELETE FROM registration_for_chat WHERE viewer_id={viewer_id};\
                        DELETE FROM user WHERE id={viewer_id};\
                        END TRANSACTION;"""
            self.__cur.executescript(query)
            self.__db.commit()
        except sqlite3.Error as e :
            print("Error deleting data from database: "+str(e))
            return False
        return True

    def deleteStreamer(self, streamer_id):
        try:
            query = f"""BEGIN TRANSACTION;\
                        DELETE FROM question WHERE streaming_id IN (SELECT id FROM streaming WHERE streamer_id={streamer_id});\
                        DELETE FROM ban WHERE streamer_id={streamer_id};\
                        DELETE FROM registration_for_chat WHERE streamer_id={streamer_id};\
                        DELETE FROM streaming WHERE streamer_id={streamer_id};\
                        DELETE FROM user WHERE id={streamer_id};\
                        END TRANSACTION;"""
            self.__cur.executescript(query)
            self.__db.commit()
        except sqlite3.Error as e :
            print("Error deleting data from database: "+str(e))
            return False
        return True

    # To make authorization work
    def getUser(self, user_id):
        try:
            self.__cur.execute("SELECT * FROM user WHERE id = ? LIMIT 1", (user_id,))
            res = self.__cur.fetchone()
            if not res:
                return False
            return res
        except sqlite3.Error as e :
            print("Error getting data from database"+str(e))
            return False

        # To make authorization work
    def getUserByEmail(self, email):
        try:
            email = email.upper().strip()
            self.__cur.execute("SELECT * FROM user WHERE email = ? LIMIT 1", (email, ))
            res = self.__cur.fetchone()
            if res: return res
        except sqlite3.Error as e :
            print("Error getting data from database "+str(e))
        return []

    def getUserById(self, id):
        try:
            self.__cur.execute(f"SELECT * FROM user WHERE id = ? LIMIT 1", (id, ))
            res = self.__cur.fetchone()
            if res: return res
        except sqlite3.Error as e :
            print("Error getting data from database "+str(e))
        return []

    def updateUser(self, id, username, email):
        try:
            email = email.upper().strip()
            username=username.upper().strip()
            self.__cur.execute("SELECT COUNT(*) as 'count' FROM user WHERE email = ? AND id != ?", (email, id))
            res = self.__cur.fetchone()
            if res['count'] > 0:
                return False
            self.__cur.execute("SELECT COUNT(*) as 'count' FROM user WHERE username = ? AND id != ?", (username, id))
            res = self.__cur.fetchone()
            if res['count'] > 0:
                return False
            self.__cur.execute("UPDATE user SET username=?, email=? WHERE id=?;", (username, email, id))
            self.__db.commit()
        except sqlite3.Error as e :
            print("Error adding data to database "+str(e))
            return False
        return True

    def updatePassword(self, id, hash):
        try:
            self.__cur.execute("UPDATE user SET hash=? WHERE id=?;", (hash, id))
            self.__db.commit()
        except sqlite3.Error as e :
            print("Error adding data to database "+str(e))
            return False
        return True

    def getMyStreamings(self, streamer_id):
        try:
            self.__cur.execute("SELECT * FROM streaming WHERE streamer_id = ?;", (streamer_id, ))
            res = self.__cur.fetchall()
            if res: return res
        except sqlite3.Error as e :
            print("Error database reading"+str(e))
        return []

    def getListOfRegistered(self, selected_stream, streamer_id):
        try:
            self.__cur.execute("SELECT * FROM registration_for_chat JOIN user ON user.id=registration_for_chat.viewer_id WHERE streaming_id=? AND registration_for_chat.viewer_id NOT IN (SELECT viewer_id FROM ban WHERE streamer_id=?);", (selected_stream, streamer_id))
            res = self.__cur.fetchall()
            if res: return res
        except sqlite3.Error as e :
            print("Error database reading when getListOfRegistered "+str(e))
        return []

    def getChat(self, selected_stream):
        try:
            self.__cur.execute("SELECT question_datetime, username, question, answer_datetime, comment, question.id, name_of_streaming, questions_limit, question.user_id, streaming.id, streaming_datetime FROM  user, question, streaming WHERE user.id=question.user_id AND streaming.id=question.streaming_id AND streaming.id=? ORDER BY question_datetime DESC;", (selected_stream, ))
            res = self.__cur.fetchall()
            if res: return res
        except sqlite3.Error as e :
            print("Error database reading "+str(e))
        return []

    def addComment(self, comment, question_id):
        try:
            self.__cur.execute("UPDATE question SET comment=? WHERE id=?;", (comment, question_id))
            self.__db.commit()
        except sqlite3.Error as e :
            print("Error adding comment to database "+str(e))
            return False
        return True

    def addTimeOfAnswer(self, question_id):
        try:
            current_utc_datetime = datetime.now(timezone.utc)
            self.__cur.execute("UPDATE question SET answer_datetime=? WHERE id=?;", (current_utc_datetime, question_id))
            self.__db.commit()
        except sqlite3.Error as e :
            print("Error adding time of answer to database"+str(e))
            return False
        return current_utc_datetime

    def addStreaming(self, streaming_datetime, streamer_id, name_of_streaming, streaming_duration, questions_limit):
        try:
            name_of_streaming = name_of_streaming.capitalize().strip()
            self.__cur.execute("SELECT COUNT(*) as 'count' FROM streaming WHERE name_of_streaming = ?", (name_of_streaming, ))
            res = self.__cur.fetchone()
            if res['count'] > 0:
                return False
            # Convert a string to a datetime object, convert a local date to a UTC date, convert to a string in the required format.
            # The datetime format is necessary for the correct operation of the jinja filter in the app.py.
            streaming_utc_datetime = datetime.strptime(streaming_datetime, '%Y-%m-%dT%H:%M').astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f%z")
            info_for_insert = (streaming_utc_datetime, streamer_id, name_of_streaming, streaming_duration, questions_limit)
            self.__cur.execute("INSERT INTO streaming(streaming_datetime, streamer_id, name_of_streaming, streaming_duration, questions_limit) VALUES (?, ?, ?, ?, ?);", info_for_insert)
            self.__db.commit()
        except sqlite3.Error as e :
            print("Error adding data to database: "+str(e))
            return False
        return True


    def updateStreaming(self, streaming_datetime, name_of_streaming, streaming_duration, questions_limit, streaming_to_change):
        try:
            name_of_streaming = name_of_streaming.capitalize().strip()
            self.__cur.execute("SELECT COUNT(*) as 'count' FROM streaming WHERE name_of_streaming = ? AND id != ?", (name_of_streaming, streaming_to_change))
            res = self.__cur.fetchone()
            if res['count'] > 0:
                return False
            # Convert a string to a datetime object, convert a local date to a UTC date, convert to a string in the required format.
            # The datetime format is necessary for the correct operation of the jinja filter in the app.py.
            streaming_utc_datetime = datetime.strptime(streaming_datetime, "%Y-%m-%dT%H:%M").astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f%z")
            info_for_update = (streaming_utc_datetime, name_of_streaming, streaming_duration, questions_limit, streaming_to_change)
            self.__cur.execute("UPDATE streaming SET streaming_datetime=?, name_of_streaming=?, streaming_duration=?, questions_limit=? WHERE id=?;", info_for_update)
            self.__db.commit()
        except sqlite3.Error as e :
            print("Database update error: "+str(e))
            return False
        return True


    def deleteStreaming(self, streaming_to_delete):
        try:
            query = f"""BEGIN TRANSACTION;\
                        DELETE FROM question WHERE streaming_id={streaming_to_delete};\
                        DELETE FROM registration_for_chat WHERE streaming_id={streaming_to_delete};\
                        DELETE FROM streaming WHERE id={streaming_to_delete};\
                        END TRANSACTION;"""
            self.__cur.executescript(query)
            self.__db.commit()
        except sqlite3.Error as e :
            print("Error deleting data from database "+str(e))
            return False
        return True

    def getAllStreamings(self):
        try:
            self.__cur.execute("SELECT * FROM streaming JOIN user ON streaming.streamer_id = user.id;")
            res = self.__cur.fetchall()
            if res: return res
        except sqlite3.Error as e :
            print("Error database reading "+str(e))
        return []

    def registrationForChat(self, selected_streaming_id, streamer_id, viewer_id, viewer_email):
        try:
            self.__cur.execute("SELECT COUNT(*) as 'count' FROM registration_for_chat WHERE streaming_id=? AND (viewer_id=? OR viewer_email=?)", (selected_streaming_id, viewer_id, viewer_email))
            res = self.__cur.fetchone()
            if res['count'] > 0:
                return False
            self.__cur.execute("SELECT COUNT(*) as 'count' FROM ban WHERE streamer_id=? AND (viewer_id=? OR viewer_email=?)", (streamer_id, viewer_id, viewer_email))
            res = self.__cur.fetchone()
            if res['count'] > 0:
                return False
            current_utc_datetime = datetime.now(timezone.utc)
            info_for_insert = (current_utc_datetime, selected_streaming_id, streamer_id, viewer_id, viewer_email)
            self.__cur.execute("INSERT INTO registration_for_chat (datetime_regist_for_chat, streaming_id, streamer_id, viewer_id, viewer_email) VALUES (?, ?, ?, ?, ?);", info_for_insert)
            self.__db.commit()
        except sqlite3.Error as e :
            print("Error adding data to database"+str(e))
            return False
        return True
    

    def getStreamWhereRegist(self, viewer_id):
        try:
            self.__cur.execute("SELECT * FROM streaming, registration_for_chat WHERE registration_for_chat.streaming_id=streaming.id AND registration_for_chat.viewer_id = ?;", (viewer_id, ))
            res = self.__cur.fetchall()
            if res: return res
        except sqlite3.Error as e :
            print("Error database reading "+str(e))
        return []


    def delRegistForChat(self, streaming_id_to_del_regist, viewer_id):
        try:
            query = f"""BEGIN TRANSACTION;\
                        DELETE FROM question WHERE streaming_id={streaming_id_to_del_regist} AND user_id={viewer_id};\
                        DELETE FROM registration_for_chat WHERE streaming_id={streaming_id_to_del_regist} AND viewer_id={viewer_id};\
                        END TRANSACTION;"""
            self.__cur.executescript(query)
            self.__db.commit()
        except sqlite3.Error as e :
            print("Error deleting data from database: "+str(e))
            return False
        return True
    

    def addQuestion(self, id_selected_stream, viewer_id, question, streamer_id, viewer_email):
        try:
            self.__cur.execute("SELECT COUNT(*) as 'count' FROM ban WHERE streamer_id=? AND (viewer_id=? OR viewer_email=?)", (streamer_id, viewer_id, viewer_email))
            res = self.__cur.fetchone()
            if res['count'] > 0:
                return False
            current_utc_datetime = datetime.now(timezone.utc)
            self.__cur.execute("INSERT INTO question (question_datetime, streaming_id, user_id, question) VALUES (?, ?, ?, ?);", (current_utc_datetime, id_selected_stream, viewer_id, question))
            self.__db.commit()
        except sqlite3.Error as e :
            print("Error adding question to database "+str(e))
            return False
        return True

    def updateQuestion(self, question_id, changed_question):
        try:
            self.__cur.execute("UPDATE question SET question=? WHERE id=?;", (changed_question, question_id))
            self.__db.commit()
        except sqlite3.Error as e :
            print("Error adding data to database"+str(e))
            return False
        return True

    def getNoAnswerOrComment(self, question_id):
        try:
            self.__cur.execute("SELECT COUNT (*) as 'count' FROM question WHERE answer_datetime IS NULL AND comment IS NULL AND id=?;", (question_id, ))
            res = self.__cur.fetchone()
            if int(res['count']) == 1:
                return True
        except sqlite3.Error as e :
            print("Error getting information from database "+str(e))
            return False
        return False

    def getMyQuestions(self, user_id):
        try:
            self.__cur.execute("SELECT * FROM question, streaming WHERE question.streaming_id=streaming.id AND question.user_id = ? ORDER BY question_datetime DESC;", (user_id, ))
            res = self.__cur.fetchall()
            if res: return res
        except sqlite3.Error as e :
            print("Error getting questions from database "+str(e))
        return []

    def getNumberOfQuestions(self, user_id, id_selected_stream):
        try:
            self.__cur.execute("SELECT COUNT(*) as 'count' FROM question WHERE streaming_id=? AND user_id = ?;", (id_selected_stream, user_id))
            res = self.__cur.fetchone()
            if res: return int(res['count'])
        except sqlite3.Error as e :
            print("Error getting number of questions from database"+str(e))
        return []

    def getQuestionsLimit(self, id_selected_stream):
        try:
            self.__cur.execute("SELECT questions_limit FROM streaming WHERE id=?;", (id_selected_stream, ))
            res = self.__cur.fetchone()
            if res: return int(res["questions_limit"])
        except sqlite3.Error as e :
            print("Error database reading"+str(e))
        return []

    def addBan(self, streamer_id, viewer_id, viewer_email):
        try:
            current_utc_datetime = datetime.now(timezone.utc)
            self.__cur.execute("INSERT INTO ban (datetime_ban, streamer_id, viewer_id, viewer_email) VALUES (?, ?, ?, ?);", (current_utc_datetime, streamer_id, viewer_id, viewer_email))
            self.__db.commit()
        except sqlite3.Error as e :
            print("Error adding users to database (to the list of blocked users) "+str(e))
            return False
        return True

    def getBlockedUsers(self, streamer_id):
        try:
            self.__cur.execute("SELECT ban.viewer_id, user.username, ban.streamer_id, ban.viewer_email FROM ban JOIN user ON user.id=ban.viewer_id WHERE ban.streamer_id = ?", (streamer_id,))
            res = self.__cur.fetchall()
            if res: return res
        except sqlite3.Error as e :
            print("Error getting data (list of blocked users) from database "+str(e))
        return []

    def deleteBan(self, streamer_id, viewer_id):
        try:
            self.__cur.execute("DELETE FROM ban WHERE streamer_id=? AND viewer_id=?;", (streamer_id, viewer_id))
            self.__db.commit()
        except sqlite3.Error as e :
            print("Error deleting user from database (from the list of blocked users) "+str(e))
            return False
        return True

    def getStreamerIdByStreamingId(self, streaming_id):
        try:
            self.__cur.execute("SELECT streamer_id FROM streaming WHERE id = ?;", (streaming_id, ))
            res = self.__cur.fetchone()
            if res: return int(res["streamer_id"])
        except sqlite3.Error as e :
            print("Error database reading "+str(e))
        return []

    def updateStreamingDatetime(self, id):
        try:
            current_utc_datetime = datetime.now(timezone.utc)
            self.__cur.execute("UPDATE streaming SET streaming_datetime=? WHERE id=?;", (current_utc_datetime, id))
            self.__db.commit()
        except sqlite3.Error as e :
            print("Error adding data to database "+str(e))
            return False
        return True

    def getEmail(self, user_id):
        try:
            self.__cur.execute("SELECT email FROM user WHERE id = ? LIMIT 1", (user_id,))
            res = self.__cur.fetchone()
            if not res:
                return False
            return res["email"]
        except sqlite3.Error as e :
            print("Error getting data from database"+str(e))
            return False

    def checkUserByEmail(self, email):
        email = email.upper().strip()
        try:
            self.__cur.execute("SELECT COUNT(*) as 'count' FROM user WHERE email = ?", (email,))
            res = self.__cur.fetchone()
            if res['count'] > 0:
                return True
            return False
        except sqlite3.Error as e :
            print("Error getting number of users by email from database"+str(e))
            return False