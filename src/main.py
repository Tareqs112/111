import os
import sys
# DON"T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# إضافة مسار site-packages للبيئة الافتراضية بشكل صريح
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                    '..', '.venv', 'lib', 'python3.13', 'site-packages'))

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.extensions import db
from src.routes.clients import clients_bp
from src.routes.companies import companies_bp
from src.routes.drivers import drivers_bp
from src.routes.vehicles import vehicles_bp
from src.routes.bookings import bookings_bp
from src.routes.invoices import invoices_bp
from src.routes.notifications import notifications_bp
from src.routes.settings import settings_bp
from src.routes.dashboard import dashboard_bp
from waitress import serve # أضف هذا السطر


app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), "static"))
app.config["SECRET_KEY"] = "tourism_booking_secret_key_2024"

# Enable CORS for all routes
CORS(app)

# Register blueprints
app.register_blueprint(clients_bp, url_prefix="/api")
app.register_blueprint(companies_bp, url_prefix="/api")
app.register_blueprint(drivers_bp, url_prefix="/api")
app.register_blueprint(vehicles_bp, url_prefix="/api")
app.register_blueprint(bookings_bp, url_prefix="/api")
app.register_blueprint(invoices_bp, url_prefix="/api")
app.register_blueprint(notifications_bp, url_prefix="/api")
app.register_blueprint(settings_bp, url_prefix="/api")  # تأكد من تسجيل settings_bp
app.register_blueprint(dashboard_bp, url_prefix="/api")

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path): # تم تغيير اسم الدالة هنا لتجنب التعارض
    if path != "" and os.path.exists(app.static_folder + "/" + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, "index.html")




if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("Database tables created and/or checked.")
    
    port = int(os.environ.get("PORT", 5000)) # الحصول على المنفذ من متغيرات البيئة
    serve(app, host="0.0.0.0", port=port) # استخدام serve من waitress هنا
