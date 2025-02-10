from captcha.image import ImageCaptcha
import random, string
from flask import session

# Global Variables as Part of Application Configuration
# Limiting the maximum number of streamings/chats per streamer
max_numb_of_streamings = 10    
# Streaming name length limitation
length_of_streaming_name = 40
# Limit the maximum number of questions per chat member
max_number_of_questions = 15
# Limiting question length 
length_of_question = 400
# Limiting answer length 
length_of_answer = 400
# Frequency of chat updating
chat_update_frequency = 6000
# number_of_emails_per_user
number_of_emails_per_user = 10

# Captcha for login, registration, account settings.
image_captca = ImageCaptcha(width = 200, height = 70)
filename = './static/'+'CAPTCHA'+'.png'
def make_captcha():
    session["captcha_text"] = str("".join(random.choices(string.ascii_uppercase + string.digits, k=4))).replace('O', 'A').replace('0', 'B')
    image_captca.write(session["captcha_text"], filename)


