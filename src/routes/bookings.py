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
                    "service_type": service.service_type,
                    "service_name": service.service_name,
                    "start_date": service.start_date.isoformat(),
                    "end_date": service.end_date.isoformat(),
                    "start_time": service.start_time.strftime("%H:%M") if service.start_time else None,
                    "end_time": service.end_time.strftime("%H:%M") if service.end_time else None,
                    "notes": service.notes,
                    "driver_id": service.driver_id,
                    "vehicle_id": service.vehicle_id,
                    "cost_to_company": service.cost_to_company,
                    "selling_price": service.selling_price,
                    "hotel_name": service.hotel_name,
                    "hotel_city": service.hotel_city,
                    "room_type": service.room_type,
                    "num_nights": service.num_nights,
                    "cost_per_night": service.cost_per_night,
                    "selling_price_per_night": service.selling_price_per_night,
                    "is_hourly": service.is_hourly,
                    "hours": service.hours,
                    "with_driver": service.with_driver,
                    "is_accommodation": service.is_accommodation,
                    "is_tour": service.is_tour,
                    "is_vehicle_rental": service.is_vehicle_rental,
                    "total_cost": service.total_cost,
                    "total_selling_price": service.total_selling_price,
                    "profit": service.profit
                }
                services_data.append(service_dict)

            booking_data = {
                "id": booking.id,
                "client_id": booking.client_id,
                "client": booking.client,
                "overall_start_date": booking.overall_start_date.isoformat(),
                "overall_end_date": booking.overall_end_date.isoformat(),
                "notes": booking.notes,
                "status": booking.status,
                "created_at": booking.created_at.isoformat(),
                "services": services_data,
                "total_cost": booking.total_cost,
                "total_selling_price": booking.total_selling_price,
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
        
        required_fields = ["client_id", "overall_start_date", "overall_end_date", "services"]
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"{field} is required"}), 400
        
        try:
            overall_start_date = datetime.strptime(data["overall_start_date"], "%Y-%m-%d").date()
            overall_end_date = datetime.strptime(data["overall_end_date"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Invalid date format for overall dates. Use YYYY-MM-DD"}), 400
        
        if overall_end_date < overall_start_date:
            return jsonify({"error": "Overall end date must be after overall start date"}), 400
        
        new_booking = Booking(
            client_id=int(data["client_id"]),
            overall_start_date=overall_start_date,
            overall_end_date=overall_end_date,
            notes=data.get("notes", ""),
            status=data.get("status", "pending")
        )
        db.session.add(new_booking)
        db.session.flush() # To get the new_booking.id

        for service_data in data["services"]:
            service_required_fields = ["service_type", "service_name", "start_date", "end_date"]
            for field in service_required_fields:
                if field not in service_data or not service_data[field]:
                    return jsonify({"error": f"Service {field} is required"}), 400
            
            try:
                service_start_date = datetime.strptime(service_data["start_date"], "%Y-%m-%d").date()
                service_end_date = datetime.strptime(service_data["end_date"], "%Y-%m-%d").date()
            except ValueError:
                return jsonify({"error": "Invalid date format for service dates. Use YYYY-MM-DD"}), 400
            
            if service_end_date < service_start_date:
                return jsonify({"error": "Service end date must be after service start date"}), 400

            is_accommodation = service_data["service_type"] in ["Hotel", "Cabin"]
            is_vehicle_rental = service_data["service_type"] == "Vehicle"
            is_tour = service_data["service_type"] == "Tour"
            
            new_service = Service(
                booking_id=new_booking.id,
                service_type=service_data["service_type"],
                service_name=service_data["service_name"],
                start_date=service_start_date,
                end_date=service_end_date,
                notes=service_data.get("notes", ""),
                driver_id=int(service_data["driver_id"]) if service_data.get("driver_id") else None,
                vehicle_id=int(service_data["vehicle_id"]) if service_data.get("vehicle_id") else None,
                is_hourly=service_data.get("is_hourly", False) if is_vehicle_rental else False,
                hours=float(service_data["hours"]) if service_data.get("hours") and is_vehicle_rental else None,
                with_driver=service_data.get("with_driver", None) if is_vehicle_rental else None
            )

            # Handle tour times
            if is_tour:
                if service_data.get("start_time"):
                    try:
                        new_service.start_time = datetime.strptime(service_data["start_time"], "%H:%M").time()
                    except ValueError:
                        return jsonify({"error": "Invalid start time format. Use HH:MM"}), 400
                
                if service_data.get("end_time"):
                    try:
                        new_service.end_time = datetime.strptime(service_data["end_time"], "%H:%M").time()
                    except ValueError:
                        return jsonify({"error": "Invalid end time format. Use HH:MM"}), 400

            if is_accommodation:
                accommodation_fields = ["hotel_name", "hotel_city", "room_type", "num_nights", "cost_per_night", "selling_price_per_night"]
                for field in accommodation_fields:
                    if field not in service_data or not service_data[field]:
                        return jsonify({"error": f"Service {field} is required for accommodation bookings"}), 400
                
                try:
                    new_service.num_nights = int(service_data["num_nights"])
                    new_service.cost_per_night = float(service_data["cost_per_night"])
                    new_service.selling_price_per_night = float(service_data["selling_price_per_night"])
                    
                    if new_service.num_nights <= 0 or new_service.cost_per_night < 0 or new_service.selling_price_per_night < 0:
                        return jsonify({"error": "Numeric values for accommodation must be positive"}), 400
                    
                except (ValueError, TypeError):
                    return jsonify({"error": "Invalid numeric values for accommodation"}), 400
                
                new_service.hotel_name = service_data["hotel_name"]
                new_service.hotel_city = service_data["hotel_city"]
                new_service.room_type = service_data["room_type"]
            else:
                if "cost_to_company" not in service_data or "selling_price" not in service_data:
                    return jsonify({"error": "cost_to_company and selling_price are required for non-accommodation services"}), 400
                
                try:
                    new_service.cost_to_company = float(service_data["cost_to_company"])
                    new_service.selling_price = float(service_data["selling_price"])
                    
                    if new_service.cost_to_company < 0 or new_service.selling_price < 0:
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
        
        required_fields = ["client_id", "overall_start_date", "overall_end_date", "services"]
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"{field} is required"}), 400
        
        try:
            overall_start_date = datetime.strptime(data["overall_start_date"], "%Y-%m-%d").date()
            overall_end_date = datetime.strptime(data["overall_end_date"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Invalid date format for overall dates. Use YYYY-MM-DD"}), 400
        
        if overall_end_date < overall_start_date:
            return jsonify({"error": "Overall end date must be after overall start date"}), 400
        
        booking.client_id = int(data["client_id"])
        booking.overall_start_date = overall_start_date
        booking.overall_end_date = overall_end_date
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
            service_required_fields = ["service_type", "service_name", "start_date", "end_date"]
            for field in service_required_fields:
                if field not in service_data or not service_data[field]:
                    return jsonify({"error": f"Service {field} is required"}), 400
            
            try:
                service_start_date = datetime.strptime(service_data["start_date"], "%Y-%m-%d").date()
                service_end_date = datetime.strptime(service_data["end_date"], "%Y-%m-%d").date()
            except ValueError:
                return jsonify({"error": "Invalid date format for service dates. Use YYYY-MM-DD"}), 400
            
            if service_end_date < service_start_date:
                return jsonify({"error": "Service end date must be after service start date"}), 400

            is_accommodation = service_data["service_type"] in ["Hotel", "Cabin"]
            is_vehicle_rental = service_data["service_type"] == "Vehicle"
            is_tour = service_data["service_type"] == "Tour"
            
            new_service = Service(
                booking_id=booking.id,
                service_type=service_data["service_type"],
                service_name=service_data["service_name"],
                start_date=service_start_date,
                end_date=service_end_date,
                notes=service_data.get("notes", ""),
                driver_id=int(service_data["driver_id"]) if service_data.get("driver_id") else None,
                vehicle_id=int(service_data["vehicle_id"]) if service_data.get("vehicle_id") else None,
                is_hourly=service_data.get("is_hourly", False) if is_vehicle_rental else False,
                hours=float(service_data["hours"]) if service_data.get("hours") and is_vehicle_rental else None,
                with_driver=service_data.get("with_driver", None) if is_vehicle_rental else None
            )

            # Handle tour times
            if is_tour:
                if service_data.get("start_time"):
                    try:
                        new_service.start_time = datetime.strptime(service_data["start_time"], "%H:%M").time()
                    except ValueError:
                        return jsonify({"error": "Invalid start time format. Use HH:MM"}), 400
                
                if service_data.get("end_time"):
                    try:
                        new_service.end_time = datetime.strptime(service_data["end_time"], "%H:%M").time()
                    except ValueError:
                        return jsonify({"error": "Invalid end time format. Use HH:MM"}), 400

            if is_accommodation:
                accommodation_fields = ["hotel_name", "hotel_city", "room_type", "num_nights", "cost_per_night", "selling_price_per_night"]
                for field in accommodation_fields:
                    if field not in service_data or not service_data[field]:
                        return jsonify({"error": f"Service {field} is required for accommodation bookings"}), 400
                
                try:
                    new_service.num_nights = int(service_data["num_nights"])
                    new_service.cost_per_night = float(service_data["cost_per_night"])
                    new_service.selling_price_per_night = float(service_data["selling_price_per_night"])
                    
                    if new_service.num_nights <= 0 or new_service.cost_per_night < 0 or new_service.selling_price_per_night < 0:
                        return jsonify({"error": "Numeric values for accommodation must be positive"}), 400
                    
                except (ValueError, TypeError):
                    return jsonify({"error": "Invalid numeric values for accommodation"}), 400
                
                new_service.hotel_name = service_data["hotel_name"]
                new_service.hotel_city = service_data["hotel_city"]
                new_service.room_type = service_data["room_type"]
            else:
                if "cost_to_company" not in service_data or "selling_price" not in service_data:
                    return jsonify({"error": "cost_to_company and selling_price are required for non-accommodation services"}), 400
                
                try:
                    new_service.cost_to_company = float(service_data["cost_to_company"])
                    new_service.selling_price = float(service_data["selling_price"])
                    
                    if new_service.cost_to_company < 0 or new_service.selling_price < 0:
                        return jsonify({"error": "Cost and selling price must be non-negative"}), 400
                    
                except (ValueError, TypeError):
                    return jsonify({"error": "Invalid cost or selling price"}), 400
            
            db.session.add(new_service)
        
        db.session.commit()
        
        return jsonify({"message": "Booking updated successfully"}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@bookings_bp.route("/bookings/<int:booking_id>", methods=["DELETE"])
def delete_booking(booking_id):
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Delete associated MonthlyInvoiceItem records first
        existing_services = Service.query.filter_by(booking_id=booking.id).all()
        for service in existing_services:
            MonthlyInvoiceItem.query.filter_by(service_id=service.id).delete()
        db.session.flush() # Flush to ensure MonthlyInvoiceItem deletions are processed

        # Now delete the booking, which will cascade to services and invoices
        db.session.delete(booking)
        db.session.commit()
        
        return jsonify({"message": "Booking deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


