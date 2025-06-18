from flask import Blueprint, request, jsonify, current_app
from src.models.database import db, Settings
import json
import traceback

settings_bp = Blueprint("settings", __name__)

@settings_bp.route("/", methods=["GET"])
def get_settings():
    """Get all settings"""
    try:
        settings = Settings.query.all()
        result = {}
        for setting in settings:
            try:
                result[setting.key] = json.loads(setting.value)
            except json.JSONDecodeError:
                result[setting.key] = setting.value
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@settings_bp.route("/<key>", methods=["GET"])
def get_setting(key):
    """Get specific setting"""
    try:
        setting = Settings.query.filter_by(key=key).first()
        if setting:
            try:
                value = json.loads(setting.value)
            except json.JSONDecodeError:
                value = setting.value
            return jsonify({key: value})
        return jsonify({key: None})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@settings_bp.route("/<key>", methods=["POST"])
def update_setting(key):
    """Update specific setting"""
    try:
        data = request.get_json()
        value = data.get("value")
        
        # Convert value to JSON string if it\"s not already a string
        if isinstance(value, (dict, list)):
            value_str = json.dumps(value)
        else:
            value_str = str(value)
        
        setting = Settings.query.filter_by(key=key).first()
        if setting:
            setting.value = value_str
        else:
            setting = Settings(key=key, value=value_str)
            db.session.add(setting)
        
        db.session.commit()
        return jsonify({"message": f"Setting {key} updated successfully"})
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@settings_bp.route("/meta-whatsapp", methods=["GET"])
def get_meta_whatsapp_settings():
    """Get Meta WhatsApp Business API settings"""
    try:
        setting = Settings.query.filter_by(key="meta_whatsapp_settings").first()
        if setting:
            settings_data = json.loads(setting.value)
            # Don\"t return sensitive data like access_token and app_secret
            safe_settings = {
                "phone_number_id": settings_data.get("phone_number_id", ""),
                "app_id": settings_data.get("app_id", ""),
                "webhook_verify_token": settings_data.get("webhook_verify_token", ""),
                "configured": bool(settings_data.get("access_token") and settings_data.get("phone_number_id"))
            }
            return jsonify(safe_settings)
        return jsonify({
            "phone_number_id": "",
            "app_id": "",
            "webhook_verify_token": "",
            "configured": False
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@settings_bp.route("/meta-whatsapp", methods=["POST"])
def update_meta_whatsapp_settings():
    """Update Meta WhatsApp Business API settings"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ["access_token", "phone_number_id", "app_id", "app_secret"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Field {field} is required"}), 400
        
        # Get existing settings or create new
        setting = Settings.query.filter_by(key="meta_whatsapp_settings").first()
        
        settings_data = {
            "access_token": data["access_token"],
            "phone_number_id": data["phone_number_id"],
            "app_id": data["app_id"],
            "app_secret": data["app_secret"],
            "webhook_verify_token": data.get("webhook_verify_token", ""),
            "api_version": data.get("api_version", "v18.0")
        }
        
        if setting:
            setting.value = json.dumps(settings_data)
        else:
            setting = Settings(key="meta_whatsapp_settings", value=json.dumps(settings_data))
            db.session.add(setting)
        
        db.session.commit()
        return jsonify({"message": "Meta WhatsApp ayarları başarıyla güncellendi"})
        
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@settings_bp.route("/admin-phones", methods=["GET"])
def get_admin_phones():
    """Get admin phone numbers"""
    try:
        setting = Settings.query.filter_by(key="admin_phone_numbers").first()
        if setting:
            phones = json.loads(setting.value)
            return jsonify({"admin_phone_numbers": phones})
        return jsonify({"admin_phone_numbers": []})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@settings_bp.route("/admin-phones", methods=["POST"])
def update_admin_phones():
    """Update admin phone numbers"""
    try:
        data = request.get_json()
        phone_numbers = data.get("phone_numbers", [])
        
        # Clean and validate phone numbers
        clean_phones = []
        for phone in phone_numbers:
            phone = phone.strip()
            if phone:
                # Add + if not present
                if not phone.startswith("+"):
                    phone = "+" + phone
                clean_phones.append(phone)
        
        setting = Settings.query.filter_by(key="admin_phone_numbers").first()
        if setting:
            setting.value = json.dumps(clean_phones)
        else:
            setting = Settings(key=key, value=value_str)
            db.session.add(setting)
        
        db.session.commit()
        return jsonify({"message": "Yönetici telefon numaraları başarıyla güncellendi"})
        
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@settings_bp.route("/email", methods=["GET"])
def get_email_settings():
    """Get email settings"""
    try:
        setting = Settings.query.filter_by(key="email_settings").first()
        if setting:
            email_data = json.loads(setting.value)
            # Don\"t return password for security
            safe_email_data = {
                "smtp_server": email_data.get("smtp_server", ""),
                "smtp_port": email_data.get("smtp_port", "587"),
                "username": email_data.get("username", ""),
                "configured": bool(email_data.get("username") and email_data.get("password"))
            }
            return jsonify(safe_email_data)
        return jsonify({
            "smtp_server": "",
            "smtp_port": "587",
            "username": "",
            "configured": False
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@settings_bp.route("/email", methods=["POST"])
def update_email_settings():
    """Update email settings"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ["smtp_server", "smtp_port", "username", "password"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Field {field} is required"}), 400
        
        setting = Settings.query.filter_by(key="email_settings").first()
        
        email_data = {
            "smtp_server": data["smtp_server"],
            "smtp_port": data["smtp_port"],
            "username": data["username"],
            "password": data["password"]
        }
        
        if setting:
            setting.value = json.dumps(email_data)
        else:
            setting = Settings(key=key, value=value_str)
            db.session.add(setting)
        
        db.session.commit()
        return jsonify({"message": "E-posta ayarları başarıyla güncelllendi"})
        
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@settings_bp.route("/test-meta-whatsapp", methods=["POST"])
def test_meta_whatsapp():
    current_app.logger.debug("Received request to /settings/test-meta-whatsapp")
    """Test Meta WhatsApp Business API connection"""
    try:
        data = request.get_json()
        test_phone = data.get("test_phone")
        
        if not test_phone:
            return jsonify({"error": "Test telefon numarası gerekli"}), 400
        
        # Import the notification function
        from src.routes.notifications import send_whatsapp_notification_meta
        
        test_message = "🧪 Meta WhatsApp Business API Test Mesajı\\n\\nBu bir test mesajıdır. API bağlantısı başarılı!"
        
        success = send_whatsapp_notification_meta(test_phone, test_message)
        
        return jsonify({
            "success": success,
            "message": "Test mesajı başarıyla gönderildi" if success else "Test mesajı gönderilemedi"
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@settings_bp.route("/test-turkish-template", methods=["POST"])
def test_turkish_template():
    """Test Turkish notification template"""
    try:
        data = request.get_json()
        recipient_type = data.get("recipient_type", "admin")  # \"admin\" or \"driver\"
        test_phone = data.get("test_phone")  # Required for driver test
        
        # Import the notification functions
        from src.routes.notifications import send_formatted_admin_notification, send_formatted_driver_notification
        
        # Sample data for testing
        client_name = "Ahmet Yılmaz"
        arrival_time = "14:30"
        date = "2024-01-15"
        tour_name = "İstanbul Tarihi Şehir Turu"
        
        success = False
        
        if recipient_type == "admin":
            success = send_formatted_admin_notification(
                client_name, arrival_time, date, tour_name, "arrival"
            )
        elif recipient_type == "driver":
            if not test_phone:
                return jsonify({"error": "Şoför testi için telefon numarası gerekli"}), 400
            success = send_formatted_driver_notification(
                test_phone, client_name, arrival_time, date, tour_name, "driver_assignment"
            )
        else:
            return jsonify({"error": "Geçersiz alıcı türü"}), 400
        
        return jsonify({
            "success": success,
            "message": "Türkçe şablon test mesajı başarıyla gönderildi" if success else "Test mesajı gönderilemedi"
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@settings_bp.route("/backup", methods=["GET"])
def backup_settings():
    """Backup all settings"""
    try:
        settings = Settings.query.all()
        backup_data = {}
        for setting in settings:
            try:
                backup_data[setting.key] = json.loads(setting.value)
            except json.JSONDecodeError:
                backup_data[setting.key] = setting.value
        
        return jsonify({
            "backup_date": datetime.utcnow().isoformat(),
            "settings": backup_data
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@settings_bp.route("/restore", methods=["POST"])
def restore_settings():
    """Restore settings from backup"""
    try:
        data = request.get_json()
        settings_data = data.get("settings", {})
        
        for key, value in settings_data.items():
            # Convert value to JSON string if it\"s not already a string
            if isinstance(value, (dict, list)):
                value_str = json.dumps(value)
            else:
                value_str = str(value)
            
            setting = Settings.query.filter_by(key=key).first()
            if setting:
                setting.value = value_str
            else:
                setting = Settings(key=key, value=value_str)
                db.session.add(setting)
        
        db.session.commit()
        return jsonify({"message": "Ayarlar başarıyla geri yüklendi"})
        
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500





