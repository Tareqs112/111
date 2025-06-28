from src.extensions import db
from datetime import datetime, date, time

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    passport_number = db.Column(db.String(50), nullable=True)
    license_number = db.Column(db.String(50), nullable=True)
    address = db.Column(db.Text)
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_amount = db.Column(db.Float, nullable=True, default=0.0)
    payment_status = db.Column(db.String(20), default="pending")
    payment_date = db.Column(db.Date, nullable=True)
    
    # Relationships
    company = db.relationship("Company", backref="clients", lazy=True)
    bookings = db.relationship("Booking", backref="client_ref", lazy=True)

class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text)
    contact_person = db.Column(db.String(100), nullable=True)
    logo_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Driver(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    license_number = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    assigned_vehicles = db.relationship("Vehicle", backref="assigned_driver", lazy=True)
    services = db.relationship("Service", backref="driver_ref", lazy=True)

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    model = db.Column(db.String(100), nullable=False)
    plate_number = db.Column(db.String(20), unique=True, nullable=False)
    type = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    assigned_driver_id = db.Column(db.Integer, db.ForeignKey("driver.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    services = db.relationship("Service", backref="vehicle_ref", lazy=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False)
    
    # Overall booking details
    overall_start_date = db.Column(db.Date, nullable=False)
    overall_end_date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    services = db.relationship("Service", backref="booking_ref", lazy=True, cascade="all, delete-orphan")
    invoices = db.relationship("Invoice", backref="booking", lazy=True, cascade="all, delete-orphan")

    @property
    def client(self):
        """Get client name for display"""
        if self.client_ref:
            return f"{self.client_ref.first_name} {self.client_ref.last_name}"
        return "Unknown Client"
    
    @property
    def total_cost(self):
        """Calculate total cost of all services in the booking"""
        return sum(service.total_cost for service in self.services)
    
    @property
    def total_selling_price(self):
        """Calculate total selling price of all services in the booking"""
        return sum(service.total_selling_price for service in self.services)
    
    @property
    def profit(self):
        """Calculate total profit of all services in the booking"""
        return self.total_selling_price - self.total_cost

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("booking.id"), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey("driver.id"), nullable=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicle.id"), nullable=True)
    
    service_type = db.Column(db.String(50), nullable=False)
    service_name = db.Column(db.String(200), nullable=False)
    
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    
    # New fields for tour timing (for notifications)
    start_time = db.Column(db.Time, nullable=True)
    end_time = db.Column(db.Time, nullable=True)
    
    cost_to_company = db.Column(db.Float, nullable=True, default=0.0)
    selling_price = db.Column(db.Float, nullable=True, default=0.0)
    
    hotel_name = db.Column(db.String(200), nullable=True)
    hotel_city = db.Column(db.String(100), nullable=True)
    room_type = db.Column(db.String(100), nullable=True)
    num_nights = db.Column(db.Integer, nullable=True)
    cost_per_night = db.Column(db.Float, nullable=True)
    selling_price_per_night = db.Column(db.Float, nullable=True)
    
    # Keep is_hourly and hours for vehicle rentals only
    is_hourly = db.Column(db.Boolean, default=False)
    hours = db.Column(db.Float, nullable=True)
    with_driver = db.Column(db.Boolean, nullable=True)

    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_accommodation(self):
        return self.service_type in ["Hotel", "Cabin"]
    
    @property
    def is_tour(self):
        return self.service_type == "Tour"
    
    @property
    def is_vehicle_rental(self):
        return self.service_type == "Vehicle"

    @property
    def total_cost(self):
        if self.is_accommodation and self.num_nights and self.cost_per_night:
            return self.num_nights * self.cost_per_night
        if self.is_vehicle_rental and self.is_hourly and self.hours and self.cost_to_company:
            return self.hours * self.cost_to_company
        return self.cost_to_company if self.cost_to_company is not None else 0.0
    
    @property
    def total_selling_price(self):
        if self.is_accommodation and self.num_nights and self.selling_price_per_night:
            return self.num_nights * self.selling_price_per_night
        if self.is_vehicle_rental and self.is_hourly and self.hours and self.selling_price:
            return self.hours * self.selling_price
        return self.selling_price if self.selling_price is not None else 0.0
    
    @property
    def profit(self):
        return self.total_selling_price - self.total_cost
    
    @property
    def start_date_time(self):
        """Get full start datetime for tours (combining date and time)"""
        if self.is_tour and self.start_time:
            return datetime.combine(self.start_date, self.start_time)
        return datetime.combine(self.start_date, time(0, 0))
    
    @property
    def end_date_time(self):
        """Get full end datetime for tours (combining date and time)"""
        if self.is_tour and self.end_time:
            return datetime.combine(self.end_date, self.end_time)
        return datetime.combine(self.end_date, time(23, 59))

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("booking.id"), nullable=False)
    invoice_type = db.Column(db.String(20), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="pending")
    invoice_date = db.Column(db.Date, nullable=False)
    pdf_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MonthlyCompanyInvoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"), nullable=False)
    invoice_month = db.Column(db.Integer, nullable=False)
    invoice_year = db.Column(db.Integer, nullable=False)
    
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    total_cost = db.Column(db.Float, nullable=False, default=0.0)
    total_profit = db.Column(db.Float, nullable=False, default=0.0)
    
    invoice_type = db.Column(db.String(20), nullable=False, default="partner_company")
    
    status = db.Column(db.String(20), default="pending")
    invoice_date = db.Column(db.Date, nullable=False)
    pdf_path = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    company = db.relationship("Company", backref="monthly_invoices", lazy=True)
    invoice_items = db.relationship("MonthlyInvoiceItem", backref="monthly_invoice", lazy=True, cascade="all, delete-orphan")
    
    @property
    def invoice_period(self):
        """Get formatted invoice period"""
        months = [
             "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
        ]
        return f"{months[self.invoice_month - 1]} {self.invoice_year}"

class MonthlyInvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    monthly_invoice_id = db.Column(db.Integer, db.ForeignKey("monthly_company_invoice.id"), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("service.id"), nullable=True)
    
    client_name = db.Column(db.String(200), nullable=False)
    arrival_date = db.Column(db.Date, nullable=True)
    
    service_type = db.Column(db.String(50), nullable=False)
    service_name = db.Column(db.String(200), nullable=False)
    service_date = db.Column(db.Date, nullable=False)
    
    cost_price = db.Column(db.Float, nullable=False, default=0.0)
    selling_price = db.Column(db.Float, nullable=False, default=0.0)
    profit = db.Column(db.Float, nullable=False, default=0.0)
    
    nights_or_hours = db.Column(db.String(50), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    hotel_or_tour_name = db.Column(db.String(200), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    service = db.relationship("Service", backref="monthly_invoice_items", lazy=True)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey("driver.id"), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey("booking.id"), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_sent = db.Column(db.Boolean, default=False)
    
    # Relationships
    driver = db.relationship("Driver", backref="notifications", lazy=True)
    booking = db.relationship("Booking", backref="notifications", lazy=True)

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


