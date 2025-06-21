from flask import Blueprint, request, jsonify
from src.models.database import db, Company, Client, Booking, Service, MonthlyCompanyInvoice, MonthlyInvoiceItem
from datetime import datetime, date
import logging

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

# NEW FEATURE: Excel-like monthly invoice with payment status
@companies_bp.route("/companies/<int:company_id>/monthly-invoice-excel", methods=["GET"])
def get_company_monthly_invoice_excel(company_id):
    """Get Excel-like monthly invoice data with payment status for each client"""
    try:
        company = Company.query.get_or_404(company_id)
        
        # Get query parameters
        month = request.args.get('month', type=int, default=datetime.now().month)
        year = request.args.get('year', type=int, default=datetime.now().year)
        
        # Validate month and year
        if month < 1 or month > 12:
            month = datetime.now().month
        if year < 2020 or year > 2030:
            year = datetime.now().year
        
        # Get all clients for this company with bookings in the specified month/year
        clients = Client.query.filter_by(company_id=company_id).all()
        
        excel_data = []
        total_paid = 0
        total_due = 0
        total_amount = 0
        
        for client in clients:
            try:
                # Get bookings for this client in the specified period
                bookings = Booking.query.filter_by(client_id=client.id).filter(
                    db.extract('month', Booking.created_at) == month,
                    db.extract('year', Booking.created_at) == year
                ).all()
                
                if not bookings:
                    continue
                
                # Calculate client totals
                client_total = 0
                arrival_date = None
                
                for booking in bookings:
                    try:
                        if booking.overall_startDate:
                            if not arrival_date or booking.overall_startDate < arrival_date:
                                arrival_date = booking.overall_startDate
                        
                        # Safely get services
                        if hasattr(booking, 'services') and booking.services:
                            for service in booking.services:
                                try:
                                    if hasattr(service, 'totalSellingPrice') and service.totalSellingPrice:
                                        client_total += float(service.totalSellingPrice)
                                except (ValueError, TypeError, AttributeError) as e:
                                    logging.warning(f"Error processing service price for booking {booking.id}: {e}")
                                    continue
                    except Exception as e:
                        logging.warning(f"Error processing booking {booking.id}: {e}")
                        continue
                
                # Skip clients with no valid bookings
                if client_total <= 0:
                    continue
                
                # Check payment status (simplified for now)
                # In real implementation, you'd check against payment records
                payment_status = "pending"
                paid_amount = 0
                
                # Create safe client name
                client_name = "Unknown Client"
                try:
                    first_name = getattr(client, 'firstName', '') or ''
                    last_name = getattr(client, 'lastName', '') or ''
                    client_name = f"{first_name} {last_name}".strip()
                    if not client_name:
                        client_name = f"Client {client.id}"
                except Exception as e:
                    logging.warning(f"Error getting client name for client {client.id}: {e}")
                    client_name = f"Client {client.id}"
                
                excel_data.append({
                    "clientId": client.id,
                    "clientName": client_name,
                    "arrivalDate": arrival_date.isoformat() if arrival_date else None,
                    "totalAmount": float(client_total),
                    "paidAmount": float(paid_amount),
                    "dueAmount": float(client_total - paid_amount),
                    "paymentStatus": payment_status,
                    "email": getattr(client, 'email', '') or '',
                    "phone": getattr(client, 'phone', '') or ''
                })
                
                total_amount += client_total
                total_paid += paid_amount
                total_due += (client_total - paid_amount)
                
            except Exception as e:
                logging.error(f"Error processing client {client.id}: {e}")
                continue
        
        # Create month name safely
        try:
            month_name = datetime(year, month, 1).strftime("%B")
        except Exception as e:
            logging.warning(f"Error creating month name: {e}")
            month_name = f"Month {month}"
        
        return jsonify({
            "company": {
                "id": company.id,
                "name": getattr(company, 'name', '') or 'Unknown Company',
                "email": getattr(company, 'email', '') or '',
                "contactPerson": getattr(company, 'contactPerson', '') or ''
            },
            "period": {
                "month": month,
                "year": year,
                "monthName": month_name
            },
            "clients": excel_data,
            "summary": {
                "totalAmount": float(total_amount),
                "totalPaid": float(total_paid),
                "totalDue": float(total_due),
                "clientCount": len(excel_data)
            }
        })
    except Exception as e:
        logging.error(f"Error in get_company_monthly_invoice_excel: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

# NEW FEATURE: Add client directly from company context
@companies_bp.route("/companies/<int:company_id>/clients", methods=["POST"])
def add_client_to_company(company_id):
    """Add a new client directly to a company with total amount and arrival date"""
    try:
        company = Company.query.get_or_404(company_id)
        data = request.get_json()
        
        # Validate required fields
        required_fields = ["firstName", "lastName", "totalAmount", "arrivalDate"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"{field} is required"}), 400
        
        # Check if client email already exists (if provided)
        if data.get("email"):
            existing_client = Client.query.filter_by(email=data["email"]).first()
            if existing_client:
                return jsonify({"error": "Client with this email already exists"}), 400
        
        # Create new client
        client = Client(
            firstName=data["firstName"],
            lastName=data["lastName"],
            email=data.get("email"),
            phone=data.get("phone"),
            passportNumber=data.get("passportNumber"),
            licenseNumber=data.get("licenseNumber"),
            address=data.get("address"),
            company_id=company_id
        )
        
        db.session.add(client)
        db.session.flush()  # Get the client ID
        
        # Parse arrival date
        try:
            arrival_date = datetime.strptime(data["arrivalDate"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Invalid arrival date format. Use YYYY-MM-DD"}), 400
        
        # Create a booking for this client
        booking = Booking(
            client_id=client.id,
            overall_startDate=arrival_date,
            overall_endDate=arrival_date,  # Can be updated later
            notes=data.get("notes", "Added directly from company"),
            status="confirmed"
        )
        
        db.session.add(booking)
        db.session.flush()  # Get the booking ID
        
        # Create a service entry for the total amount
        service = Service(
            booking_id=booking.id,
            serviceType="Package",  # Generic service type
            serviceName=data.get("serviceName", "Service Package"),
            startDate=arrival_date,
            endDate=arrival_date,
            costToCompany=data.get("costToCompany", 0),
            sellingPrice=data["totalAmount"],
            notes=data.get("serviceNotes", "Added directly from company")
        )
        
        db.session.add(service)
        db.session.commit()
        
        return jsonify({
            "message": "Client added successfully",
            "client": {
                "id": client.id,
                "firstName": client.firstName,
                "lastName": client.lastName,
                "email": client.email,
                "phone": client.phone,
                "totalAmount": float(service.totalSellingPrice),
                "arrivalDate": arrival_date.isoformat(),
                "bookingId": booking.id,
                "serviceId": service.id
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error adding client to company: {e}")
        return jsonify({"error": str(e)}), 500

# NEW FEATURE: Update payment status for a client
@companies_bp.route("/companies/<int:company_id>/clients/<int:client_id>/payment", methods=["PUT"])
def update_client_payment_status(company_id, client_id):
    """Update payment status for a specific client"""
    try:
        company = Company.query.get_or_404(company_id)
        client = Client.query.filter_by(id=client_id, company_id=company_id).first_or_404()
        
        data = request.get_json()
        paid_amount = data.get("paidAmount", 0)
        payment_status = data.get("paymentStatus", "pending")
        payment_date = data.get("paymentDate")
        
        # Here you would update your payment tracking system
        # For now, we'll just return success
        # In a real implementation, you'd have a Payment model to track this
        
        return jsonify({
            "message": "Payment status updated successfully",
            "clientId": client_id,
            "paidAmount": paid_amount,
            "paymentStatus": payment_status,
            "paymentDate": payment_date
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

