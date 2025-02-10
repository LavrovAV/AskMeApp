from flask import Flask, redirect, render_template, request, session, g, url_for, flash, get_flashed_messages, jsonify, make_response, current_app, json
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, fresh_login_required
from UserLogin import UserLogin
from FDataBase import FDataBase
import sqlite3, os, random, string
from datetime import datetime, timezone, timedelta
from flask_mail import Mail, Message
from helpers import make_captcha, max_numb_of_streamings, length_of_streaming_name, max_number_of_questions, length_of_question, length_of_answer, chat_update_frequency, number_of_emails_per_user
from config import MAIL_PASSWORD, SECRET_KEY, MAIL_USERNAME
import hashlib

app = Flask(__name__)
app.config.from_object(__name__)                                           
app.config.update(dict(DATABASE=os.path.join(app.root_path, 'database.db')))                
app.permanent_session_lifetime = timedelta(days=1, weeks=0, hours=0, minutes=0)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 587                                               
app.config['MAIL_USE_TLS'] = True                                            
app.config['MAIL_USERNAME'] = MAIL_USERNAME                       
app.config['MAIL_DEFAULT_SENDER'] = MAIL_USERNAME                 
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD                        

mail = Mail(app)

# connection to DB
def connect_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

# function to save connection to DB in global variable inside query
def get_db():
    if not hasattr(g, 'link_db'):
        g.link_db = connect_db()
    return g.link_db

# dbase is necessary to make a global variable, so we declare it outside the function
dbase = None

# Connecting to the database via a request interception decorator, triggered immediately before executing the request
@app.before_request
def before_request():
    global dbase
    db = get_db()
    dbase = FDataBase(db)

# Breaking the connection to the database via the request interception decorator, triggered when the application context is broken (at the end of request processing)
@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'link_db'):
        g.link_db.close()

# Initialization of the database and creation of tables if the database is missing. Below is a call to this function.
def create_tables():
    with app.app_context():
        db = connect_db()
        with app.open_resource('tables.sql', mode = 'r') as f:
            db.cursor().executescript(f.read())
            db.commit()
            db.close()

create_tables()

login_manager = LoginManager(app)    

# Message and redirect to /login if not authorized.        
login_manager.login_view = "login"              
login_manager.login_message = "Please log in to access this page"   
login_manager.login_message_category = "error"

#This method from login_manager is used to reload the user object from the user ID (user_id) stored in the session.
@login_manager.user_loader  
def load_user(user_id):     
    return UserLogin().fromDB(user_id, dbase)

@login_manager.needs_refresh_handler
def refresh():
    logout_user()
    flash("To protect your account, please reauthenticate to access this page.", "success")
    return redirect(url_for("login"))


# Jinja filter to convert date and time from database for templates. The filter converts to JS format
@app.template_filter('utc_db_time_to_local_js_format')
def utc_db_time_to_local_js_format(utc_str):
    if ("time_zone" in session) and ("time_zone_offset" in session) and utc_str:
        loc_str = datetime.strptime(utc_str, "%Y-%m-%d %H:%M:%S.%f%z").astimezone(timezone(timedelta(hours=session["time_zone_offset"]/60))).strftime("%Y-%m-%dT%H:%M:%S")
        return loc_str

# Jinja filter to convert date and time from database for templates. The filter converts UTC time to local time in the required format.
@app.template_filter('utc_time_to_local')
def utc_time_to_local(utc_str):
    if ("time_zone" in session) and ("time_zone_offset" in session) and utc_str:
        time_zone = session["time_zone"]
        loc_str = datetime.strptime(utc_str, "%Y-%m-%d %H:%M:%S.%f%z").astimezone(timezone(timedelta(hours=session["time_zone_offset"]/60))).strftime("%d-%m-%Y %H:%M")
        return loc_str + ", " + time_zone

# Jinja filter for editing streaming form
@app.template_filter('db_time_to_dispay_in_form')
def db_time_to_dispay_in_form(utc_str):
    if ("time_zone" in session) and ("time_zone_offset" in session) and utc_str:
        loc_str = datetime.strptime(utc_str, "%Y-%m-%d %H:%M:%S.%f%z").astimezone(timezone(timedelta(hours=session["time_zone_offset"]/60))).strftime("%Y-%m-%dT%H:%M")
        return str(loc_str)

# Jinja filter to calculate the difference between answer time and streaming start time.
@app.template_filter('timedelta_for_answer')
def timedelta_for_answer(str_streaming_datetime, str_answer_datetime):
    obj_streaming_datetime = datetime.strptime(str_streaming_datetime, "%Y-%m-%d %H:%M:%S.%f%z") # Time from the database (from HTML) is transformed into an object and brought to a unified standard for this app
    obj_answer_datetime = datetime.strptime(str_answer_datetime, "%Y-%m-%d %H:%M:%S.%f%z")
    obj_timedelta_since_start = obj_answer_datetime - obj_streaming_datetime # Arithmetic operations can be performed on datetime objects.
    sec = int(obj_timedelta_since_start.total_seconds())  # Express the resulting object in seconds and convert the type to int (milliseconds are cut off)
    if sec < 0:           # to exclude output of negative values
        return "answer before streaming starts"
    return str(timedelta(seconds=sec)) # Сonvert the seconds back to an object and then to a string, so we can output the time without milliseconds

# Saving information about the time zone on the client side to the session. Processing the request from layout.html
@app.route("/time_zone_info", methods=["POST"])
def time_zone_info():
    if request.json['timeZone'] and request.json['timeZoneOffset']:
        session["time_zone"] = request.json['timeZone']
        session["time_zone_offset"] = int(request.json['timeZoneOffset'])
        res = make_response(jsonify(message = "the server received timezone information"), 200)
        res.headers['Content-Type'] = "application/json; charset=utf-8"
        return res
    else:
        res = make_response(jsonify(message = "Error on the client side, the server did not receive timezone information."), 400)
        res.headers['Content-Type'] = "application/json; charset=utf-8"
        return res

# Below are two functions for monitoring chats in real time.
@app.route("/streamer_check_chat", methods=["POST"])
def streamer_check_chat():
    try:
        my_chat = dbase.getChat(int(request.json['selected_stream']))
        if len(my_chat) != int(request.json['number_of_questions']):
            return "", 200
        else:
            return "", 204
    except:
        res = make_response(jsonify(message = "Problem on the server side"), 500)
        res.headers['Content-Type'] = "application/json; charset=utf-8"
        return res

@app.route("/viewer_check_chat")
def viewer_check_chat():
    try:
        my_questions = dbase.getMyQuestions(current_user.get_id())
        current_status_of_answers = []
        # Сreate a data structure completely similar to the structure that is saved in the session["status_of_answers"]
        for row in my_questions:
            row_data = {
                row.keys()[0] : str(row[0]), 
                row.keys()[5] : str(row['answer_datetime']),
                row.keys()[6] : row['comment']
                }
            current_status_of_answers.append(row_data)
        if current_status_of_answers != session["status_of_answers"]:
            res = make_response(jsonify(current_status_of_answers), 200)
            res.headers['Content-Type'] = "application/json; charset=utf-8"
            session["status_of_answers"] = current_status_of_answers
            return res      
        else:
            return "", 204
    except:
        return "", 500

# Email verification for registration, account settings, recovery password
@app.route("/send_email", methods=["POST"])
def send_email():
    if  request.json['data']:
        # Protection limited mail box
        result = dbase.checkUserByEmail(request.json['data'])
        # If the request came from the login or account settings pages, then the email should be in the database
        # but if it came from the registration page, then the email could not be in the database
        if result or ("/registration" in str(request.referrer)):
            session["entered_email"] = request.json['data'].upper().strip()
            session["verification_code"] = str("".join(random.choices(string.ascii_uppercase + string.digits, k=5))).replace('O', 'A').replace('0', 'B')
            try:
                if ("email_counter" in session) and (session["email_counter"] >= number_of_emails_per_user):
                    res = make_response(jsonify(message = "TOO_MANY_REQUESTS, The limit for sending email by one user has been exceeded, please try again later"), 429)
                    res.headers['Content-Type'] = "application/json; charset=utf-8"
                    return res
                else:
                    msg = Message("Verification code", recipients=[session["entered_email"]])
                    msg.html = f'<h1 style="color: red">{session["verification_code"]}</h1><h2> is your AskMeApp verification code.</h2>'
                    mail.send(msg)   # как я понял, если мы находимся в запросе, то создавать контекст вручную не нужно - with app.app_context():
            except:
                res = make_response(jsonify(message = "SERVICE_UNAVAILABLE"), 503)
                res.headers['Content-Type'] = "application/json; charset=utf-8"
                return res
            if "email_counter" in session:
                session["email_counter"] = session.get("email_counter") + 1
            else:
                session["email_counter"] = 1
            res = make_response(jsonify(message = "Confrmation code has been sent"), 200)
            res.headers['Content-Type'] = "application/json; charset=utf-8"
            return res
        else:
            res = make_response(jsonify(message = "NOT_FOUND, Please enter the email address you used when registering"), 404) 
            res.headers['Content-Type'] = "application/json; charset=utf-8" 
            return res
    else:
        res = make_response(jsonify(message = "BAD_REQUEST. You didn`t enter any e-mail."), 400) 
        res.headers['Content-Type'] = "application/json; charset=utf-8" 
        return res

@app.errorhandler(404)
def pageNotFount(error):
    return render_template('page404.html', title="Page not found", menu = dbase.getMenu())

@app.errorhandler(500)
def InternalServerError(error):
    flash("Internal Server Error.", "error")
    return redirect(url_for("index"))

@app.route("/", methods=["GET", "POST"])
def index():
    if current_user.is_authenticated :
        try:
            if current_user.get_status() == 'streamer':
                return redirect(url_for("streamer_profile"))
            elif current_user.get_status() == 'viewer':
                return redirect(url_for("viewer_profile"))
        except:
            return redirect(url_for("logout"))
    return render_template("index.html", menu = dbase.getMenu())


@app.route("/registration", methods=["GET", "POST"])
def registration():
    if current_user.is_authenticated:
        flash("For registration please log out.", "error")
        return redirect(url_for("index"))
    if request.method == "POST":
        if request.form.get("captcha").upper().strip() == str(session["captcha_text"]):
            if len(request.form.get("username")) >= 3 and len(request.form.get("username")) <= 30 \
                and len(request.form.get("password")) >= 5 and len(request.form.get("password")) <= 20 \
                and request.form.get("password") == request.form.get("confirmation") \
                and request.form.get("email").upper().strip() == session["entered_email"]  \
                and request.form.get("verification_code").upper().strip() == session["verification_code"]:
                hash = generate_password_hash(request.form.get("password"))
                # The .addUser() method is defined in the FDataBase class. The dbase variable is global and holds an instance of the FDataBase class, which is responsible for interacting with the database.
                res = dbase.addUser(request.form.get("status"), request.form.get("username"), request.form.get("email"), hash)
                if res:
                    flash("successful registration", "success")
                    return redirect(url_for("login"))
                else:
                    flash("Error when adding to database. A user with the same e-mail or username already exists", "error")
            else:
                flash("The form is filled out incorrectly.", "error")
        else:
            flash("You made a mistake when entering text from the image.", "error")
    make_captcha()
    return render_template("registration.html", menu = dbase.getMenu(), number_of_emails_per_user=number_of_emails_per_user)
    

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        flash("If you want to change user please log out.", "error")
        return redirect(url_for("index"))
    if request.method == "POST":
        if request.form.get("captcha").upper().strip() == str(session["captcha_text"]):
            if request.form.get("password") and request.form.get("email"):
                user = dbase.getUserByEmail(request.form.get("email"))
                if user and check_password_hash(user["hash"], request.form.get("password")):
                    userlogin = UserLogin().create(user)
                    rm = True if request.form.get('remain_me') else False
                    login_user(userlogin, remember=rm)
                    session["time_zone"] = request.form.get("time_zone")
                    session["time_zone_offset"] = int(request.form.get("time_zone_offset"))
                    return redirect(request.args.get("next") or url_for("index"))
                else:
                    flash("invalid e-mail or password.", "error")
            elif request.form.get("new_password") and request.form.get("verification_code"):
                if len(request.form.get("new_password")) >= 5 and len(request.form.get("new_password")) <= 20 \
                        and request.form.get("new_password") == request.form.get("confirmation") \
                        and request.form.get("verification_code").upper().strip() == session["verification_code"]:
                    email = request.form.get("email")
                    hash = generate_password_hash(request.form.get("new_password"))
                    user = dbase.getUserByEmail(email)
                    res = dbase.updatePassword(user["id"], hash)
                    if res:
                        flash("Password changed", "success")
                    else:
                        flash("Error when adding to database", "error")
                else:
                    flash("Please check new password, confirmation and verification code.", "error")
            else:
                flash("Please check all fields must be filled in.", "error")
        else:
            flash("You made a mistake when entering text from the image.", "error")
    make_captcha()
    return render_template("login.html", menu = dbase.getMenu(), current_user = current_user, number_of_emails_per_user=number_of_emails_per_user)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You were logged out of your account", "success")
    return redirect(url_for("index"))


@app.route("/account_settings", methods=["GET", "POST"])
@fresh_login_required
def account_settings():
    if request.method == "POST":
        if request.form.get("captcha").upper().strip() == str(session["captcha_text"]):
            user = dbase.getUserById(current_user.get_id())
            if request.form.get("new_password") and request.form.get("password"):
                if len(request.form.get("new_password")) >= 5 and len(request.form.get("new_password")) <= 20 \
                    and request.form.get("new_password") == request.form.get("confirmation"):
                    if check_password_hash(user["hash"], request.form.get("password")):
                        hash = generate_password_hash(request.form.get("new_password"))
                        res = dbase.updatePassword(current_user.get_id(), hash)
                        if res:
                            flash("Password changed", "success")
                        else:
                            flash("Error when adding to database", "error")
                    else:
                        flash("Invalid current password", "error")
                else:
                    flash("The new password or confirmation is incorrect", "error")
            elif request.form.get("change_account") and request.form.get("username") and request.form.get("verification_code") and request.form.get("email"):
                if len(request.form.get("username")) >= 3 and len(request.form.get("username")) <= 30 \
                    and request.form.get("email").upper().strip() == session["entered_email"]  \
                    and request.form.get("verification_code").upper().strip() == session["verification_code"]:
                    if check_password_hash(user["hash"], request.form.get("password")):
                        res = dbase.updateUser(current_user.get_id(), request.form.get("username"), request.form.get("email"))
                        if res:
                            flash("Account changed", "success")
                        else:
                            flash("Error when adding to database", "error")
                    else:
                        flash("invalid password", "error")
                else:
                    flash("Username or email are filled in incorrectly.", "error")
            elif request.form.get("delete_account") and request.form.get("password"):
                if check_password_hash(user["hash"], request.form.get("password")):
                    try:
                        if current_user.get_status() == 'streamer':
                            res = dbase.deleteStreamer(current_user.get_id())
                            if res:
                                flash("Account deleted.", "success")
                                return redirect(url_for("logout"))
                            else:
                                flash("Error when deleting from database", "error")
                        elif current_user.get_status() == 'viewer':
                            res = dbase.deleteViewer(current_user.get_id())
                            if res:
                                flash("Account deleted.", "success")
                                return redirect(url_for("logout"))
                            else:
                                flash("Error when deleting from database", "error")
                    except:
                        flash("Error when deleting from database", "error")
                else:
                    flash("invalid password", "error")
        else:
            flash("You made a mistake when entering text from the image.", "error")
    make_captcha()
    return render_template("account_settings.html", menu = dbase.getMenu(), current_user = current_user, number_of_emails_per_user=number_of_emails_per_user)


@app.route("/streamer_profile", methods=["GET", "POST"])
@login_required
def streamer_profile():
    if current_user.get_status() != 'streamer':
        return redirect(url_for("index"))
    if ("time_zone" not in session) or ("time_zone_offset" not in session):
        flash("Session has ended, you need to login.", "error")
        return redirect(url_for("logout"))
    user_id =  current_user.get_id()
    if request.method == "POST":
        global length_of_answer
        global chat_update_frequency
        selected_stream = int(request.form.get("selected_stream"))
        if selected_stream:
            if request.form.get("comment"):
                comment = request.form.get("comment")[:length_of_answer]
                comment = comment.replace("\b", "")
                res=dbase.addComment(comment, request.form.get("question_id"))
                if res:
                    flash("Your comment has been saved successfully", "success")
                else:
                    flash("Error when adding your comment to database", "error")
            elif request.form.get("time_of_answer"):
                res=dbase.addTimeOfAnswer(request.form.get("question_id"))
                if res:
                    flash("Time of your answer has been saved successfully", "success")
                else:
                    flash("Error when adding time of your answer to database", "error")
            elif request.form.get("viewer_id_for_ban"):
                list_blocked_users = dbase.getBlockedUsers(user_id)
                viewer_email =dbase.getEmail(request.form.get("viewer_id_for_ban"))
                if viewer_email :
                    res=dbase.addBan(user_id, request.form.get("viewer_id_for_ban"), viewer_email)
                    if res:
                        flash("You have successfully blocked a chat member.", "success")
                    else:
                        flash("Error when adding a chat participant to the list of blocked participants.", "error")
                else:
                        flash("Error when adding a chat participant to the list of blocked participants.", "error")
            elif request.form.get("user_id_for_unblock"):
                res=dbase.deleteBan(user_id, request.form.get("user_id_for_unblock"))
                if res:
                    flash("You have successfully unblocked the chat member.", "success")
                else:
                    flash("Error when removing the chat participant from the list of blocked participants.", "error")
            elif request.form.get("streaming_datetime"):
                res=dbase.updateStreamingDatetime(request.form.get("selected_stream"))
                if res:
                    flash("You have successfully changed the start time of streaming.", "success")
                else:
                    flash("Error when updating the start time of streaming in the database.", "error")
            return render_template("streamer_profile.html", 
                                    menu = dbase.getMenu(), 
                                    current_user = current_user, 
                                    my_streamings = dbase.getMyStreamings(user_id), 
                                    selected_stream= selected_stream,
                                    list_of_registered=dbase.getListOfRegistered(selected_stream, user_id),
                                    my_chat = dbase.getChat(selected_stream),
                                    list_blocked_users = dbase.getBlockedUsers(user_id),
                                    length_of_answer = length_of_answer,
                                    chat_update_frequency = chat_update_frequency
                                    )
        else:
            flash("You didn't select streaming", "error")

    return render_template("streamer_profile.html", 
                            menu = dbase.getMenu(), 
                            current_user = current_user, 
                            my_streamings = dbase.getMyStreamings(user_id),
                            )


@app.route("/add_streaming", methods=["GET", "POST"])
@login_required
def add_streaming():
    if current_user.get_status() != 'streamer':
        return redirect(url_for("index"))
    if ("time_zone" not in session) or ("time_zone_offset" not in session):
        flash("Session has ended, you need to login.", "error")
        return redirect(url_for("logout"))
    user_id =  current_user.get_id()
    my_streamings = dbase.getMyStreamings(user_id)
    global length_of_streaming_name                 
    global max_numb_of_streamings
    global max_number_of_questions
    numb_of_streamings = len(my_streamings)
    if request.method == "POST":
        name_of_streaming = request.form.get("name_of_streaming")[:length_of_streaming_name]
        questions_limit = int(request.form.get("questions_limit"))
        if questions_limit > max_number_of_questions : questions_limit = max_number_of_questions
        if questions_limit < 1 : questions_limit = 1
        if numb_of_streamings < max_numb_of_streamings:
            res = dbase.addStreaming(request.form.get("streaming_datetime"), user_id, name_of_streaming, request.form.get("streaming_duration"), questions_limit)
            if res:
                flash("your streaming information successfuy saved", "success")
                return redirect(url_for("add_streaming"))
            else:
                flash("Error adding to the database, try changing the name of the streaming.", "error")
        else:
            flash(f"You have already created {numb_of_streamings} chats. To add a new chat, you need to delete one of the old ones. You are redirected to the streaming/chat management page.", "error")
            return redirect(url_for("add_streaming"))
        
    return render_template("add_streaming.html", 
                            menu = dbase.getMenu(), 
                            current_user = current_user, 
                            numb_of_streamings = numb_of_streamings,
                            my_streamings = my_streamings,
                            length_of_streaming_name = length_of_streaming_name,
                            max_number_of_questions = max_number_of_questions,
                            max_numb_of_streamings=max_numb_of_streamings,
                            time_zone = session["time_zone"]
                            )


@app.route("/change_streaming", methods=["GET", "POST"])
@login_required
def change_streaming():
    if current_user.get_status() != 'streamer':
        return redirect(url_for("index"))
    if ("time_zone" not in session) or ("time_zone_offset" not in session):
        flash("Session has ended, you need to login.", "error")
        return redirect(url_for("logout"))
    user_id =  current_user.get_id()
    if request.method == "POST":
        selected_stream = int(request.form.get("selected_stream"))
        if selected_stream :
            global length_of_streaming_name                            
            global max_number_of_questions
            if request.form.get("streaming_to_change"):
                name_of_streaming = request.form.get("name_of_streaming")[:length_of_streaming_name]
                questions_limit = int(request.form.get("questions_limit"))
                if questions_limit > max_number_of_questions : questions_limit = max_number_of_questions
                res = dbase.updateStreaming(request.form.get("streaming_datetime"), name_of_streaming, request.form.get("streaming_duration"), questions_limit, request.form.get("streaming_to_change") )
                if res:
                    flash("Your streaming information successfuy updated.", "success")
                else:
                    flash("Error when updating the database", "error")
            elif request.form.get("streaming_to_delete"):
                res = dbase.deleteStreaming(request.form.get("streaming_to_delete"))
                if res:
                    flash("Your streaming deleted.", "success")
                    return redirect(url_for("streamer_profile"))
                else:
                    flash("Error when updating the database", "error")
            return render_template("change_streaming.html", 
                                    menu = dbase.getMenu(), 
                                    current_user = current_user, 
                                    my_streamings = dbase.getMyStreamings(user_id),
                                    selected_stream=selected_stream,
                                    length_of_streaming_name = length_of_streaming_name,
                                    max_number_of_questions = max_number_of_questions,
                                    time_zone = session["time_zone"]
                                    )
        else:
            flash("You didn't select streaming", "error")

    return render_template("change_streaming.html", 
                            menu = dbase.getMenu(), 
                            current_user = current_user, 
                            my_streamings = dbase.getMyStreamings(user_id)
                            )


@app.route("/viewer_profile", methods=["GET", "POST"])
@login_required
def viewer_profile():
    if current_user.get_status() != 'viewer':
        return redirect(url_for("index"))
    if ("time_zone" not in session) or ("time_zone_offset" not in session):
        flash("Session has ended, you need to login.", "error")
        return redirect(url_for("logout"))
    user_id =  current_user.get_id()
    viewer_email = current_user.get_email().upper().strip()
    global chat_update_frequency
    global length_of_question
    if request.method == "POST":
        if request.form.get("selected_streaming_id"):
            streamer_id = dbase.getStreamerIdByStreamingId(request.form.get("selected_streaming_id"))
            res = dbase.registrationForChat(request.form.get("selected_streaming_id"), streamer_id, user_id, viewer_email)
            if res:
                flash("You registered for the chat.", "success")
            else:
                flash("Error when adding to database. You may have previously registered in this chat, or the streamer has blocked your registration.", "error")
        if request.form.get("streaming_id_to_del_regist"):
            res = dbase.delRegistForChat(request.form.get("streaming_id_to_del_regist"), user_id)
            if res:
                flash("You left the chat.", "success")
            else:
                flash("Error when updating the database", "error")
        if request.form.get("question"):
            questions_number = dbase.getNumberOfQuestions(user_id, request.form.get("id_selected_stream"))
            limit_questions = dbase.getQuestionsLimit(request.form.get("id_selected_stream"))
            streamer_id = dbase.getStreamerIdByStreamingId(request.form.get("id_selected_stream"))
            # Limit the length of a question for a viewer
            question = request.form.get("question")[:length_of_question]
            question = question.replace("\b", "")
            if questions_number < limit_questions:
                res = dbase.addQuestion(request.form.get("id_selected_stream"), user_id, question, streamer_id, viewer_email)
                if res:
                    flash("You sent a question to the streamer.", "success")
                else:
                    flash("Error when adding to database. It's possible the streamer has blocked your registration.", "error")
            else:
                flash(f"You have exceeded the question limit for this streaming. The streamer set a limit of {limit_questions} questions.", "error")
        if request.form.get("change_question"):
            changed_question = request.form.get("change_question")[:length_of_question]
            changed_question = changed_question.replace("\b", "")
            res = dbase.getNoAnswerOrComment(request.form.get("question_id"))
            if res:
                res = dbase.updateQuestion(request.form.get("question_id"), changed_question)
                if res:
                    flash("You changed the question.", "success")
                else:
                    flash("Error when adding new question to database.", "error")
            else:
                flash("The streamer has already answered your question, changing the question is prohibited.", "error")
        return redirect(url_for("viewer_profile"))
    
    my_questions  = dbase.getMyQuestions(user_id)
    if my_questions:
        session["status_of_answers"] = []
        for row in my_questions:
            row_data = {
                row.keys()[0] : str(row[0]), 
                row.keys()[5] : str(row['answer_datetime']),
                row.keys()[6] : row['comment']
                }
            session["status_of_answers"].append(row_data)
    return render_template("viewer_profile.html",
                            menu = dbase.getMenu(),
                            current_user = current_user,
                            all_streamings = dbase.getAllStreamings(),
                            streamings_where_registered = dbase.getStreamWhereRegist(user_id),
                            my_questions  = my_questions,
                            chat_update_frequency = chat_update_frequency,
                            length_of_question = length_of_question
                            )

# Condition for running the application locally
if __name__ == "__main__":  
    app.run(debug=False)    

