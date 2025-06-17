from flask import Blueprint, request, jsonify
from src.models.database import db, Driver, Vehicle, Booking # Moved Booking import to top

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
            
            result.append({
                "id": driver.id,
                "firstName": driver.firstName,
                "lastName": driver.lastName,
                "email": driver.email,
                "phone": driver.phone,
                "licenseNumber": driver.licenseNumber,
                "assignedVehicles": assigned_vehicles
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



