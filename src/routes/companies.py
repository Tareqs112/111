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
        month = request.args.get("month", type=int)
        year = request.args.get("year", type=int)
        
        clients = Client.query.filter_by(company_id=company_id).all()
        
        result = []
        total_company_revenue = 0
        
        for client in clients:
            # Get all bookings for this client
            bookings_query = Booking.query.filter_by(client_id=client.id)
            
            # Filter by month/year if provided
            if month and year:
                bookings_query = bookings_query.filter(
                    db.extract("month", Booking.created_at) == month,
                    db.extract("year", Booking.created_at) == year
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
        month = request.args.get("month", type=int, default=datetime.now().month)
        year = request.args.get("year", type=int, default=datetime.now().year)
        
        # Validate month and year
        if month < 1 or month > 12:
            month = datetime.now().month
        if year < 2020 or year > 2030:
            year = datetime.now().year
        
        # FIXED: Get only clients who have bookings with arrival dates in the specified month/year
        # Use overall_startDate (arrival date) instead of created_at
        bookings_in_period = db.session.query(Booking).join(Client).filter(
            Client.company_id == company_id,
            Booking.overall_startDate.isnot(None),  # Ensure arrival date exists
            db.extract("month", Booking.overall_startDate) == month,
            db.extract("year", Booking.overall_startDate) == year
        ).all()
        
        # Get unique client IDs from these bookings
        client_ids_with_bookings = list(set([booking.client_id for booking in bookings_in_period]))
        
        if not client_ids_with_bookings:
            # No bookings in this period
            return jsonify({
                "company": {
                    "id": company.id,
                    "name": getattr(company, "name", "") or "Unknown Company",
                    "email": getattr(company, "email", "") or "",
                    "contactPerson": getattr(company, "contactPerson", "") or ""
                },
                "period": {
                    "month": month,
                    "year": year,
                    "monthName": datetime(year, month, 1).strftime("%B")
                },
                "clients": [],
                "summary": {
                    "totalAmount": 0.0,
                    "totalPaid": 0.0,
                    "totalDue": 0.0,
                    "clientCount": 0
                }
            })
        
        # Get clients who have bookings in this period
        clients = Client.query.filter(Client.id.in_(client_ids_with_bookings)).all()
        
        excel_data = []
        total_paid = 0
        total_due = 0
        total_amount = 0
        
        for client in clients:
            try:
                # Get bookings for this client in the specified period only
                client_bookings = [b for b in bookings_in_period if b.client_id == client.id]
                
                if not client_bookings:
                    continue
                
                # Calculate client totals from bookings in this period only
                client_total = 0
                arrival_date = None
                
                for booking in client_bookings:
                    try:
                        # Get the earliest arrival date from bookings in this period
                        if booking.overall_startDate:
                            if not arrival_date or booking.overall_startDate < arrival_date:
                                arrival_date = booking.overall_startDate
                        
                        # Safely get services for this booking
                        if hasattr(booking, "services") and booking.services:
                            for service in booking.services:
                                try:
                                    if hasattr(service, "totalSellingPrice") and service.totalSellingPrice:
                                        client_total += float(service.totalSellingPrice)
                                except (ValueError, TypeError, AttributeError) as e:
                                    logging.warning(f"Error processing service price for booking {booking.id}: {e}")
                                    continue
                    except Exception as e:
                        logging.warning(f"Error processing booking {booking.id}: {e}")
                        continue
                
                # Skip clients with no valid bookings or zero amount
                if client_total <= 0:
                    continue
                
                # Get payment status (check if client has payment tracking fields)
                payment_status = "pending"
                paid_amount = 0
                
                # Check if client has payment tracking fields
                if hasattr(client, "paymentStatus"):
                    payment_status = getattr(client, "paymentStatus", "pending") or "pending"
                if hasattr(client, "paidAmount"):
                    paid_amount = float(getattr(client, "paidAmount", 0) or 0)
                
                # Create safe client name
                client_name = f"{getattr(client, 'firstName', '') or ''} {getattr(client, 'lastName', '') or ''}".strip()
                if not client_name:
                    client_name = f"Client {client.id}"
                
                # Calculate due amount
                due_amount = max(0, client_total - paid_amount)
                
                excel_data.append({
                    "clientId": client.id,
                    "clientName": client_name,
                    "email": getattr(client, "email", "") or "",
                    "arrivalDate": arrival_date.isoformat() if arrival_date else "",
                    "totalAmount": client_total,
                    "paidAmount": paid_amount,
                    "dueAmount": due_amount,
                    "paymentStatus": payment_status
                })
                
                # Update totals
                total_amount += client_total
                total_paid += paid_amount
                total_due += due_amount
                
            except Exception as e:
                logging.warning(f"Error processing client {client.id}: {e}")
                continue
        
        return jsonify({
            "company": {
                "id": company.id,
                "name": getattr(company, "name", "") or "Unknown Company",
                "email": getattr(company, "email", "") or "",
                "contactPerson": getattr(company, "contactPerson", "") or ""
            },
            "period": {
                "month": month,
                "year": year,
                "monthName": datetime(year, month, 1).strftime("%B")
            },
            "clients": excel_data,
            "summary": {
                "totalAmount": round(total_amount, 2),
                "totalPaid": round(total_paid, 2),
                "totalDue": round(total_due, 2),
                "clientCount": len(excel_data)
            }
        })
    except Exception as e:
        logging.error(f"Error in get_company_monthly_invoice_excel: {e}")
        return jsonify({"error": str(e)}), 500

# NEW: Endpoint to update client payment status
@companies_bp.route("/companies/<int:company_id>/clients/<int:client_id>/payment", methods=["PUT"])
def update_client_payment_status(company_id, client_id):
    """Update payment status for a specific client"""
    try:
        # Verify company exists
        company = Company.query.get_or_404(company_id)
        
        # Verify client belongs to this company
        client = Client.query.filter_by(id=client_id, company_id=company_id).first()
        if not client:
            return jsonify({"error": "Client not found or does not belong to this company"}), 404
        
        data = request.get_json()
        
        # Validate input data
        paid_amount = data.get("paidAmount", 0)
        payment_status = data.get("paymentStatus", "pending")
        payment_date = data.get("paymentDate")
        
        try:
            paid_amount = float(paid_amount) if paid_amount is not None else 0
        except (ValueError, TypeError):
            paid_amount = 0
        
        # Update client payment information
        # Note: These fields might need to be added to the Client model if they don't exist
        if hasattr(client, "paidAmount"):
            client.paidAmount = paid_amount
        if hasattr(client, "paymentStatus"):
            client.paymentStatus = payment_status
        if hasattr(client, "paymentDate") and payment_date:
            try:
                client.paymentDate = datetime.strptime(payment_date, "%Y-%m-%d").date()
            except ValueError:
                pass  # Invalid date format, skip
        
        # Commit the changes to the database
        db.session.commit()
        
        return jsonify({
            "message": "Payment status updated successfully",
            "clientId": client.id,
            "paidAmount": paid_amount,
            "paymentStatus": payment_status
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating payment status: {e}")
        return jsonify({"error": str(e)}), 500

# NEW: Get companies with updated counts including payment information
@companies_bp.route("/companies/with-counts", methods=["GET"])
def get_companies_with_counts():
    """Get all companies with updated client counts and payment summaries"""
    try:
        companies = Company.query.all()
        result = []
        
        for company in companies:
            # Get basic client count
            client_count = Client.query.filter_by(company_id=company.id).count()
            
            # Get payment summary for current month
            current_month = datetime.now().month
            current_year = datetime.now().year
            
            # Get clients with bookings in current month
            bookings_current_month = db.session.query(Booking).join(Client).filter(
                Client.company_id == company.id,
                Booking.overall_startDate.isnot(None),
                db.extract("month", Booking.overall_startDate) == current_month,
                db.extract("year", Booking.overall_startDate) == current_year
            ).all()
            
            monthly_revenue = 0
            monthly_paid = 0
            
            client_ids_current_month = list(set([booking.client_id for booking in bookings_current_month]))
            
            for client_id in client_ids_current_month:
                client = Client.query.get(client_id)
                if client:
                    # Calculate client total for current month
                    client_bookings = [b for b in bookings_current_month if b.client_id == client_id]
                    client_total = 0
                    
                    for booking in client_bookings:
                        if hasattr(booking, "services") and booking.services:
                            for service in booking.services:
                                if hasattr(service, "totalSellingPrice") and service.totalSellingPrice:
                                    client_total += float(service.totalSellingPrice)
                    
                    monthly_revenue += client_total
                    
                    # Get paid amount
                    if hasattr(client, "paidAmount"):
                        paid_amount = float(getattr(client, "paidAmount", 0) or 0)
                        monthly_paid += paid_amount
            
            result.append({
                "id": company.id,
                "name": company.name,
                "contactPerson": company.contactPerson,
                "email": company.email,
                "phone": company.phone,
                "logoPath": company.logoPath,
                "clientCount": client_count,
                "monthlyRevenue": round(monthly_revenue, 2),
                "monthlyPaid": round(monthly_paid, 2),
                "monthlyDue": round(monthly_revenue - monthly_paid, 2)
            })
        
        return jsonify(result)
    except Exception as e:
        logging.error(f"Error in get_companies_with_counts: {e}")
        return jsonify({"error": str(e)}), 500

# NEW: Simplified endpoint for company clients
@companies_bp.route("/companies/<int:company_id>/clients/simple", methods=["GET"])
def get_company_clients_simple(company_id):
    """Get simplified client list for a company"""
    try:
        company = Company.query.get_or_404(company_id)
        
        # Get query parameters for date filtering
        month = request.args.get("month", type=int)
        year = request.args.get("year", type=int)
        
        if month and year:
            # Get clients with bookings in specified period
            bookings_in_period = db.session.query(Booking).join(Client).filter(
                Client.company_id == company_id,
                Booking.overall_startDate.isnot(None),
                db.extract("month", Booking.overall_startDate) == month,
                db.extract("year", Booking.overall_startDate) == year
            ).all()
            
            client_ids = list(set([booking.client_id for booking in bookings_in_period]))
            clients = Client.query.filter(Client.id.in_(client_ids)).all() if client_ids else []
        else:
            # Get all clients for the company
            clients = Client.query.filter_by(company_id=company_id).all()
        
        result = []
        for client in clients:
            client_name = f"{getattr(client, 'firstName', '') or ''} {getattr(client, 'lastName', '') or ''}".strip()
            if not client_name:
                client_name = f"Client {client.id}"
            
            # Get payment info
            paid_amount = 0
            payment_status = "pending"
            
            if hasattr(client, "paidAmount"):
                paid_amount = float(getattr(client, "paidAmount", 0) or 0)
            if hasattr(client, "paymentStatus"):
                payment_status = getattr(client, "paymentStatus", "pending") or "pending"
            
            result.append({
                "clientId": client.id,
                "clientName": client_name,
                "email": getattr(client, "email", "") or "",
                "paidAmount": paid_amount,
                "paymentStatus": payment_status
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
        logging.error(f"Error in get_company_clients_simple: {e}")
        return jsonify({"error": str(e)}), 500

