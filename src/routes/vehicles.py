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
            
            # Get assigned driver (permanent assignment)
            assigned_driver = None
            assigned_driver_id = None
            if vehicle.assigned_driver:
                assigned_driver = f"{vehicle.assigned_driver.firstName} {vehicle.assigned_driver.lastName}"
                assigned_driver_id = vehicle.assigned_driver.id
            
            result.append({
                "id": vehicle.id,
                "model": vehicle.model,
                "plateNumber": vehicle.plateNumber,
                "type": vehicle.type,
                "capacity": vehicle.capacity,
                "assignedDriver": assigned_driver,
                "assignedDriverId": assigned_driver_id,
                "availability": availability
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


