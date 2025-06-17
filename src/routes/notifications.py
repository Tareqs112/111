from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.models.database import db, Notification, Booking, Driver, Service, Company, Client, Settings
import json
import traceback
import requests
import hashlib
import hmac

notifications_bp = Blueprint("notifications", __name__)

def get_email_settings():
    """Get email settings from database"""
    try:
        email_settings = Settings.query.filter_by(key="email_settings").first()
        if email_settings:
            return json.loads(email_settings.value)
        return None
    except:
        return None

def get_admin_phone_numbers():
    """Get admin phone numbers from database settings"""
    try:
        admin_settings = Settings.query.filter_by(key="admin_phone_numbers").first()
        if admin_settings:
            return json.loads(admin_settings.value)
        return []
    except:
        return []

def get_meta_whatsapp_settings():
    """Get Meta WhatsApp Business API settings from database"""
    try:
        meta_settings = Settings.query.filter_by(key="meta_whatsapp_settings").first()
        if meta_settings:
            return json.loads(meta_settings.value)
        return None
    except Exception as e:
        print(f"Error getting Meta WhatsApp settings: {str(e)}")
        return None

def format_turkish_notification_template(client_name, arrival_time, date, tour_name, notification_type="arrival"):
    """
    Türkçe bildirim şablonunu formatla
    
    Args:
        client_name (str): Müşteri adı
        arrival_time (str): Varış saati
        date (str): Tarih
        tour_name (str): Tur adı
        notification_type (str): Bildirim türü (arrival, reminder, etc.)
    
    Returns:
        str: Formatlanmış mesaj
    """
    
    if notification_type == "arrival":
        template = f"""🔔 Yeni Müşteri Varış Bildirimi

👤 Müşteri Adı: {client_name}
🕐 Varış Saati: {arrival_time}
📅 Tarih: {date}
🎯 Tur Adı: {tour_name}

Lütfen müşteriyi belirlenen zamanda karşılamaya hazır olun.

---
Tur Yönetim Sistemi"""
    
    elif notification_type == "reminder_24h":
        template = f"""⏰ Hatırlatma: 24 Saat İçinde Müşteri Geliyor

👤 Müşteri Adı: {client_name}
🕐 Beklenen Varış Saati: {arrival_time}
📅 Tarih: {date}
🎯 Tur Adı: {tour_name}

Lütfen tüm hazırlıkların tamamlandığından emin olun.

---
Tur Yönetim Sistemi"""
    
    elif notification_type == "reminder_1h":
        template = f"""🚨 Acil Uyarı: Müşteri 1 Saat İçinde Geliyor

👤 Müşteri Adı: {client_name}
🕐 Varış Saati: {arrival_time}
📅 Tarih: {date}
🎯 Tur Adı: {tour_name}

Lütfen hemen karşılama noktasına gidin.

---
Tur Yönetim Sistemi"""
    
    elif notification_type == "driver_assignment":
        template = f"""🚗 Yeni Tur Ataması

👤 Müşteri Adı: {client_name}
🕐 Başlangıç Saati: {arrival_time}
📅 Tarih: {date}
🎯 Tur Adı: {tour_name}

Lütfen tur detaylarını inceleyin ve belirlenen zamana hazır olun.

---
Tur Yönetim Sistemi"""
    
    else:
        # Varsayılan şablon
        template = f"""📋 Tur Yönetim Sistemi Bildirimi

👤 Müşteri: {client_name}
🕐 Saat: {arrival_time}
📅 Tarih: {date}
🎯 Tur: {tour_name}

---
Tur Yönetim Sistemi"""
    
    return template

def send_email_notification(recipient_email, subject, message):
    """Send email notification to recipient"""
    try:
        email_settings = get_email_settings()
        if not email_settings:
            print("Email settings not configured")
            return False
        
        # Create message
        msg = MIMEMultipart()
        msg["From"] = email_settings.get("username")
        msg["To"] = recipient_email
        msg["Subject"] = subject
        
        msg.attach(MIMEText(message, "plain", "utf-8"))
        
        # Send email
        server = smtplib.SMTP(email_settings.get("smtp_server"), int(email_settings.get("smtp_port", 587)))
        server.starttls()
        server.login(email_settings.get("username"), email_settings.get("password"))
        text = msg.as_string()
        server.sendmail(email_settings.get("username"), recipient_email, text)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Email sending failed: {str(e)}")
        traceback.print_exc()
        return False

def send_whatsapp_notification_meta(phone_number, message):
    """Send WhatsApp notification using Meta WhatsApp Business API"""
    try:
        # Get Meta WhatsApp settings
        meta_settings = get_meta_whatsapp_settings()
        if not meta_settings:
            print("Meta WhatsApp settings not configured")
            return False
        
        # Check if required settings are available
        access_token = meta_settings.get("access_token")
        phone_number_id = meta_settings.get("phone_number_id")
        
        if not access_token or not phone_number_id:
            print("Incomplete Meta WhatsApp settings")
            return False
        
        # Format phone number (remove + if present)
        if phone_number.startswith("+"):
            phone_number = phone_number[1:]
        
        # Prepare the API request
        url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {
                "body": message
            }
        }
        
        # Send the message
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            response_data = response.json()
            print(f"WhatsApp message sent successfully: {response_data}")
            return True
        else:
            print(f"Failed to send WhatsApp message: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"WhatsApp sending failed: {str(e)}")
        traceback.print_exc()
        return False

def send_admin_notification(message):
    """Send notification to admin phone numbers"""
    admin_numbers = get_admin_phone_numbers()
    if not admin_numbers:
        print("Admin phone numbers not configured.")
        return False
    
    success_count = 0
    for phone_number in admin_numbers:
        if send_whatsapp_notification_meta(phone_number, message):
            success_count += 1
    return success_count > 0

def send_formatted_admin_notification(client_name, arrival_time, date, tour_name, notification_type="arrival"):
    """Send formatted notification to admin"""
    message = format_turkish_notification_template(client_name, arrival_time, date, tour_name, notification_type)
    return send_admin_notification(message)

def send_formatted_driver_notification(driver_phone, client_name, arrival_time, date, tour_name, notification_type="driver_assignment"):
    """Send formatted notification to driver"""
    message = format_turkish_notification_template(client_name, arrival_time, date, tour_name, notification_type)
    return send_whatsapp_notification_meta(driver_phone, message)

def verify_webhook_signature(payload, signature, app_secret):
    """Verify webhook signature from Meta"""
    try:
        expected_signature = hmac.new(
            app_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"sha256={expected_signature}", signature)
    except Exception as e:
        print(f"Webhook signature verification failed: {str(e)}")
        return False

@notifications_bp.route("/notifications/send", methods=["POST"])
def send_notification():
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get("driverId") or not data.get("bookingId") or not data.get("message"):
            return jsonify({"error": "Driver ID, booking ID, and message are required"}), 400
        
        # Validate method
        method = data.get("method", "email")
        if method not in ["email", "whatsapp"]:
            return jsonify({"error": "Invalid notification method"}), 400
        
        # Get driver and booking
        driver = Driver.query.get(data["driverId"])
        if not driver:
            return jsonify({"error": "Driver not found"}), 400
        
        booking = Booking.query.get(data["bookingId"])
        if not booking:
            return jsonify({"error": "Booking not found"}), 400
        
        # Create notification record
        notification = Notification(
            driver_id=data["driverId"],
            booking_id=data["bookingId"],
            message=data["message"],
            notification_type=method,
            sent_at=datetime.utcnow(),
            is_sent=False
        )
        
        # Send notification
        success = False
        if method == "email":
            if driver.email:
                subject = f"Rezervasyon Hatırlatması - Servis Bildirimi"
                success = send_email_notification(driver.email, subject, data["message"])
            else:
                return jsonify({"error": "Driver email not available"}), 400
        elif method == "whatsapp":
            if driver.phone:
                success = send_whatsapp_notification_meta(driver.phone, data["message"])
            else:
                return jsonify({"error": "Driver phone not available"}), 400
        
        notification.is_sent = success
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({
            "id": notification.id,
            "driverId": notification.driver_id,
            "bookingId": notification.booking_id,
            "message": notification.message,
            "method": notification.notification_type,
            "sentStatus": notification.is_sent,
            "sendTime": notification.sent_at.isoformat()
        }), 201
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@notifications_bp.route("/notifications/send-formatted", methods=["POST"])
def send_formatted_notification():
    """Send formatted notification with Turkish template"""
    try:
        data = request.get_json()
        
        # Check required fields
        required_fields = ["client_name", "arrival_time", "date", "tour_name", "recipient_type"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Field {field} is required"}), 400
        
        client_name = data["client_name"]
        arrival_time = data["arrival_time"]
        date = data["date"]
        tour_name = data["tour_name"]
        recipient_type = data["recipient_type"]  # "admin" or "driver"
        notification_type = data.get("notification_type", "arrival")
        
        success = False
        
        if recipient_type == "admin":
            success = send_formatted_admin_notification(
                client_name, arrival_time, date, tour_name, notification_type
            )
        elif recipient_type == "driver":
            driver_phone = data.get("driver_phone")
            if not driver_phone:
                return jsonify({"error": "Driver phone is required for driver notifications"}), 400
            success = send_formatted_driver_notification(
                driver_phone, client_name, arrival_time, date, tour_name, notification_type
            )
        else:
            return jsonify({"error": "Invalid recipient_type. Must be 'admin' or 'driver'"}), 400
        
        # Save notification record to database
        message = format_turkish_notification_template(client_name, arrival_time, date, tour_name, notification_type)
        notification = Notification(
            driver_id=data.get("driver_id"),
            booking_id=data.get("booking_id"),
            message=message,
            notification_type="whatsapp",
            sent_at=datetime.utcnow(),
            is_sent=success
        )
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({
            "success": success,
            "message": "Bildirim başarıyla gönderildi" if success else "Bildirim gönderimi başarısız",
            "notification_id": notification.id,
            "formatted_message": message
        }), 200 if success else 500
        
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@notifications_bp.route("/notifications/webhook", methods=["GET", "POST"])
def webhook():
    """Handle Meta WhatsApp webhook"""
    try:
        if request.method == "GET":
            # Webhook verification
            verify_token = request.args.get("hub.verify_token")
            challenge = request.args.get("hub.challenge")
            
            # Get webhook verify token from settings
            meta_settings = get_meta_whatsapp_settings()
            if not meta_settings:
                return "Webhook verify token not configured", 403
            
            expected_verify_token = meta_settings.get("webhook_verify_token")
            if verify_token == expected_verify_token:
                return challenge
            else:
                return "Invalid verify token", 403
        
        elif request.method == "POST":
            # Handle incoming webhook
            payload = request.get_data()
            signature = request.headers.get("X-Hub-Signature-256")
            
            # Verify signature
            meta_settings = get_meta_whatsapp_settings()
            if meta_settings and meta_settings.get("app_secret"):
                if not verify_webhook_signature(payload, signature, meta_settings["app_secret"]):
                    return "Invalid signature", 403
            
            # Process webhook data
            data = request.get_json()
            print(f"Received webhook: {json.dumps(data, indent=2)}")
            
            # Handle different webhook events
            if "entry" in data:
                for entry in data["entry"]:
                    if "changes" in entry:
                        for change in entry["changes"]:
                            if change.get("field") == "messages":
                                # Handle message events
                                value = change.get("value", {})
                                if "messages" in value:
                                    for message in value["messages"]:
                                        print(f"Received message: {message}")
                                        # Process incoming message here
                                
                                if "statuses" in value:
                                    for status in value["statuses"]:
                                        print(f"Message status update: {status}")
                                        # Process message status updates here
            
            return "OK", 200
    
    except Exception as e:
        print(f"Webhook error: {str(e)}")
        traceback.print_exc()
        return "Internal server error", 500

@notifications_bp.route("/notifications/driver/<int:driver_id>", methods=["GET"])
def get_driver_notifications(driver_id):
    try:
        notifications = Notification.query.filter_by(driver_id=driver_id).order_by(Notification.sent_at.desc()).all()
        result = []
        for notification in notifications:
            result.append({
                "id": notification.id,
                "driverId": notification.driver_id,
                "bookingId": notification.booking_id,
                "message": notification.message,
                "method": notification.notification_type,
                "sentStatus": notification.is_sent,
                "sendTime": notification.sent_at.isoformat()
            })
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@notifications_bp.route("/notifications/company/<int:company_id>", methods=["POST"])
def send_company_notification(company_id):
    """Send notification to company about upcoming bookings"""
    try:
        data = request.get_json()
        hours_ahead = data.get("hours_ahead", 24)  # Default to 24 hours ahead
        
        # Get company
        company = Company.query.get_or_404(company_id)
        
        # Calculate the target date/time
        target_datetime = datetime.now() + timedelta(hours=hours_ahead)
        target_date = target_datetime.date()
        
        # Find all services starting on the target date for clients associated with this company
        upcoming_services = db.session.query(Service).join(Booking).join(Client).filter(
            Client.company_id == company_id,
            Service.startDate == target_date,
            Booking.status.in_(["pending", "confirmed"])
        ).all()
        
        if not upcoming_services:
            return jsonify({"message": "Bu şirket için belirtilen dönemde yaklaşan hizmet bulunamadı"}), 200
        
        # Group services by type
        hotels = []
        tours = []
        vehicle_rentals = []
        
        for service in upcoming_services:
            service_info = {
                "serviceName": service.serviceName,
                "clientName": f"{service.booking_ref.client_ref.firstName} {service.booking_ref.client_ref.lastName}",
                "startDate": service.startDate.isoformat(),
                "endDate": service.endDate.isoformat(),
                "sellingPrice": float(service.totalSellingPrice)
            }
            
            if service.serviceType == "Hotel":
                service_info.update({
                    "hotelName": service.hotelName,
                    "numNights": service.numNights
                })
                hotels.append(service_info)
            elif service.serviceType == "Tour":
                # Add tour timing information for notifications
                if service.startTime:
                    service_info["startTime"] = service.startTime.strftime("%H:%M")
                if service.endTime:
                    service_info["endTime"] = service.endTime.strftime("%H:%M")
                tours.append(service_info)
            elif service.serviceType == "Vehicle":
                service_info.update({
                    "with_driver": service.with_driver,
                    "hours": service.hours if service.is_hourly else None
                })
                vehicle_rentals.append(service_info)
        
        # Create notification message in Turkish
        message = f"📋 {company.name} Şirketi İçin Yaklaşan Hizmetler Bildirimi\n\n"
        message += f"{target_date.strftime('%Y-%m-%d')} tarihinde planlanan hizmetler:\n\n"
        
        if hotels:
            message += "🏨 Oteller:\n"
            for hotel in hotels:
                message += f"- {hotel['hotelName']} müşteri {hotel['clientName']} için ({hotel['numNights']} gece) - ${hotel['sellingPrice']:.2f}\n"
            message += "\n"
        
        if tours:
            message += "🎯 Turlar:\n"
            for tour in tours:
                time_info = ""
                if tour.get("startTime") and tour.get("endTime"):
                    time_info = f" ({tour['startTime']} - {tour['endTime']})"
                elif tour.get("startTime"):
                    time_info = f" (başlangıç {tour['startTime']})"
                message += f"- {tour['serviceName']} müşteri {tour['clientName']} için{time_info} - ${tour['sellingPrice']:.2f}\n"
            message += "\n"
        
        if vehicle_rentals:
            message += "🚗 Araç Kiralama:\n"
            for rental in vehicle_rentals:
                driver_info = " şoförlü" if rental["with_driver"] else " şoförsüz"
                hours_info = f" ({rental['hours']} saat)" if rental.get("hours") else ""
                message += f"- {rental['serviceName']} müşteri {rental['clientName']} için{driver_info}{hours_info} - ${rental['sellingPrice']:.2f}\n"
            message += "\n"
        
        total_amount = sum(service.totalSellingPrice for service in upcoming_services)
        message += f"💰 Toplam Gelir: ${total_amount:.2f}"
        
        # Send email to company
        subject = f"Yaklaşan Hizmetler - {target_date.strftime('%Y-%m-%d')}"
        success = send_email_notification(company.email, subject, message)
        
        return jsonify({
            "message": "Şirket bildirimi başarıyla gönderildi" if success else "Şirket bildirimi gönderilemedi",
            "success": success,
            "servicesCount": len(upcoming_services),
            "totalRevenue": float(total_amount)
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@notifications_bp.route("/notifications/schedule", methods=["POST"])
def schedule_notifications():
    """Schedule automatic notifications for upcoming bookings with Turkish templates"""
    try:
        notifications_sent = 0
        
        # --- Admin Notifications (24-hour and 1-hour before client arrival) ---
        now = datetime.now()
        
        # 24-hour reminder for admin about client arrival
        twenty_four_hours_later = now + timedelta(hours=24)
        services_24h_admin = db.session.query(Service).join(Booking).join(Client).filter(
            Service.startDate == twenty_four_hours_later.date(),
            Booking.status.in_(["pending", "confirmed"])
        ).all()
        
        for service in services_24h_admin:
            client_name = f"{service.booking_ref.client_ref.firstName} {service.booking_ref.client_ref.lastName}"
            arrival_time = service.startTime.strftime("%H:%M") if service.startTime else "Belirtilmemiş"
            date = service.startDate.strftime("%Y-%m-%d")
            tour_name = service.serviceName
            
            if send_formatted_admin_notification(client_name, arrival_time, date, tour_name, "reminder_24h"):
                notifications_sent += 1

        # 1-hour reminder for admin about client arrival (especially for tours)
        one_hour_later = now + timedelta(hours=1)
        services_1h_admin = []
        for service in db.session.query(Service).join(Booking).join(Client).filter(
            Service.startDate == one_hour_later.date(),
            Booking.status.in_(["pending", "confirmed"])
        ).all():
            # For tours, check specific start time
            if service.serviceType == "Tour" and service.startTime:
                service_datetime = datetime.combine(service.startDate, service.startTime)
                time_diff = service_datetime - now
                if timedelta(minutes=50) <= time_diff <= timedelta(hours=1, minutes=10):
                    services_1h_admin.append(service)

        for service in services_1h_admin:
            client_name = f"{service.booking_ref.client_ref.firstName} {service.booking_ref.client_ref.lastName}"
            arrival_time = service.startTime.strftime("%H:%M") if service.startTime else "Belirtilmemiş"
            date = service.startDate.strftime("%Y-%m-%d")
            tour_name = service.serviceName
            
            if send_formatted_admin_notification(client_name, arrival_time, date, tour_name, "reminder_1h"):
                notifications_sent += 1

        # --- Driver Notifications (Existing Logic with new templates) ---
        # Get services that need 24-hour reminders
        tomorrow = datetime.now().date() + timedelta(days=1)
        services_24h_driver = db.session.query(Service).join(Booking).filter(
            Service.startDate == tomorrow,
            Booking.status.in_(["pending", "confirmed"]),
            Service.driver_id.isnot(None) # Only notify drivers if assigned
        ).all()
        
        for service in services_24h_driver:
            driver = Driver.query.get(service.driver_id)
            if driver and driver.phone:
                client_name = f"{service.booking_ref.client_ref.firstName} {service.booking_ref.client_ref.lastName}"
                arrival_time = service.startTime.strftime("%H:%M") if service.startTime else "Belirtilmemiş"
                date = service.startDate.strftime("%Y-%m-%d")
                tour_name = service.serviceName
                
                if send_formatted_driver_notification(driver.phone, client_name, arrival_time, date, tour_name, "reminder_24h"):
                    notifications_sent += 1

        # Get services that need 1-hour reminders
        one_hour_later = now + timedelta(hours=1)
        services_1h_driver = []
        for service in db.session.query(Service).join(Booking).filter(
            Service.startDate == one_hour_later.date(),
            Booking.status.in_(["pending", "confirmed"]),
            Service.driver_id.isnot(None)
        ).all():
            if service.startTime:
                service_datetime = datetime.combine(service.startDate, service.startTime)
                time_diff = service_datetime - now
                if timedelta(minutes=50) <= time_diff <= timedelta(hours=1, minutes=10):
                    services_1h_driver.append(service)

        for service in services_1h_driver:
            driver = Driver.query.get(service.driver_id)
            if driver and driver.phone:
                client_name = f"{service.booking_ref.client_ref.firstName} {service.booking_ref.client_ref.lastName}"
                arrival_time = service.startTime.strftime("%H:%M") if service.startTime else "Belirtilmemiş"
                date = service.startDate.strftime("%Y-%m-%d")
                tour_name = service.serviceName
                
                if send_formatted_driver_notification(driver.phone, client_name, arrival_time, date, tour_name, "reminder_1h"):
                    notifications_sent += 1

        return jsonify({
            "message": f"{notifications_sent} bildirim başarıyla gönderildi",
            "notifications_sent": notifications_sent
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@notifications_bp.route("/notifications/test", methods=["POST"])
def test_notifications():
    """Test notification system"""
    try:
        data = request.get_json()
        test_type = data.get("type", "admin")
        
        if test_type == "admin":
            # Test admin notification with sample data
            success = send_formatted_admin_notification(
                client_name="Ahmet Mehmet",
                arrival_time="14:30",
                date="2024-01-15",
                tour_name="Tarihi Şehir Turu",
                notification_type="arrival"
            )
            
            return jsonify({
                "success": success,
                "message": "Yönetim için test mesajı gönderildi" if success else "Test mesajı gönderilemedi"
            })
        
        elif test_type == "driver":
            phone_number = data.get("phone_number")
            if not phone_number:
                return jsonify({"error": "Şoför testi için telefon numarası gerekli"}), 400
            
            success = send_formatted_driver_notification(
                driver_phone=phone_number,
                client_name="Ayşe Fatma",
                arrival_time="10:00",
                date="2024-01-15",
                tour_name="Sahil Turu",
                notification_type="driver_assignment"
            )
            
            return jsonify({
                "success": success,
                "message": "Şoför için test mesajı gönderildi" if success else "Test mesajı gönderilemedi"
            })
        
        else:
            return jsonify({"error": "Geçersiz test türü. 'admin' veya 'driver' kullanın"}), 400
            
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@notifications_bp.route("/notifications/admin-settings", methods=["GET"])
def get_admin_settings():
    """Get admin notification settings"""
    try:
        admin_phone_numbers = get_admin_phone_numbers()
        meta_settings = get_meta_whatsapp_settings()
        email_settings = get_email_settings()
        
        return jsonify({
            "admin_phone_numbers": admin_phone_numbers,
            "meta_whatsapp_configured": bool(meta_settings and 
                                           meta_settings.get("access_token") and 
                                           meta_settings.get("phone_number_id")),
            "email_configured": bool(email_settings and 
                                   email_settings.get("username") and 
                                   email_settings.get("password")),
            "meta_whatsapp_settings": {
                "phone_number_id": meta_settings.get("phone_number_id", "") if meta_settings else "",
                "app_id": meta_settings.get("app_id", "") if meta_settings else "",
                # Access token ve app secret güvenlik nedeniyle gönderilmez
            } if meta_settings else {}
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@notifications_bp.route("/notifications/admin-settings", methods=["POST"])
def update_admin_settings():
    """Update admin notification settings"""
    try:
        data = request.get_json()
        
        # Update admin phone numbers
        if "admin_phone_numbers" in data:
            admin_phones = [phone.strip() for phone in data["admin_phone_numbers"] if phone.strip()]
            existing_setting = Settings.query.filter_by(key="admin_phone_numbers").first()
            
            if existing_setting:
                existing_setting.value = json.dumps(admin_phones)
            else:
                new_setting = Settings(key="admin_phone_numbers", value=json.dumps(admin_phones))
                db.session.add(new_setting)
        
        # Update Meta WhatsApp settings
        if "meta_whatsapp_settings" in data:
            meta_data = data["meta_whatsapp_settings"]
            existing_meta = Settings.query.filter_by(key="meta_whatsapp_settings").first()
            
            if existing_meta:
                existing_meta.value = json.dumps(meta_data)
            else:
                new_meta = Settings(key="meta_whatsapp_settings", value=json.dumps(meta_data))
                db.session.add(new_meta)
        
        db.session.commit()
        
        return jsonify({"message": "Bildirim ayarları başarıyla güncellendi"})
        
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

