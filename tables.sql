CREATE TABLE IF NOT EXISTS menu (
id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
name TEXT NOT NULL,
url TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user (
id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
datetime_user_registration TEXT NOT NULL,
status TEXT NOT NULL,
username TEXT NOT NULL,
email TEXT NOT NULL,
hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS streaming (
id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
streaming_datetime TEXT NOT NULL,
streamer_id INTEGER NOT NULL,
name_of_streaming TEXT NOT NULL,
streaming_duration TEXT NOT NULL,
questions_limit TEXT NOT NULL,
FOREIGN KEY (streamer_id) REFERENCES user(id)
);
CREATE TABLE IF NOT EXISTS question (
id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
question_datetime TEXT NOT NULL,
streaming_id INTEGER NOT NULL,
user_id INTEGER NOT NULL,
question TEXT NOT NULL,
answer_datetime TEXT,
comment TEXT,
FOREIGN KEY (streaming_id) REFERENCES streaming(id),
FOREIGN KEY (user_id) REFERENCES user(id)
);
CREATE TABLE IF NOT EXISTS registration_for_chat (
id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
datetime_regist_for_chat TEXT NOT NULL,
streaming_id INTEGER NOT NULL,
streamer_id INTEGER NOT NULL,
viewer_id INTEGER NOT NULL,
viewer_email TEXT NOT NULL,
FOREIGN KEY (streaming_id) REFERENCES streaming(id),
FOREIGN KEY (streamer_id) REFERENCES user(id),
FOREIGN KEY (viewer_id) REFERENCES user(id)
);
CREATE TABLE IF NOT EXISTS ban (
id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
datetime_ban TEXT,
streamer_id INTEGER NOT NULL,
viewer_id INTEGER,
viewer_email TEXT NOT NULL,
FOREIGN KEY (streamer_id) REFERENCES user(id),
FOREIGN KEY (viewer_id) REFERENCES user(id)
);
