from flask import Blueprint, request, jsonify
from src.models.database import db, Company, Client, Booking, Service
from datetime import datetime, date

companies_bp = Blueprint("companies", __name__)

@companies_bp.route("/companies", methods=["GET"])
def get_companies():
    try:
        companies = Company.query.all()
        result = []
        for company in companies:
            client_count = Client.query.filter_by(company_id=company.id).count()
            result.append({
                "id": company.id,
                "name": company.name,
                "contactPerson": company.contactPerson,
                "email": company.email,
                "phone": company.phone,
                "logoPath": company.logoPath,
                "clientCount": client_count
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@companies_bp.route("/companies/<int:company_id>", methods=["GET"])
def get_company(company_id):
    try:
        company = Company.query.get_or_404(company_id)
        client_count = Client.query.filter_by(company_id=company.id).count()
        return jsonify({
            "id": company.id,
            "name": company.name,
            "contactPerson": company.contactPerson,
            "email": company.email,
            "phone": company.phone,
            "logoPath": company.logoPath,
            "clientCount": client_count
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@companies_bp.route("/companies", methods=["POST"])
def add_company():
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get("name") or not data.get("contactPerson") or not data.get("email"):
            return jsonify({"error": "Company name, contact person, and email are required"}), 400
        
        # Check if company name already exists
        existing_company = Company.query.filter_by(name=data["name"]).first()
        if existing_company:
            return jsonify({"error": "Company name already exists"}), 400
        
        company = Company(
            name=data["name"],
            contactPerson=data["contactPerson"],
            email=data["email"],
            phone=data.get("phone"),
            logoPath=data.get("logoPath")
        )
        
        db.session.add(company)
        db.session.commit()
        
        return jsonify({
            "id": company.id,
            "name": company.name,
            "contactPerson": company.contactPerson,
            "email": company.email,
            "phone": company.phone,
            "logoPath": company.logoPath,
            "clientCount": 0
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@companies_bp.route("/companies/<int:company_id>", methods=["PUT"])
def update_company(company_id):
    try:
        company = Company.query.get_or_404(company_id)
        data = request.get_json()
        
        # Validate required fields
        if not data.get("name") or not data.get("contactPerson") or not data.get("email"):
            return jsonify({"error": "Company name, contact person, and email are required"}), 400
        
        # Check if company name already exists (excluding current company)
        existing_company = Company.query.filter(Company.name == data["name"], Company.id != company_id).first()
        if existing_company:
            return jsonify({"error": "Company name already exists"}), 400
        
        company.name = data["name"]
        company.contactPerson = data["contactPerson"]
        company.email = data["email"]
        company.phone = data.get("phone")
        company.logoPath = data.get("logoPath")
        
        db.session.commit()
        
        client_count = Client.query.filter_by(company_id=company.id).count()
        return jsonify({
            "id": company.id,
            "name": company.name,
            "contactPerson": company.contactPerson,
            "email": company.email,
            "phone": company.phone,
            "logoPath": company.logoPath,
            "clientCount": client_count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@companies_bp.route("/companies/<int:company_id>", methods=["DELETE"])
def delete_company(company_id):
    try:
        company = Company.query.get_or_404(company_id)
        
        # Check if company has associated clients
        client_count = Client.query.filter_by(company_id=company.id).count()
        if client_count > 0:
            return jsonify({"error": f"Cannot delete company with {client_count} associated clients"}), 400
        
        db.session.delete(company)
        db.session.commit()
        return jsonify({"message": "Company deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@companies_bp.route("/companies/<int:company_id>/clients", methods=["GET"])
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

@companies_bp.route("/companies/<int:company_id>/clients/detailed", methods=["GET"])
def get_company_clients_detailed(company_id):
    """Get detailed client information with arrival dates and service breakdown for monthly invoicing"""
    try:
        company = Company.query.get_or_404(company_id)
        
        # Get query parameters for date filtering
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        
        clients = Client.query.filter_by(company_id=company_id).all()
        
        result = []
        total_company_revenue = 0
        
        for client in clients:
            # Get all bookings for this client
            bookings_query = Booking.query.filter_by(client_id=client.id)
            
            # Filter by month/year if provided
            if month and year:
                bookings_query = bookings_query.filter(
                    db.extract('month', Booking.created_at) == month,
                    db.extract('year', Booking.created_at) == year
                )
            
            bookings = bookings_query.all()
            
            if not bookings:
                continue  # Skip clients with no bookings in the specified period
            
            client_services = []
            client_total_selling_price = 0
            
            # Get the earliest booking date as arrival date
            arrival_date = min(booking.overall_startDate for booking in bookings)
            
            for booking in bookings:
                for service in booking.services:
                    # Categorize services
                    service_category = "جولات وإيجار سيارة"
                    if service.serviceType == "Hotel":
                        service_category = "فنادق"
                    
                    service_data = {
                        "id": service.id,
                        "bookingId": booking.id,
                        "serviceName": service.serviceName,
                        "serviceType": service.serviceType,
                        "serviceCategory": service_category,
                        "startDate": service.startDate.isoformat(),
                        "endDate": service.endDate.isoformat(),
                        "totalSellingPrice": float(service.totalSellingPrice),
                        "totalCost": float(service.totalCost),
                        "profit": float(service.profit),
                        "nights": service.numNights if service.serviceType == "Hotel" else None,
                        "hours": service.hours if service.is_hourly else None,
                        "hotelName": service.hotelName if service.serviceType == "Hotel" else None,
                        "city": "IST"  # Default city, can be made dynamic
                    }
                    client_services.append(service_data)
                    client_total_selling_price += service.totalSellingPrice
            
            if client_services:  # Only include clients with services
                result.append({
                    "clientId": client.id,
                    "clientName": f"{client.firstName} {client.lastName}",
                    "email": client.email,
                    "arrivalDate": arrival_date.isoformat(),
                    "services": client_services,
                    "totalSellingPrice": client_total_selling_price
                })
                total_company_revenue += client_total_selling_price
        
        return jsonify({
            "company": {
                "id": company.id,
                "name": company.name,
                "email": company.email,
                "contactPerson": company.contactPerson
            },
            "clients": result,
            "totalRevenue": total_company_revenue,
            "period": {
                "month": month,
                "year": year
            } if month and year else None
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

