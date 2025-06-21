from flask import Blueprint, request, jsonify
from src.models.database import db, Driver, Vehicle, Booking, Service # Import Service model

drivers_bp = Blueprint("drivers", __name__)

@drivers_bp.route("/drivers", methods=["GET"])
def get_drivers():
    try:
        drivers = Driver.query.all()
        result = []
        for driver in drivers:
            # Get assigned vehicles
            assigned_vehicles = []
            for vehicle in driver.assigned_vehicles:
                assigned_vehicles.append({
                    "id": vehicle.id,
                    "model": vehicle.model,
                    "plateNumber": vehicle.plateNumber,
                    "type": vehicle.type
                })
            
            # Calculate booking statistics for the driver
            total_bookings = Service.query.filter_by(driver_id=driver.id).join(Booking).count()
            active_bookings = Service.query.filter_by(driver_id=driver.id).join(Booking).filter(
                Booking.status.in_(["pending", "confirmed"])
            ).count()
            completed_bookings = Service.query.filter_by(driver_id=driver.id).join(Booking).filter(
                Booking.status == "completed"
            ).count()
            
            result.append({
                "id": driver.id,
                "firstName": driver.firstName,
                "lastName": driver.lastName,
                "email": driver.email,
                "phone": driver.phone,
                "licenseNumber": driver.licenseNumber,
                "assignedVehicles": assigned_vehicles,
                "totalBookings": total_bookings,
                "activeBookings": active_bookings,
                "completedBookings": completed_bookings
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@drivers_bp.route("/drivers/<int:driver_id>", methods=["GET"])
def get_driver(driver_id):
    try:
        driver = Driver.query.get_or_404(driver_id)
        
        # Get assigned vehicles
        assigned_vehicles = []
        for vehicle in driver.assigned_vehicles:
            assigned_vehicles.append({
                "id": vehicle.id,
                "model": vehicle.model,
                "plateNumber": vehicle.plateNumber,
                "type": vehicle.type
            })
        
        return jsonify({
            "id": driver.id,
            "firstName": driver.firstName,
            "lastName": driver.lastName,
            "email": driver.email,
            "phone": driver.phone,
            "licenseNumber": driver.licenseNumber,
            "assignedVehicles": assigned_vehicles
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@drivers_bp.route("/drivers", methods=["POST"])
def add_driver():
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get("firstName") or not data.get("lastName") or not data.get("email") or not data.get("licenseNumber"):
            return jsonify({"error": "First name, last name, email, and license number are required"}), 400
        
        # Check if email already exists
        existing_driver = Driver.query.filter_by(email=data["email"]).first()
        if existing_driver:
            return jsonify({"error": "Email already exists"}), 400
        
        # Check if license number already exists
        existing_license = Driver.query.filter_by(licenseNumber=data["licenseNumber"]).first()
        if existing_license:
            return jsonify({"error": "License number already exists"}), 400
        
        driver = Driver(
            firstName=data["firstName"],
            lastName=data["lastName"],
            email=data["email"],
            phone=data.get("phone"),
            licenseNumber=data["licenseNumber"]
        )
        
        db.session.add(driver)
        db.session.commit()
        
        return jsonify({
            "id": driver.id,
            "firstName": driver.firstName,
            "lastName": driver.lastName,
            "email": driver.email,
            "phone": driver.phone,
            "licenseNumber": driver.licenseNumber,
            "assignedVehicles": []
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@drivers_bp.route("/drivers/<int:driver_id>", methods=["PUT"])
def update_driver(driver_id):
    try:
        driver = Driver.query.get_or_404(driver_id)
        data = request.get_json()
        
        # Validate required fields
        if not data.get("firstName") or not data.get("lastName") or not data.get("email") or not data.get("licenseNumber"):
            return jsonify({"error": "First name, last name, email, and license number are required"}), 400
        
        # Check if email already exists (excluding current driver)
        existing_driver = Driver.query.filter(Driver.email == data["email"], Driver.id != driver_id).first()
        if existing_driver:
            return jsonify({"error": "Email already exists"}), 400
        
        # Check if license number already exists (excluding current driver)
        existing_license = Driver.query.filter(Driver.licenseNumber == data["licenseNumber"], Driver.id != driver_id).first()
        if existing_license:
            return jsonify({"error": "License number already exists"}), 400
        
        driver.firstName = data["firstName"]
        driver.lastName = data["lastName"]
        driver.email = data["email"]
        driver.phone = data.get("phone")
        driver.licenseNumber = data["licenseNumber"]
        
        db.session.commit()
        
        # Get assigned vehicles
        assigned_vehicles = []
        for vehicle in driver.assigned_vehicles:
            assigned_vehicles.append({
                "id": vehicle.id,
                "model": vehicle.model,
                "plateNumber": vehicle.plateNumber,
                "type": vehicle.type
            })
        
        return jsonify({
            "id": driver.id,
            "firstName": driver.firstName,
            "lastName": driver.lastName,
            "email": driver.email,
            "phone": driver.phone,
            "licenseNumber": driver.licenseNumber,
            "assignedVehicles": assigned_vehicles
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@drivers_bp.route("/drivers/<int:driver_id>/assign-vehicles", methods=["PUT"])
def assign_vehicles_to_driver(driver_id):
    try:
        driver = Driver.query.get_or_404(driver_id)
        data = request.get_json()
        
        vehicle_ids = data.get("vehicleIds", [])
        
        # Clear current assignments for this driver
        for vehicle in driver.assigned_vehicles:
            vehicle.assigned_driver_id = None
        
        # Assign new vehicles
        for vehicle_id in vehicle_ids:
            vehicle = Vehicle.query.get(vehicle_id)
            if vehicle:
                # Check if vehicle is already assigned to another driver
                if vehicle.assigned_driver_id and vehicle.assigned_driver_id != driver_id:
                    return jsonify({"error": f"Vehicle {vehicle.model} - {vehicle.plateNumber} is already assigned to another driver"}), 400
                vehicle.assigned_driver_id = driver_id
        
        db.session.commit()
        
        # Get updated assigned vehicles
        assigned_vehicles = []
        for vehicle in driver.assigned_vehicles:
            assigned_vehicles.append({
                "id": vehicle.id,
                "model": vehicle.model,
                "plateNumber": vehicle.plateNumber,
                "type": vehicle.type
            })
        
        return jsonify({
            "message": "Vehicle assignment updated successfully",
            "assignedVehicles": assigned_vehicles
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@drivers_bp.route("/drivers/<int:driver_id>", methods=["DELETE"])
def delete_driver(driver_id):
    try:
        driver = Driver.query.get_or_404(driver_id)
        
        # Check if driver has active bookings
        active_bookings = Booking.query.filter_by(driver_id=driver_id).filter(
            Booking.status.in_(["pending", "confirmed"])
        ).count()
        
        if active_bookings > 0:
            return jsonify({"error": f"Cannot delete driver with {active_bookings} active bookings"}), 400
        
        # Unassign vehicles before deleting driver
        for vehicle in driver.assigned_vehicles:
            vehicle.assigned_driver_id = None
        
        db.session.delete(driver)
        db.session.commit()
        return jsonify({"message": "Driver deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500




# New endpoint to get driver schedule/calendar data
@drivers_bp.route("/drivers/<int:driver_id>/schedule", methods=["GET"])
def get_driver_schedule(driver_id):
    try:
        from datetime import datetime, timedelta
        
        driver = Driver.query.get_or_404(driver_id)
        
        # Get date range from query parameters (default to current month)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date:
            # Default to current month
            today = datetime.now().date()
            start_date = today.replace(day=1)
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            
        if not end_date:
            # Default to end of current month
            if start_date.month == 12:
                end_date = start_date.replace(year=start_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_date = start_date.replace(month=start_date.month + 1, day=1) - timedelta(days=1)
        else:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Get all services for this driver within the date range
        services = Service.query.filter_by(driver_id=driver_id).join(Booking).filter(
            Service.startDate >= start_date,
            Service.endDate <= end_date,
            Booking.status.in_(["pending", "confirmed", "completed"])
        ).all()
        
        schedule_data = []
        for service in services:
            schedule_data.append({
                "id": service.id,
                "title": service.serviceName,
                "start": service.startDate.isoformat(),
                "end": service.endDate.isoformat(),
                "startTime": service.startTime.strftime("%H:%M") if service.startTime else None,
                "endTime": service.endTime.strftime("%H:%M") if service.endTime else None,
                "serviceType": service.serviceType,
                "bookingId": service.booking_id,
                "bookingStatus": service.booking_ref.status,
                "clientName": f"{service.booking_ref.client_ref.firstName} {service.booking_ref.client_ref.lastName}" if service.booking_ref.client_ref else "Unknown",
                "vehicleInfo": f"{service.vehicle_ref.model} - {service.vehicle_ref.plateNumber}" if service.vehicle_ref else None,
                "notes": service.notes
            })
        
        return jsonify({
            "driverId": driver_id,
            "driverName": f"{driver.firstName} {driver.lastName}",
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "schedule": schedule_data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# New endpoint to get all drivers with their current booking status
@drivers_bp.route("/drivers/status", methods=["GET"])
def get_drivers_status():
    try:
        from datetime import datetime, date
        
        drivers = Driver.query.all()
        result = []
        
        today = date.today()
        
        for driver in drivers:
            # Check if driver has any active bookings today
            active_today = Service.query.filter_by(driver_id=driver.id).join(Booking).filter(
                Service.startDate <= today,
                Service.endDate >= today,
                Booking.status.in_(["pending", "confirmed"])
            ).first()
            
            # Get next upcoming booking
            next_booking = Service.query.filter_by(driver_id=driver.id).join(Booking).filter(
                Service.startDate > today,
                Booking.status.in_(["pending", "confirmed"])
            ).order_by(Service.startDate.asc()).first()
            
            status = "available"
            if active_today:
                status = "busy"
            elif next_booking:
                status = "scheduled"
            
            result.append({
                "id": driver.id,
                "firstName": driver.firstName,
                "lastName": driver.lastName,
                "fullName": f"{driver.firstName} {driver.lastName}",
                "status": status,
                "currentBooking": {
                    "id": active_today.id,
                    "serviceName": active_today.serviceName,
                    "startDate": active_today.startDate.isoformat(),
                    "endDate": active_today.endDate.isoformat(),
                    "clientName": f"{active_today.booking_ref.client_ref.firstName} {active_today.booking_ref.client_ref.lastName}" if active_today.booking_ref.client_ref else "Unknown"
                } if active_today else None,
                "nextBooking": {
                    "id": next_booking.id,
                    "serviceName": next_booking.serviceName,
                    "startDate": next_booking.startDate.isoformat(),
                    "endDate": next_booking.endDate.isoformat(),
                    "clientName": f"{next_booking.booking_ref.client_ref.firstName} {next_booking.booking_ref.client_ref.lastName}" if next_booking.booking_ref.client_ref else "Unknown"
                } if next_booking else None
            })
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

