from flask import Blueprint, request, jsonify
from src.models.database import db, Client, Company, Booking, Service

clients_bp = Blueprint("clients", __name__)

@clients_bp.route("/clients", methods=["GET"])
def get_clients():
    try:
        clients = Client.query.all()
        result = []
        for client in clients:
            company_name = client.company.name if client.company else "No Company"
            
            # Get booking count for this client
            booking_count = Booking.query.filter_by(client_id=client.id).count()
            
            result.append({
                "id": client.id,
                "firstName": client.firstName,
                "lastName": client.lastName,
                "email": client.email,
                "phone": client.phone,
                "passportNumber": client.passportNumber if hasattr(client, 'passportNumber') else "",
                "licenseNumber": client.licenseNumber if hasattr(client, 'licenseNumber') else "",
                "company": company_name,
                "companyId": client.company_id,
                "bookingCount": booking_count
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@clients_bp.route("/clients/<int:client_id>", methods=["GET"])
def get_client(client_id):
    try:
        client = Client.query.get_or_404(client_id)
        company_name = client.company.name if client.company else "No Company"
        
        # Get booking count for this client
        booking_count = Booking.query.filter_by(client_id=client.id).count()
        
        return jsonify({
            "id": client.id,
            "firstName": client.firstName,
            "lastName": client.lastName,
            "email": client.email,
            "phone": client.phone,
            "passportNumber": client.passportNumber if hasattr(client, 'passportNumber') else "",
            "licenseNumber": client.licenseNumber if hasattr(client, 'licenseNumber') else "",
            "company": company_name,
            "companyId": client.company_id,
            "bookingCount": booking_count
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@clients_bp.route("/clients/<int:client_id>/bookings", methods=["GET"])
def get_client_bookings(client_id):
    try:
        client = Client.query.get_or_404(client_id)
        
        # Get all bookings for this client, ordered by date (newest first)
        bookings = Booking.query.filter_by(client_id=client_id).order_by(Booking.created_at.desc()).all()
        
        # Categorize bookings by service type
        hotels = []
        tours = []
        vehicle_rentals = []
        
        total_revenue = 0
        total_profit = 0
        
        for booking in bookings:
            for service in booking.services:
                # Get driver name if assigned
                driver_name = None
                if service.driver_ref:
                    driver_name = f"{service.driver_ref.firstName} {service.driver_ref.lastName}"
                
                # Get vehicle info if assigned
                vehicle_info = None
                if service.vehicle_ref:
                    vehicle_info = f"{service.vehicle_ref.model} - {service.vehicle_ref.plateNumber}"
                
                service_data = {
                    "id": service.id,
                    "bookingId": booking.id,
                    "serviceName": service.serviceName,
                    "startDate": service.startDate.isoformat(),
                    "endDate": service.endDate.isoformat(),
                    "totalCost": float(service.totalCost),
                    "totalSellingPrice": float(service.totalSellingPrice),
                    "profit": float(service.profit),
                    "status": booking.status,
                    "notes": service.notes,
                    "driverName": driver_name,
                    "vehicleInfo": vehicle_info,
                    "createdAt": booking.created_at.isoformat()
                }
                
                if service.serviceType == "Hotel":
                    service_data.update({
                        "hotelName": service.hotelName,
                        "roomType": service.roomType,
                        "numNights": service.numNights,
                        "costPerNight": float(service.costPerNight) if service.costPerNight else 0,
                        "sellingPricePerNight": float(service.sellingPricePerNight) if service.sellingPricePerNight else 0
                    })
                    hotels.append(service_data)
                elif service.serviceType == "Tour":
                    service_data.update({
                        "is_hourly": service.is_hourly,
                        "hours": service.hours
                    })
                    tours.append(service_data)
                elif service.serviceType == "Vehicle":
                    service_data.update({
                        "with_driver": service.with_driver,
                        "is_hourly": service.is_hourly,
                        "hours": service.hours
                    })
                    vehicle_rentals.append(service_data)
                
                total_revenue += service.totalSellingPrice
                total_profit += service.profit
        
        return jsonify({
            "client": {
                "id": client.id,
                "firstName": client.firstName,
                "lastName": client.lastName,
                "email": client.email,
                "phone": client.phone,
                "company": client.company.name if client.company else "No Company"
            },
            "bookings": {
                "hotels": hotels,
                "tours": tours,
                "vehicle_rentals": vehicle_rentals
            },
            "totalBookings": len(bookings),
            "totalRevenue": total_revenue,
            "totalProfit": total_profit
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@clients_bp.route("/clients", methods=["POST"])
def add_client():
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get("firstName") or not data.get("lastName"):
            return jsonify({"error": "First name and last name are required"}), 400
        
        # Email is not required anymore
        email = data.get("email", "")
        
        # Check if email already exists (only if email is provided)
        if email:
            existing_client = Client.query.filter_by(email=email).first()
            if existing_client:
                return jsonify({"error": "Email already exists"}), 400
        
        client = Client(
            firstName=data["firstName"],
            lastName=data["lastName"],
            email=email,
            phone=data.get("phone", ""),
            passportNumber=data.get("passportNumber", ""),
            licenseNumber=data.get("licenseNumber", ""),
            company_id=data.get("companyId") if data.get("companyId") else None
        )
        
        db.session.add(client)
        db.session.commit()
        
        company_name = client.company.name if client.company else "No Company"
        return jsonify({
            "id": client.id,
            "firstName": client.firstName,
            "lastName": client.lastName,
            "email": client.email,
            "phone": client.phone,
            "passportNumber": client.passportNumber if hasattr(client, 'passportNumber') else "",
            "licenseNumber": client.licenseNumber if hasattr(client, 'licenseNumber') else "",
            "company": company_name,
            "companyId": client.company_id,
            "bookingCount": 0
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@clients_bp.route("/clients/<int:client_id>", methods=["PUT"])
def update_client(client_id):
    try:
        client = Client.query.get_or_404(client_id)
        data = request.get_json()
        
        # Validate required fields
        if not data.get("firstName") or not data.get("lastName"):
            return jsonify({"error": "First name and last name are required"}), 400
        
        email = data.get("email", "")
        
        # Check if email already exists (excluding current client, only if email is provided)
        if email:
            existing_client = Client.query.filter(Client.email == email, Client.id != client_id).first()
            if existing_client:
                return jsonify({"error": "Email already exists"}), 400
        
        client.firstName = data["firstName"]
        client.lastName = data["lastName"]
        client.email = email
        client.phone = data.get("phone", "")
        if hasattr(client, 'passportNumber'):
            client.passportNumber = data.get("passportNumber", "")
        if hasattr(client, 'licenseNumber'):
            client.licenseNumber = data.get("licenseNumber", "")
        client.company_id = data.get("companyId") if data.get("companyId") else None
        
        db.session.commit()
        
        company_name = client.company.name if client.company else "No Company"
        booking_count = Booking.query.filter_by(client_id=client.id).count()
        
        return jsonify({
            "id": client.id,
            "firstName": client.firstName,
            "lastName": client.lastName,
            "email": client.email,
            "phone": client.phone,
            "passportNumber": client.passportNumber if hasattr(client, 'passportNumber') else "",
            "licenseNumber": client.licenseNumber if hasattr(client, 'licenseNumber') else "",
            "company": company_name,
            "companyId": client.company_id,
            "bookingCount": booking_count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@clients_bp.route("/clients/<int:client_id>", methods=["DELETE"])
def delete_client(client_id):
    try:
        client = Client.query.get_or_404(client_id)
        
        # Check if client has any bookings
        booking_count = Booking.query.filter_by(client_id=client_id).count()
        if booking_count > 0:
            return jsonify({"error": f"Cannot delete client with {booking_count} existing bookings"}), 400
        
        db.session.delete(client)
        db.session.commit()
        return jsonify({"message": "Client deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@clients_bp.route("/companies/<int:company_id>/clients", methods=["GET"])
def get_company_clients(company_id):
    """Get all clients associated with a specific company along with their service details"""
    try:
        company = Company.query.get_or_404(company_id)
        clients = Client.query.filter_by(company_id=company_id).all()
        
        result = []
        for client in clients:
            # Get all bookings for this client
            bookings = Booking.query.filter_by(client_id=client.id).all()
            
            client_services = []
            total_cost = 0
            total_selling_price = 0
            
            for booking in bookings:
                for service in booking.services:
                    service_data = {
                        "serviceName": service.serviceName,
                        "serviceType": service.serviceType,
                        "startDate": service.startDate.isoformat(),
                        "totalSellingPrice": float(service.totalSellingPrice)
                    }
                    client_services.append(service_data)
                    total_selling_price += service.totalSellingPrice
            
            result.append({
                "clientId": client.id,
                "clientName": f"{client.firstName} {client.lastName}",
                "email": client.email,
                "services": client_services,
                "totalAmount": total_selling_price
            })
        
        return jsonify({
            "company": {
                "id": company.id,
                "name": company.name,
                "email": company.email,
                "contactPerson": company.contactPerson
            },
            "clients": result
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500



