from flask import Blueprint, request, jsonify
from src.models.database import db, Booking, Client, Driver, Vehicle, Service, Invoice, Notification, MonthlyInvoiceItem
from datetime import datetime, time

bookings_bp = Blueprint("bookings", __name__)

@bookings_bp.route("/bookings", methods=["GET"])
def get_bookings():
    try:
        bookings = Booking.query.all()
        bookings_data = []
        
        for booking in bookings:
            services_data = []
            for service in booking.services:
                service_dict = {
                    "id": service.id,
                    "serviceType": service.serviceType,
                    "serviceName": service.serviceName,
                    "startDate": service.startDate.isoformat(),
                    "endDate": service.endDate.isoformat(),
                    "startTime": service.startTime.strftime("%H:%M") if service.startTime else None,
                    "endTime": service.endTime.strftime("%H:%M") if service.endTime else None,
                    "notes": service.notes,
                    "driverId": service.driver_id,
                    "vehicleId": service.vehicle_id,
                    "costToCompany": service.costToCompany,
                    "sellingPrice": service.sellingPrice,
                    "hotelName": service.hotelName,
                    "hotelCity": service.hotelCity,
                    "roomType": service.roomType,
                    "numNights": service.numNights,
                    "costPerNight": service.costPerNight,
                    "sellingPricePerNight": service.sellingPricePerNight,
                    "is_hourly": service.is_hourly,
                    "hours": service.hours,
                    "with_driver": service.with_driver,
                    "isAccommodation": service.isAccommodation,
                    "isTour": service.isTour,
                    "isVehicleRental": service.isVehicleRental,
                    "totalCost": service.totalCost,
                    "totalSellingPrice": service.totalSellingPrice,
                    "profit": service.profit
                }
                services_data.append(service_dict)

            booking_data = {
                "id": booking.id,
                "clientId": booking.client_id,
                "client": booking.client,
                "overall_startDate": booking.overall_startDate.isoformat(),
                "overall_endDate": booking.overall_endDate.isoformat(),
                "notes": booking.notes,
                "status": booking.status,
                "createdAt": booking.created_at.isoformat(),
                "services": services_data,
                "totalCost": booking.totalCost,
                "totalSellingPrice": booking.totalSellingPrice,
                "profit": booking.profit
            }
            
            bookings_data.append(booking_data)
        
        return jsonify(bookings_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bookings_bp.route("/bookings", methods=["POST"])
def add_booking():
    try:
        data = request.get_json()
        
        required_fields = ["clientId", "overall_startDate", "overall_endDate", "services"]
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"{field} is required"}), 400
        
        try:
            overall_start_date = datetime.strptime(data["overall_startDate"], "%Y-%m-%d").date()
            overall_end_date = datetime.strptime(data["overall_endDate"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Invalid date format for overall dates. Use YYYY-MM-DD"}), 400
        
        if overall_end_date < overall_start_date:
            return jsonify({"error": "Overall end date must be after overall start date"}), 400
        
        new_booking = Booking(
            client_id=int(data["clientId"]),
            overall_startDate=overall_start_date,
            overall_endDate=overall_end_date,
            notes=data.get("notes", ""),
            status=data.get("status", "pending")
        )
        db.session.add(new_booking)
        db.session.flush() # To get the new_booking.id

        for service_data in data["services"]:
            service_required_fields = ["serviceType", "serviceName", "startDate", "endDate"]
            for field in service_required_fields:
                if field not in service_data or not service_data[field]:
                    return jsonify({"error": f"Service {field} is required"}), 400
            
            try:
                service_start_date = datetime.strptime(service_data["startDate"], "%Y-%m-%d").date()
                service_end_date = datetime.strptime(service_data["endDate"], "%Y-%m-%d").date()
            except ValueError:
                return jsonify({"error": "Invalid date format for service dates. Use YYYY-MM-DD"}), 400
            
            if service_end_date < service_start_date:
                return jsonify({"error": "Service end date must be after service start date"}), 400

            is_accommodation = service_data["serviceType"] in ["Hotel", "Cabin"]
            is_vehicle_rental = service_data["serviceType"] == "Vehicle"
            is_tour = service_data["serviceType"] == "Tour"
            
            new_service = Service(
                booking_id=new_booking.id,
                serviceType=service_data["serviceType"],
                serviceName=service_data["serviceName"],
                startDate=service_start_date,
                endDate=service_end_date,
                notes=service_data.get("notes", ""),
                driver_id=int(service_data["driverId"]) if service_data.get("driverId") else None,
                vehicle_id=int(service_data["vehicleId"]) if service_data.get("vehicleId") else None,
                is_hourly=service_data.get("is_hourly", False) if is_vehicle_rental else False,
                hours=float(service_data["hours"]) if service_data.get("hours") and is_vehicle_rental else None,
                with_driver=service_data.get("with_driver", None) if is_vehicle_rental else None
            )

            # Handle tour times
            if is_tour:
                if service_data.get("startTime"):
                    try:
                        new_service.startTime = datetime.strptime(service_data["startTime"], "%H:%M").time()
                    except ValueError:
                        return jsonify({"error": "Invalid start time format. Use HH:MM"}), 400
                
                if service_data.get("endTime"):
                    try:
                        new_service.endTime = datetime.strptime(service_data["endTime"], "%H:%M").time()
                    except ValueError:
                        return jsonify({"error": "Invalid end time format. Use HH:MM"}), 400

            if is_accommodation:
                accommodation_fields = ["hotelName", "hotelCity", "roomType", "numNights", "costPerNight", "sellingPricePerNight"]
                for field in accommodation_fields:
                    if field not in service_data or not service_data[field]:
                        return jsonify({"error": f"Service {field} is required for accommodation bookings"}), 400
                
                try:
                    new_service.numNights = int(service_data["numNights"])
                    new_service.costPerNight = float(service_data["costPerNight"])
                    new_service.sellingPricePerNight = float(service_data["sellingPricePerNight"])
                    
                    if new_service.numNights <= 0 or new_service.costPerNight < 0 or new_service.sellingPricePerNight < 0:
                        return jsonify({"error": "Numeric values for accommodation must be positive"}), 400
                    
                except (ValueError, TypeError):
                    return jsonify({"error": "Invalid numeric values for accommodation"}), 400
                
                new_service.hotelName = service_data["hotelName"]
                new_service.hotelCity = service_data["hotelCity"]
                new_service.roomType = service_data["roomType"]
            else:
                if "costToCompany" not in service_data or "sellingPrice" not in service_data:
                    return jsonify({"error": "costToCompany and sellingPrice are required for non-accommodation services"}), 400
                
                try:
                    new_service.costToCompany = float(service_data["costToCompany"])
                    new_service.sellingPrice = float(service_data["sellingPrice"])
                    
                    if new_service.costToCompany < 0 or new_service.sellingPrice < 0:
                        return jsonify({"error": "Cost and selling price must be non-negative"}), 400
                    
                except (ValueError, TypeError):
                    return jsonify({"error": "Invalid cost or selling price"}), 400
            
            db.session.add(new_service)
        
        db.session.commit()
        
        return jsonify({"message": "Booking added successfully", "id": new_booking.id}), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@bookings_bp.route("/bookings/<int:booking_id>", methods=["PUT"])
def update_booking(booking_id):
    try:
        booking = Booking.query.get_or_404(booking_id)
        data = request.get_json()
        
        required_fields = ["clientId", "overall_startDate", "overall_endDate", "services"]
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"{field} is required"}), 400
        
        try:
            overall_start_date = datetime.strptime(data["overall_startDate"], "%Y-%m-%d").date()
            overall_end_date = datetime.strptime(data["overall_endDate"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Invalid date format for overall dates. Use YYYY-MM-DD"}), 400
        
        if overall_end_date < overall_start_date:
            return jsonify({"error": "Overall end date must be after overall start date"}), 400
        
        booking.client_id = int(data["clientId"])
        booking.overall_startDate = overall_start_date
        booking.overall_endDate = overall_end_date
        booking.notes = data.get("notes", "")
        booking.status = data.get("status", "pending")

        # Handle services: delete existing, add new ones
        # First, delete associated MonthlyInvoiceItem records for each service
        existing_services = Service.query.filter_by(booking_id=booking.id).all()
        for service in existing_services:
            MonthlyInvoiceItem.query.filter_by(service_id=service.id).delete()
        db.session.flush() # Flush to ensure MonthlyInvoiceItem deletions are processed

        Service.query.filter_by(booking_id=booking.id).delete()
        db.session.flush()

        for service_data in data["services"]:
            service_required_fields = ["serviceType", "serviceName", "startDate", "endDate"]
            for field in service_required_fields:
                if field not in service_data or not service_data[field]:
                    return jsonify({"error": f"Service {field} is required"}), 400
            
            try:
                service_start_date = datetime.strptime(service_data["startDate"], "%Y-%m-%d").date()
                service_end_date = datetime.strptime(service_data["endDate"], "%Y-%m-%d").date()
            except ValueError:
                return jsonify({"error": "Invalid date format for service dates. Use YYYY-MM-DD"}), 400
            
            if service_end_date < service_start_date:
                return jsonify({"error": "Service end date must be after service start date"}), 400

            is_accommodation = service_data["serviceType"] in ["Hotel", "Cabin"]
            is_vehicle_rental = service_data["serviceType"] == "Vehicle"
            is_tour = service_data["serviceType"] == "Tour"
            
            new_service = Service(
                booking_id=booking.id,
                serviceType=service_data["serviceType"],
                serviceName=service_data["serviceName"],
                startDate=service_start_date,
                endDate=service_end_date,
                notes=service_data.get("notes", ""),
                driver_id=int(service_data["driverId"]) if service_data.get("driverId") else None,
                vehicle_id=int(service_data["vehicleId"]) if service_data.get("vehicleId") else None,
                is_hourly=service_data.get("is_hourly", False) if is_vehicle_rental else False,
                hours=float(service_data["hours"]) if service_data.get("hours") and is_vehicle_rental else None,
                with_driver=service_data.get("with_driver", None) if is_vehicle_rental else None
            )

            # Handle tour times
            if is_tour:
                if service_data.get("startTime"):
                    try:
                        new_service.startTime = datetime.strptime(service_data["startTime"], "%H:%M").time()
                    except ValueError:
                        return jsonify({"error": "Invalid start time format. Use HH:MM"}), 400
                
                if service_data.get("endTime"):
                    try:
                        new_service.endTime = datetime.strptime(service_data["endTime"], "%H:%M").time()
                    except ValueError:
                        return jsonify({"error": "Invalid end time format. Use HH:MM"}), 400

            if is_accommodation:
                accommodation_fields = ["hotelName", "hotelCity", "roomType", "numNights", "costPerNight", "sellingPricePerNight"]
                for field in accommodation_fields:
                    if field not in service_data or not service_data[field]:
                        return jsonify({"error": f"Service {field} is required for accommodation bookings"}), 400
                
                try:
                    new_service.numNights = int(service_data["numNights"])
                    new_service.costPerNight = float(service_data["costPerNight"])
                    new_service.sellingPricePerNight = float(service_data["sellingPricePerNight"])
                    
                    if new_service.numNights <= 0 or new_service.costPerNight < 0 or new_service.sellingPricePerNight < 0:
                        return jsonify({"error": "Numeric values for accommodation must be positive"}), 400
                    
                except (ValueError, TypeError):
                    return jsonify({"error": "Invalid numeric values for accommodation"}), 400
                
                new_service.hotelName = service_data["hotelName"]
                new_service.hotelCity = service_data["hotelCity"]
                new_service.roomType = service_data["roomType"]
            else:
                if "costToCompany" not in service_data or "sellingPrice" not in service_data:
                    return jsonify({"error": "costToCompany and sellingPrice are required for non-accommodation services"}), 400
                
                try:
                    new_service.costToCompany = float(service_data["costToCompany"])
                    new_service.sellingPrice = float(service_data["sellingPrice"])
                    
                    if new_service.costToCompany < 0 or new_service.sellingPrice < 0:
                        return jsonify({"error": "Cost and selling price must be non-negative"}), 400
                    
                except (ValueError, TypeError):
                    return jsonify({"error": "Invalid cost or selling price"}), 400
            
            db.session.add(new_service)
        
        db.session.commit()
        
        return jsonify({"message": "Booking updated successfully"})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@bookings_bp.route("/bookings/<int:booking_id>", methods=["DELETE"])
def delete_booking(booking_id):
    try:
        booking = Booking.query.get_or_404(booking_id)

        # الطريقة الصحيحة: حذف الفواتير أولاً وبشكل صريح
        # هذا يمنع SQLAlchemy من محاولة تحديث booking_id إلى NULL
        print(f"🗑️ بدء حذف الحجز رقم {booking_id}")
        
        # الخطوة 1: حذف الفواتير أولاً (هذا هو الأهم!)
        invoices = Invoice.query.filter_by(booking_id=booking.id).all()
        print(f"📄 العثور على {len(invoices)} فاتورة مرتبطة")
        for invoice in invoices:
            print(f"   حذف الفاتورة رقم {invoice.id}")
            db.session.delete(invoice)
        
        # فرض تنفيذ حذف الفواتير فوراً قبل المتابعة
        if invoices:
            db.session.flush()
            print("✅ تم حذف جميع الفواتير")

        # الخطوة 2: حذف عناصر الفواتير الشهرية المرتبطة بالخدمات
        monthly_items_count = 0
        for service in booking.services:
            monthly_invoice_items = MonthlyInvoiceItem.query.filter_by(service_id=service.id).all()
            for item in monthly_invoice_items:
                db.session.delete(item)
                monthly_items_count += 1
        
        if monthly_items_count > 0:
            db.session.flush()
            print(f"✅ تم حذف {monthly_items_count} عنصر من الفواتير الشهرية")

        # الخطوة 3: حذف الإشعارات المرتبطة بالحجز
        notifications = Notification.query.filter_by(booking_id=booking.id).all()
        print(f"🔔 العثور على {len(notifications)} إشعار مرتبط")
        for notification in notifications:
            db.session.delete(notification)
        
        if notifications:
            db.session.flush()
            print("✅ تم حذف جميع الإشعارات")

        # الخطوة 4: حذف الخدمات المرتبطة بالحجز
        services = Service.query.filter_by(booking_id=booking.id).all()
        print(f"🛎️ العثور على {len(services)} خدمة مرتبطة")
        for service in services:
            db.session.delete(service)
        
        if services:
            db.session.flush()
            print("✅ تم حذف جميع الخدمات")

        # الخطوة 5: حذف الحجز نفسه (الآن يجب أن يكون آمناً)
        print(f"📋 حذف الحجز رقم {booking.id}")
        db.session.delete(booking)
        
        # تنفيذ جميع التغييرات
        db.session.commit()
        print("✅ تم حذف الحجز وجميع البيانات المرتبطة به بنجاح")

        return jsonify({"message": "تم حذف الحجز وجميع البيانات المرتبطة به بنجاح"})
    
    except Exception as e:
        print(f"❌ خطأ في حذف الحجز: {str(e)}")
        db.session.rollback()
        return jsonify({"error": f"خطأ في حذف الحجز: {str(e)}"}), 500

@bookings_bp.route("/bookings/service-types", methods=["GET"])
def get_service_types():
    try:
        # Return predefined service types
        service_types = ["Hotel", "Vehicle","Tour"]
        return jsonify(service_types)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

