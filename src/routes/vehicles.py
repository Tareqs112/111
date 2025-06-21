from flask import Blueprint, request, jsonify
from src.models.database import db, Vehicle, Booking, Driver, Service # Import Service model

vehicles_bp = Blueprint("vehicles", __name__)

@vehicles_bp.route("/vehicles", methods=["GET"])
def get_vehicles():
    try:
        vehicles = Vehicle.query.all()
        result = []
        for vehicle in vehicles:
            # Check current availability by querying through Service model
            active_services = Service.query.filter_by(vehicle_id=vehicle.id).join(Booking).filter(
                Booking.status.in_(["pending", "confirmed"])
            ).count()
            
            availability = "Available" if active_services == 0 else "Booked"
            
            # Calculate booking statistics for the vehicle
            total_bookings = Service.query.filter_by(vehicle_id=vehicle.id).join(Booking).count()
            active_bookings = Service.query.filter_by(vehicle_id=vehicle.id).join(Booking).filter(
                Booking.status.in_(["pending", "confirmed"])
            ).count()
            completed_bookings = Service.query.filter_by(vehicle_id=vehicle.id).join(Booking).filter(
                Booking.status == "completed"
            ).count()
            
            # Get assigned driver (permanent assignment)
            assigned_driver = None
            assigned_driver_id = None
            if vehicle.assigned_driver:
                assigned_driver = f"{vehicle.assigned_driver.firstName} {vehicle.assigned_driver.lastName}"
                assigned_driver_id = vehicle.assigned_driver.id
            
            # Calculate booking statistics for the vehicle
            total_bookings = Service.query.filter_by(vehicle_id=vehicle.id).join(Booking).count()
            active_bookings = Service.query.filter_by(vehicle_id=vehicle.id).join(Booking).filter(
                Booking.status.in_(["pending", "confirmed"])
            ).count()
            completed_bookings = Service.query.filter_by(vehicle_id=vehicle.id).join(Booking).filter(
                Booking.status == "completed"
            ).count()
            
            result.append({
                "id": vehicle.id,
                "model": vehicle.model,
                "plateNumber": vehicle.plateNumber,
                "type": vehicle.type,
                "capacity": vehicle.capacity,
                "assignedDriver": assigned_driver,
                "assignedDriverId": assigned_driver_id,
                "availability": availability,
                "totalBookings": total_bookings,
                "activeBookings": active_bookings,
                "completedBookings": completed_bookings
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@vehicles_bp.route("/vehicles/<int:vehicle_id>", methods=["GET"])
def get_vehicle(vehicle_id):
    try:
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        
        # Check current availability by querying through Service model
        active_services = Service.query.filter_by(vehicle_id=vehicle.id).join(Booking).filter(
            Booking.status.in_(["pending", "confirmed"])
        ).count()
        
        availability = "Available" if active_services == 0 else "Booked"
        
        # Get assigned driver (permanent assignment)
        assigned_driver = None
        assigned_driver_id = None
        if vehicle.assigned_driver:
            assigned_driver = f"{vehicle.assigned_driver.firstName} {vehicle.assigned_driver.lastName}"
            assigned_driver_id = vehicle.assigned_driver.id
        
        return jsonify({
            "id": vehicle.id,
            "model": vehicle.model,
            "plateNumber": vehicle.plateNumber,
            "type": vehicle.type,
            "capacity": vehicle.capacity,
            "assignedDriver": assigned_driver,
            "assignedDriverId": assigned_driver_id,
            "availability": availability
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@vehicles_bp.route("/vehicles", methods=["POST"])
def add_vehicle():
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get("model") or not data.get("plateNumber") or not data.get("type") or not data.get("capacity"):
            return jsonify({"error": "Model, plate number, type, and capacity are required"}), 400
        
        # Check if plate number already exists
        existing_vehicle = Vehicle.query.filter_by(plateNumber=data["plateNumber"]).first()
        if existing_vehicle:
            return jsonify({"error": "Plate number already exists"}), 400
        
        vehicle = Vehicle(
            model=data["model"],
            plateNumber=data["plateNumber"],
            type=data["type"],
            capacity=int(data["capacity"]),
            assigned_driver_id=data.get("assignedDriverId") if data.get("assignedDriverId") else None
        )
        
        db.session.add(vehicle)
        db.session.commit()
        
        # Get assigned driver info for response
        assigned_driver = None
        assigned_driver_id = None
        if vehicle.assigned_driver:
            assigned_driver = f"{vehicle.assigned_driver.firstName} {vehicle.assigned_driver.lastName}"
            assigned_driver_id = vehicle.assigned_driver.id
        
        return jsonify({
            "id": vehicle.id,
            "model": vehicle.model,
            "plateNumber": vehicle.plateNumber,
            "type": vehicle.type,
            "capacity": vehicle.capacity,
            "assignedDriver": assigned_driver,
            "assignedDriverId": assigned_driver_id,
            "availability": "Available"
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@vehicles_bp.route("/vehicles/<int:vehicle_id>", methods=["PUT"])
def update_vehicle(vehicle_id):
    try:
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        data = request.get_json()
        
        # Validate required fields
        if not data.get("model") or not data.get("plateNumber") or not data.get("type") or not data.get("capacity"):
            return jsonify({"error": "Model, plate number, type, and capacity are required"}), 400
        
        # Check if plate number already exists (excluding current vehicle)
        existing_vehicle = Vehicle.query.filter(Vehicle.plateNumber == data["plateNumber"], Vehicle.id != vehicle_id).first()
        if existing_vehicle:
            return jsonify({"error": "Plate number already exists"}), 400
        
        vehicle.model = data["model"]
        vehicle.plateNumber = data["plateNumber"]
        vehicle.type = data["type"]
        vehicle.capacity = int(data["capacity"])
        
        # Handle assigned_driver_id update
        if "assignedDriverId" in data:
            vehicle.assigned_driver_id = data["assignedDriverId"] if data["assignedDriverId"] else None

        db.session.commit()
        
        # Get current status by querying through Service model
        active_services = Service.query.filter_by(vehicle_id=vehicle.id).join(Booking).filter(
            Booking.status.in_(["pending", "confirmed"])
        ).count()
        
        availability = "Available" if active_services == 0 else "Booked"
        
        # Get assigned driver (permanent assignment)
        assigned_driver = None
        assigned_driver_id = None
        if vehicle.assigned_driver:
            assigned_driver = f"{vehicle.assigned_driver.firstName} {vehicle.assigned_driver.lastName}"
            assigned_driver_id = vehicle.assigned_driver.id
        
        return jsonify({
            "id": vehicle.id,
            "model": vehicle.model,
            "plateNumber": vehicle.plateNumber,
            "type": vehicle.type,
            "capacity": vehicle.capacity,
            "assignedDriver": assigned_driver,
            "assignedDriverId": assigned_driver_id,
            "availability": availability
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@vehicles_bp.route("/vehicles/<int:vehicle_id>", methods=["DELETE"])
def delete_vehicle(vehicle_id):
    try:
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        
        # Check if vehicle has active bookings by querying through Service model
        active_services = Service.query.filter_by(vehicle_id=vehicle_id).join(Booking).filter(
            Booking.status.in_(["pending", "confirmed"])
        ).count()
        
        if active_services > 0:
            return jsonify({"error": f"Cannot delete vehicle with {active_services} active bookings"}), 400
        
        db.session.delete(vehicle)
        db.session.commit()
        return jsonify({"message": "Vehicle deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# New endpoint to assign/unassign driver to vehicle
@vehicles_bp.route("/vehicles/<int:vehicle_id>/assign-driver", methods=["POST"])
def assign_driver_to_vehicle(vehicle_id):
    try:
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        data = request.get_json()
        
        driver_id = data.get("driverId")
        
        # If driver_id is None or empty, unassign the driver
        if not driver_id:
            vehicle.assigned_driver_id = None
        else:
            # Validate that the driver exists
            driver = Driver.query.get(driver_id)
            if not driver:
                return jsonify({"error": "Driver not found"}), 404
            
            # Check if driver is already assigned to another vehicle
            existing_assignment = Vehicle.query.filter_by(assigned_driver_id=driver_id).filter(Vehicle.id != vehicle_id).first()
            if existing_assignment:
                return jsonify({"error": f"Driver is already assigned to vehicle {existing_assignment.model} ({existing_assignment.plateNumber})"}), 400
            
            vehicle.assigned_driver_id = driver_id
        
        db.session.commit()
        
        # Get updated vehicle info
        assigned_driver = None
        assigned_driver_id = None
        if vehicle.assigned_driver:
            assigned_driver = f"{vehicle.assigned_driver.firstName} {vehicle.assigned_driver.lastName}"
            assigned_driver_id = vehicle.assigned_driver.id
        
        return jsonify({
            "message": "Driver assignment updated successfully",
            "vehicle": {
                "id": vehicle.id,
                "model": vehicle.model,
                "plateNumber": vehicle.plateNumber,
                "assignedDriver": assigned_driver,
                "assignedDriverId": assigned_driver_id
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# New endpoint to get available drivers (not assigned to any vehicle)
@vehicles_bp.route("/vehicles/available-drivers", methods=["GET"])
def get_available_drivers():
    try:
        # Get all drivers that are not assigned to any vehicle
        assigned_driver_ids = db.session.query(Vehicle.assigned_driver_id).filter(Vehicle.assigned_driver_id.isnot(None)).all()
        assigned_driver_ids = [id[0] for id in assigned_driver_ids]
        
        available_drivers = Driver.query.filter(~Driver.id.in_(assigned_driver_ids)).all()
        
        result = []
        for driver in available_drivers:
            result.append({
                "id": driver.id,
                "firstName": driver.firstName,
                "lastName": driver.lastName,
                "fullName": f"{driver.firstName} {driver.lastName}",
                "email": driver.email,
                "phone": driver.phone,
                "licenseNumber": driver.licenseNumber
            })
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# New endpoint to get vehicle schedule/calendar data
@vehicles_bp.route("/vehicles/<int:vehicle_id>/schedule", methods=["GET"])
def get_vehicle_schedule(vehicle_id):
    try:
        from datetime import datetime, timedelta
        
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        
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
        
        # Get all services for this vehicle within the date range
        services = Service.query.filter_by(vehicle_id=vehicle_id).join(Booking).filter(
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
                "driverInfo": f"{service.driver_ref.firstName} {service.driver_ref.lastName}" if service.driver_ref else None,
                "notes": service.notes
            })
        
        return jsonify({
            "vehicleId": vehicle_id,
            "vehicleName": f"{vehicle.model} - {vehicle.plateNumber}",
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "schedule": schedule_data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# New endpoint to get all vehicles with their current booking status
@vehicles_bp.route("/vehicles/status", methods=["GET"])
def get_vehicles_status():
    try:
        from datetime import datetime, date
        
        vehicles = Vehicle.query.all()
        result = []
        
        today = date.today()
        
        for vehicle in vehicles:
            # Check if vehicle has any active bookings today
            active_today = Service.query.filter_by(vehicle_id=vehicle.id).join(Booking).filter(
                Service.startDate <= today,
                Service.endDate >= today,
                Booking.status.in_(["pending", "confirmed"])
            ).first()
            
            # Get next upcoming booking
            next_booking = Service.query.filter_by(vehicle_id=vehicle.id).join(Booking).filter(
                Service.startDate > today,
                Booking.status.in_(["pending", "confirmed"])
            ).order_by(Service.startDate.asc()).first()
            
            status = "available"
            if active_today:
                status = "busy"
            elif next_booking:
                status = "scheduled"
            
            result.append({
                "id": vehicle.id,
                "model": vehicle.model,
                "plateNumber": vehicle.plateNumber,
                "type": vehicle.type,
                "capacity": vehicle.capacity,
                "assignedDriver": f"{vehicle.assigned_driver.firstName} {vehicle.assigned_driver.lastName}" if vehicle.assigned_driver else None,
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

