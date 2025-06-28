from src.extensions import db
from datetime import datetime, date, time

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstName = db.Column(db.String(100), nullable=False)
    lastName = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True)  # Made nullable
    phone = db.Column(db.String(20), nullable=True)  # Made nullable
    passportNumber = db.Column(db.String(50), nullable=True)  # New field
    licenseNumber = db.Column(db.String(50), nullable=True)  # New field
    address = db.Column(db.Text)
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_amount = db.Column(db.Float, nullable=True, default=0.0)
    payment_status = db.Column(db.String(20), default="pending")  # pending, paid, overdue
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
    contactPerson = db.Column(db.String(100), nullable=True)
    logoPath = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Driver(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstName = db.Column(db.String(100), nullable=False)
    lastName = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    licenseNumber = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    assigned_vehicles = db.relationship("Vehicle", backref="assigned_driver", lazy=True)
    services = db.relationship("Service", backref="driver_ref", lazy=True)

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    model = db.Column(db.String(100), nullable=False)
    plateNumber = db.Column(db.String(20), unique=True, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # Sedan, SUV, Van, Bus, etc.
    capacity = db.Column(db.Integer, nullable=False)
    assigned_driver_id = db.Column(db.Integer, db.ForeignKey("driver.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    services = db.relationship("Service", backref="vehicle_ref", lazy=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False)
    
    # Overall booking details
    overall_startDate = db.Column(db.Date, nullable=False)
    overall_endDate = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default="pending")  # pending, confirmed, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    services = db.relationship("Service", backref="booking_ref", lazy=True, cascade="all, delete-orphan")
    invoices = db.relationship("Invoice", backref="booking", lazy=True, cascade="all, delete-orphan")

    @property
    def client(self):
        """Get client name for display"""
        if self.client_ref:
            return f"{self.client_ref.firstName} {self.client_ref.lastName}"
        return "Unknown Client"
    
    @property
    def totalCost(self):
        """Calculate total cost of all services in the booking"""
        return sum(service.totalCost for service in self.services)
    
    @property
    def totalSellingPrice(self):
        """Calculate total selling price of all services in the booking"""
        return sum(service.totalSellingPrice for service in self.services)
    
    @property
    def profit(self):
        """Calculate total profit of all services in the booking"""
        return self.totalSellingPrice - self.totalCost

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("booking.id"), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey("driver.id"), nullable=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicle.id"), nullable=True)
    
    serviceType = db.Column(db.String(50), nullable=False)  # Tour, Vehicle, Hotel
    serviceName = db.Column(db.String(200), nullable=False)
    
    startDate = db.Column(db.Date, nullable=False)
    endDate = db.Column(db.Date, nullable=False)
    
    # New fields for tour timing (for notifications)
    startTime = db.Column(db.Time, nullable=True)  # Start time for tours
    endTime = db.Column(db.Time, nullable=True)    # End time for tours
    
    costToCompany = db.Column(db.Float, nullable=True, default=0.0)
    sellingPrice = db.Column(db.Float, nullable=True, default=0.0)
    
    hotelName = db.Column(db.String(200), nullable=True)
    hotelCity = db.Column(db.String(100), nullable=True)  # New field for hotel city
    roomType = db.Column(db.String(100), nullable=True)
    numNights = db.Column(db.Integer, nullable=True)
    costPerNight = db.Column(db.Float, nullable=True)
    sellingPricePerNight = db.Column(db.Float, nullable=True)
    
    # Keep is_hourly and hours for vehicle rentals only
    is_hourly = db.Column(db.Boolean, default=False) # For vehicle rentals by hour
    hours = db.Column(db.Float, nullable=True) # Number of hours for vehicle rentals
    with_driver = db.Column(db.Boolean, nullable=True) # For car rental with/without driver

    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def isAccommodation(self):
        return self.serviceType in ["Hotel", "Cabin"]
    
    @property
    def isTour(self):
        return self.serviceType == "Tour"
    
    @property
    def isVehicleRental(self):
        return self.serviceType == "Vehicle"

    @property
    def totalCost(self):
        if self.isAccommodation and self.numNights and self.costPerNight:
            return self.numNights * self.costPerNight
        if self.isVehicleRental and self.is_hourly and self.hours and self.costToCompany:
            return self.hours * self.costToCompany
        return self.costToCompany if self.costToCompany is not None else 0.0
    
    @property
    def totalSellingPrice(self):
        if self.isAccommodation and self.numNights and self.sellingPricePerNight:
            return self.numNights * self.sellingPricePerNight
        if self.isVehicleRental and self.is_hourly and self.hours and self.sellingPrice:
            return self.hours * self.sellingPrice
        return self.sellingPrice if self.sellingPrice is not None else 0.0
    
    @property
    def profit(self):
        return self.totalSellingPrice - self.totalCost
    
    @property
    def startDateTime(self):
        """Get full start datetime for tours (combining date and time)"""
        if self.isTour and self.startTime:
            return datetime.combine(self.startDate, self.startTime)
        return datetime.combine(self.startDate, time(0, 0))  # Default to midnight
    
    @property
    def endDateTime(self):
        """Get full end datetime for tours (combining date and time)"""
        if self.isTour and self.endTime:
            return datetime.combine(self.endDate, self.endTime)
        return datetime.combine(self.endDate, time(23, 59))  # Default to end of day

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("booking.id"), nullable=False)
    invoiceType = db.Column(db.String(20), nullable=False) # client, company, monthly_company, my_company
    totalAmount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="pending")  # pending, paid, overdue
    invoiceDate = db.Column(db.Date, nullable=False)
    pdfPath = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    # booking = db.relationship("Booking", backref="invoices", lazy=True) # This line is removed as the relationship is defined in Booking model

# New model for monthly company invoices
class MonthlyCompanyInvoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"), nullable=False)
    invoice_month = db.Column(db.Integer, nullable=False)  # 1-12
    invoice_year = db.Column(db.Integer, nullable=False)
    
    # Invoice details
    totalAmount = db.Column(db.Float, nullable=False, default=0.0)
    totalCost = db.Column(db.Float, nullable=False, default=0.0)  # For my_company invoices
    totalProfit = db.Column(db.Float, nullable=False, default=0.0)  # For my_company invoices
    
    # Invoice type: 'partner_company' or 'my_company'
    invoiceType = db.Column(db.String(20), nullable=False, default="partner_company")
    
    status = db.Column(db.String(20), default="pending")  # pending, paid, overdue
    invoiceDate = db.Column(db.Date, nullable=False)
    pdfPath = db.Column(db.String(255), nullable=True)
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

# New model for monthly invoice items (services breakdown)
class MonthlyInvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    monthly_invoice_id = db.Column(db.Integer, db.ForeignKey("monthly_company_invoice.id"), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("service.id"), nullable=True)  # Reference to original service
    
    # Client information
    client_name = db.Column(db.String(200), nullable=False)
    arrival_date = db.Column(db.Date, nullable=True)
    
    # Service details
    service_type = db.Column(db.String(50), nullable=False)  # Tour, Vehicle, Hotel
    service_name = db.Column(db.String(200), nullable=False)
    service_date = db.Column(db.Date, nullable=False)
    
    # Financial details
    cost_price = db.Column(db.Float, nullable=False, default=0.0)
    selling_price = db.Column(db.Float, nullable=False, default=0.0)
    profit = db.Column(db.Float, nullable=False, default=0.0)
    
    # Additional details
    nights_or_hours = db.Column(db.String(50), nullable=True)  # "3 nights" or "5 hours"
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
    notification_type = db.Column(db.String(50), nullable=False)  # email, whatsapp, sms
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



