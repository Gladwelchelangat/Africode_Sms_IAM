
import os
SECRET_KEY="hgbToJpSEz1DaUxpCSe43tn_jx2sImZP0hLFKT8_kB8"
SECURITY_PASSWORD_SALT='46589359065962411892706150402684366383'
#Database Configuration
#SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:xzOeEwTWNtrKXSpHyLCihtupLjtYicGz@postgres.railway.internal:5432/railway'
# SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:Stuei@localhost:5432/sms'
database_url = os.environ.get('DATABASE_URL', 'postgres://default:9McNmPuGCvh7@ep-damp-lake-a4qheolk-pooler.us-east-1.aws.neon.tech:5432/verceldb?sslmode=require')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

SQLALCHEMY_DATABASE_URI = database_url



SQLALCHEMY_TRACK_MODIFICATIONS=False
SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True}
#Regisration
SECURITY_REGISTERABLE = True
SECURITY_CONFIRMABLE = True
#recover/reset
SECURITY_RECOVERABLE = True
#cookie settings
REMEMBER_COOKIE_SAMESITE='strict'
SESSION_COOKIE_SAMESITE='strict'
#mail settings
MAIL_SERVER='smtp.gmail.com'
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME='chelangatgladwel9@gmail.com'
MAIL_PASSWORD='wthzircujeprqatl'
MAIL_DEFAULT_SENDER=('chelangatgladwel9@gmail.com')
SECURITY_CHANGE_EMAIL=True

