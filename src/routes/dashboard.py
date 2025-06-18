import traceback
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta, date
from sqlalchemy import func
from src.models.database import db, Booking, Client, Driver, Vehicle, Invoice, Service

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/dashboard/summary", methods=["GET"])
def get_dashboard_summary():
    try:
        # Get current date
        today = date.today()
        
        # Get month filter from query parameters (default to current month)
        month = request.args.get("month", today.month)
        year = request.args.get("year", today.year)
        
        try:
            month = int(month)
            year = int(year)
            if month < 1 or month > 12:
                month = today.month
        except (ValueError, TypeError):
            month = today.month
            year = today.year
            
        # Create date range for the selected month
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)
        
        # Upcoming bookings (next 7 days)
        next_week = today + timedelta(days=7)
        upcoming_bookings_count = Booking.query.filter(
            Booking.overall_startDate >= today,
            Booking.overall_startDate <= next_week,
            Booking.status.in_(["pending", "confirmed"])
        ).count()
        
        # Total revenue for selected month - calculate in Python, not in SQL
        bookings_this_month = Booking.query.filter(
            Booking.overall_startDate >= month_start,
            Booking.overall_startDate <= month_end,
            Booking.status.in_(["confirmed", "completed"])
        ).all()
        
        # Calculate revenue and profit in Python after fetching the records
        total_revenue = sum(booking.totalSellingPrice for booking in bookings_this_month)
        total_profit = sum(booking.profit for booking in bookings_this_month)
        
        # Active clients
        active_clients = Client.query.count()
        
        return jsonify({
            "upcomingBookingsCount": upcoming_bookings_count,
            "totalRevenue": float(total_revenue),
            "totalProfit": float(total_profit),
            "activeClients": active_clients,
            "selectedMonth": month,
            "selectedYear": year
        })
    except Exception as e:
        traceback.print_exc() # Print full traceback to console
        return jsonify({"error": str(e)}), 500

@dashboard_bp.route("/dashboard/stats", methods=["GET"])
def get_detailed_stats():
    try:
        # Total counts
        total_clients = Client.query.count()
        total_drivers = Driver.query.count()
        total_vehicles = Vehicle.query.count()
        total_bookings = Booking.query.count()
        
        # Booking status breakdown
        booking_statuses = db.session.query(
            Booking.status,
            func.count(Booking.id)
        ).group_by(Booking.status).all()
        
        status_breakdown = {status: count for status, count in booking_statuses}
        
        # Service type breakdown
        service_types_query = db.session.query(
            Service.serviceType,
            func.count(Service.id)
        ).group_by(Service.serviceType).all()
        
        service_breakdown = {service_type: count for service_type, count in service_types_query}
        
        # Monthly revenue (last 6 months) - calculate in Python, not in SQL
        monthly_revenue = []
        for i in range(6):
            month_start = (date.today().replace(day=1) - timedelta(days=i*30)).replace(day=1)
            if i == 0:
                month_end = date.today()
            else:
                month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            # Get bookings for this month
            month_bookings = Booking.query.filter(
                Booking.overall_startDate >= month_start,
                Booking.overall_startDate <= month_end,
                Booking.status.in_(["confirmed", "completed"])
            ).all()
            
            # Calculate revenue in Python
            revenue = sum(booking.totalSellingPrice for booking in month_bookings)
            
            monthly_revenue.append({
                "month": month_start.strftime("%Y-%m"),
                "revenue": float(revenue)
            })
        
        monthly_revenue.reverse()  # Show oldest to newest
        
        return jsonify({
            "totalCounts": {
                "clients": total_clients,
                "drivers": total_drivers,
                "vehicles": total_vehicles,
                "bookings": total_bookings
            },
            "bookingStatusBreakdown": status_breakdown,
            "serviceTypeBreakdown": service_breakdown,
            "monthlyRevenue": monthly_revenue
        })
    except Exception as e:
        traceback.print_exc() # Print full traceback to console
        return jsonify({"error": str(e)}), 500

@dashboard_bp.route("/dashboard/upcoming-bookings", methods=["GET"])
def get_upcoming_bookings():
    try:
        # Get current date
        today = date.today()
        next_week = today + timedelta(days=7)
        
        # Debug: Print date range
        print(f"Fetching upcoming bookings from {today} to {next_week}")
        
        # Get upcoming bookings directly from the Booking table
        upcoming_bookings = Booking.query.filter(
            Booking.overall_startDate >= today,
            Booking.overall_startDate <= next_week,
            Booking.status.in_(["pending", "confirmed"])
        ).order_by(Booking.overall_startDate.asc()).all()
        
        # Debug: Print number of bookings found
        print(f"Found {len(upcoming_bookings)} upcoming bookings")
        
        upcoming_data = []
        for booking in upcoming_bookings:
            # Safely access client relationship with null check
            if not booking.client_ref:
                continue
                
            client_name = f"{booking.client_ref.firstName} {booking.client_ref.lastName}"
            
            # Debug: Print booking details
            print(f"Processing booking {booking.id} for client {client_name} on {booking.overall_startDate}")
            
            upcoming_data.append({
                "id": booking.id,
                "client": client_name,
                "startDate": booking.overall_startDate.isoformat() if booking.overall_startDate else None
            })
        
        # Debug: Print final data
        print(f"Returning {len(upcoming_data)} upcoming bookings")
        
        return jsonify(upcoming_data)
    except Exception as e:
        traceback.print_exc() # Print full traceback to console
        return jsonify({"error": str(e)}), 500

@dashboard_bp.route("/dashboard/todays-bookings", methods=["GET"])
def get_todays_bookings():
    try:
        today = date.today()
        
        # Get bookings where overall_startDate is today
        todays_bookings_overall = Booking.query.filter(
            Booking.overall_startDate == today,
            Booking.status.in_(["pending", "confirmed", "completed"])
        ).all()
        
        todays_data = []
        for booking in todays_bookings_overall:
            client_name = f"{booking.client_ref.firstName} {booking.client_ref.lastName}" if booking.client_ref else "Unknown Client"
            
            # Get service details for services within this booking that start today
            services_today = []
            for service in booking.services:
                if service.startDate and service.startDate == today:
                    services_today.append({
                        "serviceName": service.serviceName,
                        "serviceType": service.serviceType
                    })
            
            # Only add the booking to todays_data if it has services starting today
            if services_today:
                todays_data.append({
                    "id": booking.id,
                    "client": client_name,
                    "services": services_today
                })
        
        return jsonify(todays_data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@dashboard_bp.route("/dashboard/accommodation-stats", methods=["GET"])
def get_accommodation_stats():
    try:
        # Get accommodation bookings
        accommodation_services = Service.query.filter(
            Service.serviceType.in_(["Hotel", "Cabin"])
        ).all()
        
        # Calculate accommodation-specific stats
        total_nights = sum(service.numNights for service in accommodation_services if service.numNights)
        total_accommodation_revenue = sum(service.totalSellingPrice for service in accommodation_services)
        total_accommodation_cost = sum(service.totalCost for service in accommodation_services)
        total_accommodation_profit = total_accommodation_revenue - total_accommodation_cost
        
        # Group by hotel/cabin name
        accommodation_breakdown = {}
        for service in accommodation_services:
            if service.hotelName:
                if service.hotelName not in accommodation_breakdown:
                    accommodation_breakdown[service.hotelName] = {
                        "type": service.serviceType,
                        "bookings": 0,
                        "nights": 0,
                        "revenue": 0,
                        "profit": 0
                    }
                
                accommodation_breakdown[service.hotelName]["bookings"] += 1
                accommodation_breakdown[service.hotelName]["nights"] += service.numNights or 0
                accommodation_breakdown[service.hotelName]["revenue"] += service.totalSellingPrice
                accommodation_breakdown[service.hotelName]["profit"] += service.profit
        
        return jsonify({
            "totalNights": total_nights,
            "totalRevenue": float(total_accommodation_revenue),
            "totalCost": float(total_accommodation_cost),
            "totalProfit": float(total_accommodation_profit),
            "accommodationBreakdown": accommodation_breakdown
        })
    except Exception as e:
        traceback.print_exc() # Print full traceback to console
        return jsonify({"error": str(e)}), 500


