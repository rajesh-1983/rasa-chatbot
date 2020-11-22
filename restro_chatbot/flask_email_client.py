import os
from flask import Flask, current_app
from flask_mail import Mail, Message

app = Flask(__name__)
app.config.update(
    DEBUG=True,
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=465,
    MAIL_USE_SSL=True,
    MAIL_USE_TLS=False,
    MAIL_DEBUG=True,
    MAIL_USERNAME=os.environ['EMAIL_USERNAME'],
    MAIL_PASSWORD=os.environ['EMAIL_PASSWORD']
    )
     
     
mail = Mail(app)

class EmailClient:

    def __init__(self):
        pass
    
    #send mail notification
    def send_email(self, recepient, subject, body):
        print("Sending email with subject: {}".format(subject))
        recipients = [recepient]
        with app.app_context():
            print(current_app.name)
            try:
                msg = Message(subject=subject,
                          sender=app.config.get('MAIL_USERNAME'),
                          recipients=recipients,
                          body=body)
                mail.send(msg)
                return True
            except Exception as err:
                print('Exception while sending error: ', err)
                return False
