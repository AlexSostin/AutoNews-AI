from auto_news_site.wsgi import *
from django.db import connection
cursor = connection.cursor()
cursor.execute("SELECT '2025 Avatr 11 EREV: The 1,065 km' ~* '\y06\y';")
print("Postgres \y06\y matches 1,065:", cursor.fetchone()[0])
