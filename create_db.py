import os
from flask import Flask
from src.models.database import db

app = Flask(__name__)
# Ensure the database file is created in the same location as main.py expects it
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

with app.app_context():
    db.create_all()
    print("Database tables created successfully.")


