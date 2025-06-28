from flask import Blueprint, request, jsonify, send_file
from datetime import datetime, date
import os
from fpdf import FPDF, HTMLMixin
from fpdf.enums import Align, XPos, YPos
from src.models.database import db, Invoice, Booking, MonthlyCompanyInvoice, MonthlyInvoiceItem, Company, Client, Service, Settings
from arabic_reshaper import ArabicReshaper
from bidi.algorithm import get_display
import logging
import unicodedata

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Extend FPDF with HTMLMixin for better text handling
class MyFPDF(FPDF, HTMLMixin):
    pass

invoices_bp = Blueprint("invoices", __name__)

# Define font paths (assuming these fonts are available in a 'fonts' directory)
FONT_DIR = "/home/ubuntu/fonts"

# Ensure the fonts directory exists
if not os.path.exists(FONT_DIR):
    os.makedirs(FONT_DIR)

# Initialize Arabic reshaper
configuration = {
    'delete_harakat': False,
    'support_ligatures': True
}

reshaper = ArabicReshaper(configuration=configuration)

def get_arabic_text(text):
    return get_display(reshaper.reshape(text))

def safe_get_text(obj, key, default="N/A", max_length=None):
    """
    Safely get text from an object/dict with None handling and optional length limiting.
    
    Args:
        obj: Dictionary or object to get value from
        key: Key/attribute name to access
        default: Default value if key is None or doesn't exist
        max_length: Maximum length to truncate text (optional)
    
    Returns:
        Safe text string ready for PDF generation
    """
    try:
        # Handle dictionary access
        if isinstance(obj, dict):
            value = obj.get(key, default)
        else:
            # Handle object attribute access
            value = getattr(obj, key, default)
        
        # Handle None values
        if value is None:
            value = default
        
        # Convert to string
        value = str(value)
        
        # Apply length limit if specified
        if max_length and len(value) > max_length:
            value = value[:max_length]
        
        # Apply safe_text processing
        return safe_text(value)
    
    except Exception as e:
        logging.warning(f"Error getting safe text for key '{key}': {e}")
        return safe_text(default)

def safe_text(text):
    """
    Convert text to a safe format for PDF generation.
    Handles Turkish and other non-Latin characters, and None values.
    """
    if text is None:
        return ""
    
    # Convert to string if not already
    text = str(text)
    
    # Replace problematic Turkish characters with safe alternatives
    replacements = {
        'İ': 'I',  # Turkish capital I with dot
        'ı': 'i',  # Turkish lowercase dotless i
        'Ğ': 'G',  # Turkish capital G with breve
        'ğ': 'g',  # Turkish lowercase g with breve
        'Ü': 'U',  # Turkish capital U with diaeresis
        'ü': 'u',  # Turkish lowercase u with diaeresis
        'Ş': 'S',  # Turkish capital S with cedilla
        'ş': 's',  # Turkish lowercase s with cedilla
        'Ö': 'O',  # Turkish capital O with diaeresis
        'ö': 'o',  # Turkish lowercase o with diaeresis
        'Ç': 'C',  # Turkish capital C with cedilla
        'ç': 'c',  # Turkish lowercase c with cedilla
    }
    
    # Apply replacements
    for turkish_char, replacement in replacements.items():
        text = text.replace(turkish_char, replacement)
    
    # Remove any remaining non-ASCII characters that might cause issues
    try:
        # Try to encode as latin-1 to check compatibility
        text.encode('latin-1')
        return text
    except UnicodeEncodeError:
        # If encoding fails, normalize and remove problematic characters
        normalized = unicodedata.normalize('NFKD', text)
        ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
        return ascii_text

# Function to get company settings including logo
def get_company_settings():
    """Get company settings from the database"""
    try:
        settings = {}
        
        # Get all settings from database
        db_settings = Settings.query.all()
        for setting in db_settings:
            try:
                import json
                settings[setting.key] = json.loads(setting.value)
            except json.JSONDecodeError:
                settings[setting.key] = setting.value
        
        # Default values if not found
        company_name = safe_text(settings.get('company_name', 'AK SERAGOLU TURIZM'))
        company_logo = settings.get('company_logo', '')
        
        # Debug logging for logo path
        logging.info(f"Company logo path from settings: {company_logo}")
        
        # Handle different possible logo path formats
        if company_logo:
            # Remove leading slash if present
            logo_path = company_logo.lstrip('/')
            
            # Check if it's a relative path and make it absolute
            if not os.path.isabs(logo_path):
                # Try different possible base paths
                possible_paths = [
                    logo_path,  # As is
                    os.path.join(os.getcwd(), logo_path),  # Current working directory
                    os.path.join(os.path.dirname(__file__), logo_path),  # Relative to this file
                    os.path.join(os.path.dirname(__file__), '..', logo_path),  # Parent directory
                    os.path.join(os.path.dirname(__file__), '..', '..', logo_path),  # Two levels up
                    os.path.join('/home/ubuntu', logo_path),  # Home directory
                    os.path.join('/home/ubuntu/src', logo_path),  # src directory
                    os.path.join('/home/ubuntu/uploads', logo_path),  # uploads directory
                    os.path.join('/home/ubuntu/static', logo_path),  # static directory
                    os.path.join('/home/ubuntu/upload', logo_path),  # upload directory
                    os.path.join('/home/ubuntu/src/routes/uploads', logo_path),  # routes/uploads directory
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        logging.info(f"Found logo at: {path}")
                        company_logo = path
                        break
                else:
                    logging.warning(f"Logo file not found in any of the expected locations: {possible_paths}")
                    company_logo = ''
            else:
                # Absolute path - check if it exists
                if not os.path.exists(logo_path):
                    logging.warning(f"Logo file not found at absolute path: {logo_path}")
                    company_logo = ''
                else:
                    company_logo = logo_path
        
        return company_name, company_logo
    except Exception as e:
        logging.warning(f"Could not load company settings: {e}")
        return 'AK SERAGOLU TURIZM', ''

# Function to add a standard font for English and Unicode characters
def add_unicode_fonts(pdf):
    try:
        # Try to use Noto Sans Arabic font if available
        noto_font_path = os.path.join(FONT_DIR, "NotoSansArabic-Regular.ttf")
        noto_bold_path = os.path.join(FONT_DIR, "NotoSansArabic-Bold.ttf")
        
        if os.path.exists(noto_font_path):
            pdf.add_font("NotoArabic", "", noto_font_path)
            if os.path.exists(noto_bold_path):
                pdf.add_font("NotoArabic", "B", noto_bold_path)
            else:
                pdf.add_font("NotoArabic", "B", noto_font_path)
            pdf.set_font("NotoArabic", "", 10)
            return True
        else:
            # Fallback to DejaVu fonts
            dejavu_font_path = os.path.join(FONT_DIR, "DejaVuSansCondensed.ttf")
            dejavu_bold_path = os.path.join(FONT_DIR, "DejaVuSansCondensed-Bold.ttf")
            
            if os.path.exists(dejavu_font_path):
                pdf.add_font("DejaVu", "", dejavu_font_path)
                if os.path.exists(dejavu_bold_path):
                    pdf.add_font("DejaVu", "B", dejavu_bold_path)
                else:
                    pdf.add_font("DejaVu", "B", dejavu_font_path)
                pdf.set_font("DejaVu", "", 10)
                return True
            else:
                # Use built-in Helvetica as last resort
                pdf.set_font("Helvetica", "", 10)
                return False
    except Exception as e:
        logging.warning(f"Could not load custom font. Using built-in Helvetica. Error: {e}")
        pdf.set_font("Helvetica", "", 10)
        return False

class MonthlyCompanyInvoicePDF(MyFPDF):
    def header(self):
        company_name, company_logo = get_company_settings()
        
        # Add logo if available
        if company_logo:
            try:
                logging.info(f"Attempting to load logo from: {company_logo}")
                # Try to load the image with better error handling
                self.image(company_logo, 10, 8, 33)
                self.ln(25)  # Add more space after logo
                logging.info("Logo loaded successfully")
            except Exception as e:
                logging.error(f"Could not load logo from {company_logo}: {e}")
                # Add space even if logo fails to load
                self.ln(10)
        else:
            logging.info("No logo path provided")
            self.ln(10)
        
        add_unicode_fonts(self)
        self.set_font("NotoArabic", "B", 15) if add_unicode_fonts(self) else self.set_font("Helvetica", "B", 15)
        self.cell(0, 10, safe_text(company_name), 0, 1, "C")
        self.cell(0, 10, "Monthly Company Invoice", 0, 1, "C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        add_unicode_fonts(self)
        self.set_font("NotoArabic", "I", 8) if add_unicode_fonts(self) else self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")

class MyCompanyInvoicePDF(MyFPDF):
    def header(self):
        company_name, company_logo = get_company_settings()
        
        # Add logo if available
        if company_logo:
            try:
                logging.info(f"Attempting to load logo from: {company_logo}")
                # Try to load the image with better error handling
                self.image(company_logo, 10, 8, 33)
                self.ln(25)  # Add more space after logo
                logging.info("Logo loaded successfully")
            except Exception as e:
                logging.error(f"Could not load logo from {company_logo}: {e}")
                # Add space even if logo fails to load
                self.ln(10)
        else:
            logging.info("No logo path provided")
            self.ln(10)
        
        add_unicode_fonts(self)
        self.set_font("NotoArabic", "B", 15) if add_unicode_fonts(self) else self.set_font("Helvetica", "B", 15)
        self.cell(0, 10, safe_text(company_name), 0, 1, "C")
        self.cell(0, 10, "My Company Invoice (Internal Report)", 0, 1, "C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        add_unicode_fonts(self)
        self.set_font("NotoArabic", "I", 8) if add_unicode_fonts(self) else self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")

class ClientDetailedInvoicePDF(MyFPDF):
    def header(self):
        company_name, company_logo = get_company_settings()
        
        # Add logo if available
        if company_logo:
            try:
                logging.info(f"Attempting to load logo from: {company_logo}")
                # Try to load the image with better error handling
                self.image(company_logo, 10, 8, 33)
                self.ln(25)  # Add more space after logo
                logging.info("Logo loaded successfully")
            except Exception as e:
                logging.error(f"Could not load logo from {company_logo}: {e}")
                # Add space even if logo fails to load
                self.ln(10)
        else:
            logging.info("No logo path provided")
            self.ln(10)
        
        add_unicode_fonts(self)
        self.set_font("NotoArabic", "B", 15) if add_unicode_fonts(self) else self.set_font("Helvetica", "B", 15)
        self.cell(0, 10, safe_text(company_name), 0, 1, "C")
        self.cell(0, 10, "Client Detailed Invoice", 0, 1, "C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        add_unicode_fonts(self)
        self.set_font("NotoArabic", "I", 8) if add_unicode_fonts(self) else self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")

def generate_client_detailed_invoice_pdf(client_data):
    """Generate PDF for client detailed invoice (client-facing)"""
    pdf = ClientDetailedInvoicePDF()
    add_unicode_fonts(pdf)
    pdf.add_page()
    
    # Serial Number - Display first
    pdf.set_font("NotoArabic", "B", 14) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 14)
    invoice_serial = client_data.get('invoiceSerial', f"INV-{datetime.now().strftime('%Y%m%d')}-{client_data.get('clientId', '001')}")
    pdf.cell(0, 10, f"Invoice Serial: {invoice_serial}", 0, 1, "L")
    pdf.ln(5)
    
    # Invoice details
    pdf.set_font("NotoArabic", "B", 12) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, f"Invoice Date: {date.today().strftime('%Y-%m-%d')}", 0, 1, "L")
    pdf.ln(5)
    
    # Client information - Display client name only once at the top
    pdf.set_font("NotoArabic", "B", 14) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, f"Client: {safe_text(client_data.get('clientName', 'Unknown Client'))}", 0, 1, "L")
    pdf.set_font("NotoArabic", "", 10) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 8, f"Email: {safe_text(client_data.get('email', 'No email provided'))}", 0, 1, "L")
    pdf.cell(0, 8, f"Arrival Date: {safe_text(client_data.get('arrivalDate', 'N/A'))}", 0, 1, "L")
    pdf.ln(10)
    
    # Services breakdown
    pdf.set_font("NotoArabic", "B", 14) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Service Details", 0, 1, "C")
    pdf.ln(5)
    
    # Safely get services list
    services = client_data.get("services", [])
    if not services:
        pdf.set_font("NotoArabic", "", 10) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 10, "No services found for this client.", 0, 1, "C")
        return pdf
    
    # Separate tours/vehicles and hotels with safe access
    tours_vehicles = []
    hotels = []
    
    for service in services:
        service_category = safe_get_text(service, "serviceCategory", "Unknown")
        if service_category == "Tours and Car Rentals":
            tours_vehicles.append(service)
        elif service_category == "Hotels":
            hotels.append(service)
    
    # Calculate totals for each category with safe access
    tours_total = sum(service.get("totalSellingPrice", 0) for service in tours_vehicles)
    hotels_total = sum(service.get("totalSellingPrice", 0) for service in hotels)
    
    # Tours and Vehicle Rentals Summary
    if tours_vehicles:
        pdf.set_font("NotoArabic", "B", 12) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "Tours and Car Rentals", 0, 1, "L")
        pdf.set_font("NotoArabic", "", 10) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "", 10)
        
        # Smart table with auto-adjusting columns for tours (including start date for tours only)
        pdf.set_font("NotoArabic", "B", 10) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 10)
        
        # Check if any service is a tour to determine if we need the date column
        has_tours = any(safe_get_text(service, "serviceType", "") == "Tour" for service in tours_vehicles)
        
        if has_tours:
            # Table with tour start date column
            pdf.cell(80, 8, "Service", 1, 0, "C")
            pdf.cell(40, 8, "Date", 1, 0, "C")
            pdf.cell(40, 8, "Total Price", 1, 1, "C")
            
            pdf.set_font("NotoArabic", "", 9) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "", 9)
            for service in tours_vehicles:
                service_name = safe_get_text(service, "serviceName", "Unknown Service", 35)
                pdf.cell(80, 6, service_name, 1, 0, "L")
                
                # Show start date only for tours
                if safe_get_text(service, "serviceType", "") == "Tour":
                    start_date = safe_get_text(service, "startDate", "N/A")
                    pdf.cell(40, 6, start_date, 1, 0, "C")
                else:
                    pdf.cell(40, 6, "-", 1, 0, "C")
                
                price = service.get('totalSellingPrice', 0)
                pdf.cell(40, 6, f"${price:.2f}", 1, 1, "R")
        else:
            # Simple table without date column for non-tour services
            pdf.cell(120, 8, "Service", 1, 0, "C")
            pdf.cell(40, 8, "Total Price", 1, 1, "C")
            
            pdf.set_font("NotoArabic", "", 9) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "", 9)
            for service in tours_vehicles:
                service_name = safe_get_text(service, "serviceName", "Unknown Service", 50)
                pdf.cell(120, 6, service_name, 1, 0, "L")
                price = service.get('totalSellingPrice', 0)
                pdf.cell(40, 6, f"${price:.2f}", 1, 1, "R")
        
        # Tours subtotal
        pdf.set_font("NotoArabic", "B", 10) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 10)
        if has_tours:
            pdf.cell(120, 8, "Tours/Vehicles Total", 1, 0, "R")
            pdf.cell(40, 8, f"${tours_total:.2f}", 1, 1, "R")
        else:
            pdf.cell(120, 8, "Tours/Vehicles Total", 1, 0, "R")
            pdf.cell(40, 8, f"${tours_total:.2f}", 1, 1, "R")
        pdf.ln(5)
    
    # Hotels Summary
    if hotels:
        pdf.set_font("NotoArabic", "B", 12) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "Hotels/Bungaloves", 0, 1, "L")
        pdf.set_font("NotoArabic", "", 10) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "", 10)
        
        # Smart table with auto-adjusting columns for hotels
        pdf.set_font("NotoArabic", "B", 10) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 10)
        
        # Calculate optimal column widths based on content with safe access
        max_hotel_name_length = 20  # Default minimum
        max_city_length = 10  # Default minimum
        
        for service in hotels:
            hotel_name = safe_get_text(service, "hotelName", safe_get_text(service, "serviceName", "Unknown"), 35)
            hotel_city = safe_get_text(service, "hotelCity", "N/A", 20)
            
            max_hotel_name_length = max(max_hotel_name_length, len(hotel_name))
            max_city_length = max(max_city_length, len(hotel_city))
        
        # Adjust column widths based on content
        hotel_col_width = min(max(60, max_hotel_name_length * 2), 90)
        city_col_width = min(max(30, max_city_length * 2), 50)
        price_col_width = 40
        
        # Ensure total width doesn't exceed page width (160 is safe margin)
        total_width = hotel_col_width + city_col_width + price_col_width
        if total_width > 160:
            ratio = 160 / total_width
            hotel_col_width = int(hotel_col_width * ratio)
            city_col_width = int(city_col_width * ratio)
            price_col_width = 160 - hotel_col_width - city_col_width
        
        pdf.cell(hotel_col_width, 8, "Name", 1, 0, "C")
        pdf.cell(city_col_width, 8, "City", 1, 0, "C")
        pdf.cell(price_col_width, 8, "Total Price", 1, 1, "C")
        
        pdf.set_font("NotoArabic", "", 9) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "", 9)
        for service in hotels:
            hotel_name = safe_get_text(service, "hotelName", safe_get_text(service, "serviceName", "Unknown"), 35)
            hotel_city = safe_get_text(service, "hotelCity", "N/A", 20)
            price = service.get('totalSellingPrice', 0)
            
            pdf.cell(hotel_col_width, 6, hotel_name, 1, 0, "L")
            pdf.cell(city_col_width, 6, hotel_city, 1, 0, "L")
            pdf.cell(price_col_width, 6, f"${price:.2f}", 1, 1, "R")
        
        # Hotels subtotal
        pdf.set_font("NotoArabic", "B", 10) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 10)
        pdf.cell(hotel_col_width + city_col_width, 8, "Hotels Total", 1, 0, "R")
        pdf.cell(price_col_width, 8, f"${hotels_total:.2f}", 1, 1, "R")
        pdf.ln(5)
    
    # Grand Total
    pdf.set_font("NotoArabic", "B", 14) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 14)
    total_price = client_data.get('totalSellingPrice', 0)
    pdf.cell(120, 10, "Total Amount", 1, 0, "R")
    pdf.cell(40, 10, f"${total_price:.2f}", 1, 1, "R")
    
    return pdf

def generate_monthly_company_invoice_pdf(monthly_invoice):
    """Generate PDF for monthly company invoice (partner company)"""
    pdf = MonthlyCompanyInvoicePDF()
    add_unicode_fonts(pdf)
    pdf.add_page()
    
    # Serial Number - Display first
    pdf.set_font("NotoArabic", "B", 14) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 14)
    invoice_serial = f"COMP-{monthly_invoice.invoice_date.strftime('%Y%m')}-{monthly_invoice.id}"
    pdf.cell(0, 10, f"Invoice Serial: {invoice_serial}", 0, 1, "L")
    pdf.ln(5)
    
    # Invoice details
    pdf.set_font("NotoArabic", "B", 12) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, f"Invoice Date: {monthly_invoice.invoice_date.strftime('%Y-%m-%d')}", 0, 1, "L")
    pdf.cell(0, 10, f"Period: {safe_get_text(monthly_invoice, 'invoice_period', 'N/A')}", 0, 1, "L")
    pdf.cell(0, 10, f"Invoice ID: {monthly_invoice.id}", 0, 1, "L")
    pdf.ln(5)
    
    # Company information with safe access
    pdf.set_font("NotoArabic", "B", 12) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "Company Information:", 0, 1, "L")
    pdf.set_font("NotoArabic", "", 10) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "", 10)
    
    company_name = safe_get_text(monthly_invoice.company, 'name', 'Unknown Company') if monthly_invoice.company else 'Unknown Company'
    contact_person = safe_get_text(monthly_invoice.company, 'contactPerson', 'N/A') if monthly_invoice.company else 'N/A'
    email = safe_get_text(monthly_invoice.company, 'email', 'N/A') if monthly_invoice.company else 'N/A'
    
    pdf.cell(0, 8, f"Company: {company_name}", 0, 1, "L")
    pdf.cell(0, 8, f"Contact Person: {contact_person}", 0, 1, "L")
    pdf.cell(0, 8, f"Email: {email}", 0, 1, "L")
    pdf.ln(10)
    
    # Services breakdown grouped by client
    pdf.set_font("NotoArabic", "B", 14) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Service Summary by Client", 0, 1, "C")
    pdf.ln(5)
    
    # Group items by client with safe access
    client_groups = {}
    for item in monthly_invoice.invoice_items:
        client_name = safe_get_text(item, 'client_name', 'Unknown Client')
        if client_name not in client_groups:
            client_groups[client_name] = {
                'tours_total': 0,
                'hotels_total': 0,
                'arrival_date': getattr(item, 'service_date', None)
            }
        
        service_type = safe_get_text(item, 'service_type', '')
        selling_price = getattr(item, 'selling_price', 0) or 0
        
        if service_type in ["Tour", "Vehicle"]:
            client_groups[client_name]['tours_total'] += selling_price
        elif service_type == "Hotel":
            client_groups[client_name]['hotels_total'] += selling_price
    
    # Smart table with auto-adjusting columns
    pdf.set_font("NotoArabic", "B", 10) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 10)
    
    # Calculate optimal column widths with safe access
    max_client_name_length = 20  # Default minimum
    for client_name in client_groups.keys():
        max_client_name_length = max(max_client_name_length, len(str(client_name)[:30]))
    
    client_col_width = min(max(50, max_client_name_length * 2), 70)
    date_col_width = 35
    tours_col_width = 35
    hotels_col_width = 35
    
    # Ensure total width fits
    total_width = client_col_width + date_col_width + tours_col_width + hotels_col_width
    if total_width > 160:
        ratio = 160 / total_width
        client_col_width = int(client_col_width * ratio)
        date_col_width = int(date_col_width * ratio)
        tours_col_width = int(tours_col_width * ratio)
        hotels_col_width = 160 - client_col_width - date_col_width - tours_col_width
    
    pdf.cell(client_col_width, 8, "Client", 1, 0, "C")
    pdf.cell(date_col_width, 8, "Arrival Date", 1, 0, "C")
    pdf.cell(tours_col_width, 8, "Tours/Vehicles", 1, 0, "C")
    pdf.cell(hotels_col_width, 8, "Hotels", 1, 1, "C")
    
    pdf.set_font("NotoArabic", "", 9) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "", 9)
    
    total_tours = 0
    total_hotels = 0
    
    for client_name, data in client_groups.items():
        safe_client_name = safe_text(str(client_name)[:30])
        pdf.cell(client_col_width, 6, safe_client_name, 1, 0, "L")
        
        arrival_date = "N/A"
        if data['arrival_date']:
            try:
                arrival_date = data['arrival_date'].strftime('%Y-%m-%d')
            except:
                arrival_date = str(data['arrival_date'])[:10]
        
        pdf.cell(date_col_width, 6, arrival_date, 1, 0, "C")
        pdf.cell(tours_col_width, 6, f"${data['tours_total']:.2f}", 1, 0, "R")
        pdf.cell(hotels_col_width, 6, f"${data['hotels_total']:.2f}", 1, 1, "R")
        
        total_tours += data['tours_total']
        total_hotels += data['hotels_total']
    
    # Totals
    pdf.set_font("NotoArabic", "B", 10) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 10)
    pdf.cell(client_col_width + date_col_width, 8, "TOTALS", 1, 0, "R")
    pdf.cell(tours_col_width, 8, f"${total_tours:.2f}", 1, 0, "R")
    pdf.cell(hotels_col_width, 8, f"${total_hotels:.2f}", 1, 1, "R")
    
    # Grand Total
    pdf.ln(5)
    pdf.set_font("NotoArabic", "B", 14) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 14)
    total_amount = getattr(monthly_invoice, 'totalAmount', 0) or 0
    pdf.cell(120, 10, "Total Amount", 1, 0, "R")
    pdf.cell(40, 10, f"${total_amount:.2f}", 1, 1, "R")
    
    return pdf

def generate_my_company_invoice_pdf(monthly_invoice):
    """Generate PDF for my company invoice with cost, selling price, and profit breakdown"""
    pdf = MyCompanyInvoicePDF()
    add_unicode_fonts(pdf)
    pdf.add_page()
    
    # Serial Number - Display first
    pdf.set_font("NotoArabic", "B", 14) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 14)
    invoice_serial = f"INT-{monthly_invoice.invoice_date.strftime('%Y%m')}-{monthly_invoice.id}"
    pdf.cell(0, 10, f"Invoice Serial: {invoice_serial}", 0, 1, "L")
    pdf.ln(5)
    
    # Invoice details
    pdf.set_font("NotoArabic", "B", 12) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, f"Invoice Date: {monthly_invoice.invoice_date.strftime('%Y-%m-%d')}", 0, 1, "L")
    pdf.cell(0, 10, f"Period: {safe_get_text(monthly_invoice, 'invoice_period', 'N/A')}", 0, 1, "L")
    pdf.cell(0, 10, f"Invoice ID: {monthly_invoice.id}", 0, 1, "L")
    pdf.ln(5)
    
    # Company information with safe access
    pdf.set_font("NotoArabic", "B", 12) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "Company Information:", 0, 1, "L")
    pdf.set_font("NotoArabic", "", 10) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "", 10)
    
    company_name = safe_get_text(monthly_invoice.company, 'name', 'Unknown Company') if monthly_invoice.company else 'Unknown Company'
    contact_person = safe_get_text(monthly_invoice.company, 'contactPerson', 'N/A') if monthly_invoice.company else 'N/A'
    email = safe_get_text(monthly_invoice.company, 'email', 'N/A') if monthly_invoice.company else 'N/A'
    
    pdf.cell(0, 8, f"Company: {company_name}", 0, 1, "L")
    pdf.cell(0, 8, f"Contact Person: {contact_person}", 0, 1, "L")
    pdf.cell(0, 8, f"Email: {email}", 0, 1, "L")
    pdf.ln(10)
    
    # Services breakdown grouped by client with cost analysis
    pdf.set_font("NotoArabic", "B", 14) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Cost Analysis Summary by Client", 0, 1, "C")
    pdf.ln(5)
    
    # Group items by client with safe access
    client_groups = {}
    for item in monthly_invoice.invoice_items:
        client_name = safe_get_text(item, 'client_name', 'Unknown Client')
        if client_name not in client_groups:
            client_groups[client_name] = {
                'tours_cost': 0,
                'tours_sale': 0,
                'hotels_cost': 0,
                'hotels_sale': 0,
                'arrival_date': getattr(item, 'service_date', None)
            }
        
        service_type = safe_get_text(item, 'service_type', '')
        cost_price = getattr(item, 'cost_price', 0) or 0
        selling_price = getattr(item, 'selling_price', 0) or 0
        
        if service_type in ["Tour", "Vehicle"]:
            client_groups[client_name]['tours_cost'] += cost_price
            client_groups[client_name]['tours_sale'] += selling_price
        elif service_type == "Hotel":
            client_groups[client_name]['hotels_cost'] += cost_price
            client_groups[client_name]['hotels_sale'] += selling_price
    
    # Create summary table
    pdf.set_font("NotoArabic", "B", 9) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 9)
    pdf.cell(50, 8, "Client Name", 1, 0, "C")
    pdf.cell(25, 8, "Arrival Date", 1, 0, "C")
    pdf.cell(30, 8, "Tours Cost", 1, 0, "C")
    pdf.cell(30, 8, "Hotels Cost", 1, 0, "C")
    pdf.cell(35, 8, "Total Profit", 1, 1, "C")
    
    pdf.set_font("NotoArabic", "", 8) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "", 8)
    total_tours_cost = 0
    total_hotels_cost = 0
    total_profit = 0
    
    for client_name, totals in client_groups.items():
        client_profit = (totals['tours_sale'] - totals['tours_cost']) + (totals['hotels_sale'] - totals['hotels_cost'])
        
        safe_client_name = safe_text(str(client_name)[:25])
        pdf.cell(50, 6, safe_client_name, 1, 0, "L")
        
        arrival_date = "N/A"
        if totals['arrival_date']:
            try:
                arrival_date = totals['arrival_date'].strftime('%Y-%m-%d')
            except:
                arrival_date = str(totals['arrival_date'])[:10]
        
        pdf.cell(25, 6, arrival_date, 1, 0, "C")
        pdf.cell(30, 6, f"${totals['tours_cost']:.2f}", 1, 0, "R")
        pdf.cell(30, 6, f"${totals['hotels_cost']:.2f}", 1, 0, "R")
        pdf.cell(35, 6, f"${client_profit:.2f}", 1, 1, "R")
        
        total_tours_cost += totals['tours_cost']
        total_hotels_cost += totals['hotels_cost']
        total_profit += client_profit
    
    # Totals row
    pdf.set_font("NotoArabic", "B", 9) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 9)
    pdf.cell(75, 8, "TOTALS", 1, 0, "R")
    pdf.cell(30, 8, f"${total_tours_cost:.2f}", 1, 0, "R")
    pdf.cell(30, 8, f"${total_hotels_cost:.2f}", 1, 0, "R")
    pdf.cell(35, 8, f"${total_profit:.2f}", 1, 1, "R")
    
    # Summary section
    pdf.set_font("NotoArabic", "B", 12) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "Financial Summary", 0, 1, "L")
    pdf.set_font("NotoArabic", "", 10) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "", 10)
    
    total_cost = getattr(monthly_invoice, 'totalCost', 0) or 0
    total_amount = getattr(monthly_invoice, 'totalAmount', 0) or 0
    total_profit_calc = getattr(monthly_invoice, 'totalProfit', 0) or 0
    
    pdf.cell(0, 8, f"Total Cost: ${total_cost:.2f}", 0, 1, "L")
    pdf.cell(0, 8, f"Total Revenue: ${total_amount:.2f}", 0, 1, "L")
    pdf.cell(0, 8, f"Total Profit: ${total_profit_calc:.2f}", 0, 1, "L")
    
    return pdf

@invoices_bp.route("/invoices", methods=["GET"])
def get_invoices():
    try:
        # Get regular invoices
        invoices = Invoice.query.all()
        regular_invoices = []
        
        for invoice in invoices:
            booking = invoice.booking
            client_name = "Unknown"
            if booking and booking.client_ref:
                first_name = safe_get_text(booking.client_ref, 'firstName', '')
                last_name = safe_get_text(booking.client_ref, 'lastName', '')
                client_name = f"{first_name} {last_name}".strip()
                if not client_name:
                    client_name = "Unknown"
            
            # Get service names from booking with safe access
            service_names = []
            if booking and booking.services:
                for service in booking.services:
                    service_name = safe_get_text(service, 'serviceName', 'Unknown Service')
                    service_names.append(service_name)
            
            service_name = ", ".join(service_names[:2]) if service_names else "No services"
            if len(service_names) > 2:
                service_name += f" (+{len(service_names) - 2} more)"
            
            regular_invoices.append({
                "id": invoice.id,
                "client": client_name,
                "service": service_name,
                "type": safe_get_text(invoice, 'invoiceType', 'unknown'),
                "status": safe_get_text(invoice, 'status', 'unknown'),
                "date": invoice.invoice_date.strftime("%Y-%m-%d") if invoice.invoice_date else "N/A",
                "amount": float(getattr(invoice, 'totalAmount', 0) or 0),
                "pdfPath": safe_get_text(invoice, 'pdfPath', '')
            })
        
        # Get monthly company invoices with safe access
        monthly_invoices = MonthlyCompanyInvoice.query.all()
        logging.info(f"Found {len(monthly_invoices)} monthly company invoices")
        
        for monthly_invoice in monthly_invoices:
            # Ensure status is not None or empty
            status = safe_get_text(monthly_invoice, 'status', 'completed')
            company_name = safe_get_text(monthly_invoice.company, 'name', 'Unknown Company') if monthly_invoice.company else 'Unknown Company'
            invoice_period = safe_get_text(monthly_invoice, 'invoice_period', 'N/A')
            
            regular_invoices.append({
                "id": f"monthly_{monthly_invoice.id}",
                "client": company_name,
                "service": f"Monthly Invoice - {invoice_period}",
                "type": "company",
                "status": status,
                "date": monthly_invoice.invoice_date.strftime("%Y-%m-%d") if monthly_invoice.invoice_date else "N/A",
                "amount": float(getattr(monthly_invoice, 'totalAmount', 0) or 0),
                "pdfPath": safe_get_text(monthly_invoice, 'pdfPath', '')
            })
            
            logging.info(f"Added monthly invoice {monthly_invoice.id} with status: {status}")
        
        return jsonify(regular_invoices)
    except Exception as e:
        logging.error(f"Error fetching invoices: {e}")
        return jsonify({"error": "Failed to fetch invoices", "details": str(e)}), 500

@invoices_bp.route("/invoices/monthly-company", methods=["GET"])
def get_monthly_company_invoices():
    try:
        monthly_invoices = MonthlyCompanyInvoice.query.all()
        return jsonify([mi.to_dict() for mi in monthly_invoices])
    except Exception as e:
        logging.error(f"Error fetching monthly company invoices: {e}")
        return jsonify({"error": "Failed to fetch monthly company invoices", "details": str(e)}), 500

# Fix the route to match frontend expectations
@invoices_bp.route("/invoices/monthly/generate", methods=["POST"])
def generate_monthly_company_invoice():
    try:
        data = request.get_json()
        company_id = data.get("companyId")
        month = data.get("month")
        year = data.get("year")
        invoice_type = data.get("invoiceType", "partner_company")  # 'partner_company' or 'my_company'
    
        if not all([company_id, month, year]):
            logging.warning("Missing company ID, month, or year for monthly invoice generation.")
            return jsonify({"error": "Company ID, month, and year are required"}), 400

        company = Company.query.get(company_id)
        if not company:
            logging.warning(f"Company with ID {company_id} not found.")
            return jsonify({"error": "Company not found"}), 404

        # Check if invoice for this company, month, and year already exists
        existing_invoice = MonthlyCompanyInvoice.query.filter_by(
            company_id=company_id,
            invoice_month=month,
            invoice_year=year
        ).first()

        if existing_invoice:
            logging.info(f"Invoice for company {company_id} and period {month}/{year} already exists.")
            return jsonify({"error": "Invoice for this company and period already exists"}), 409

        # Fetch bookings for the specified company, month, and year
        # This assumes bookings have a service with a startDate
        services = db.session.query(Service).join(Booking).join(Client).filter(
            Client.company_id == company_id,
            db.extract("month", Service.startDate) == month,
            db.extract("year", Service.startDate) == year
        ).all()

        if not services:
            logging.info(f"No services found for company {company_id} in {month}/{year}.")
            return jsonify({"message": "No services found for this company in the specified period"}), 200

        total_amount = 0.0
        total_cost = 0.0
        total_profit = 0.0
        invoice_items = []

        for service in services:
            service_selling_price = getattr(service, 'totalSellingPrice', 0) or 0
            service_cost = getattr(service, 'totalCost', 0) or 0
            service_profit = getattr(service, 'profit', 0) or 0
            
            total_amount += service_selling_price
            total_cost += service_cost
            total_profit += service_profit

            # Determine nights_or_hours and hotel_or_tour_name with safe access
            nights_or_hours = None
            hotel_or_tour_name = None
            service_type = safe_get_text(service, 'serviceType', 'Unknown')
            
            if service_type == "Hotel":
                num_nights = getattr(service, 'numNights', None)
                nights_or_hours = f"{num_nights} Nights" if num_nights else None
                hotel_or_tour_name = safe_get_text(service, 'hotelName', 'Unknown Hotel')
            elif service_type in ["Tour", "Vehicle"]:
                is_hourly = getattr(service, 'is_hourly', False)
                hours = getattr(service, 'hours', None)
                
                if is_hourly and hours:
                    nights_or_hours = f"{hours} Hours"
                else:
                    # For tours/vehicles not hourly, show single date if start and end are same
                    start_date = getattr(service, 'startDate', None)
                    end_date = getattr(service, 'endDate', None)
                    
                    if start_date and end_date:
                        if start_date.strftime('%Y-%m-%d') == end_date.strftime('%Y-%m-%d'):
                            nights_or_hours = start_date.strftime('%Y-%m-%d')
                        else:
                            nights_or_hours = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                
                hotel_or_tour_name = safe_get_text(service, 'serviceName', 'Unknown Service')

            # Safe access to client information
            client_first_name = ""
            client_last_name = ""
            if service.booking_ref and service.booking_ref.client_ref:
                client_first_name = safe_get_text(service.booking_ref.client_ref, 'firstName', '')
                client_last_name = safe_get_text(service.booking_ref.client_ref, 'lastName', '')
            
            client_name = f"{client_first_name} {client_last_name}".strip()
            if not client_name:
                client_name = "Unknown Client"

            invoice_item = MonthlyInvoiceItem(
                service_id=service.id,
                client_name=client_name,
                service_name=safe_get_text(service, 'serviceName', 'Unknown Service'),
                service_type=service_type,
                service_date=getattr(service, 'startDate', None),
                selling_price=service_selling_price,
                cost_price=service_cost,
                profit=service_profit,
                nights_or_hours=nights_or_hours,
                hotel_or_tour_name=hotel_or_tour_name
            )
            invoice_items.append(invoice_item)

        new_monthly_invoice = MonthlyCompanyInvoice(
            company_id=company_id,
            invoice_month=month,
            invoice_year=year,
            invoice_date=date.today(),
            totalAmount=total_amount,
            totalCost=total_cost,
            totalProfit=total_profit,
            invoiceType=invoice_type,
            status="completed"  # Set status to completed instead of pending
        )
        db.session.add(new_monthly_invoice)
        db.session.flush()  # To get the ID for invoice_items

        for item in invoice_items:
            item.monthly_invoice_id = new_monthly_invoice.id
            db.session.add(item)

        db.session.commit()

        # Generate PDF
        pdf_output = None
        if invoice_type == "partner_company":
            pdf_output = generate_monthly_company_invoice_pdf(new_monthly_invoice)
        elif invoice_type == "my_company":
            pdf_output = generate_my_company_invoice_pdf(new_monthly_invoice)

        if pdf_output:
            # Use safe_text for filename to avoid encoding issues
            company_name_safe = safe_text(company.name).replace(" ", "_")
            pdf_filename = f"monthly_invoice_{company_name_safe}_{month}_{year}_{invoice_type}.pdf"
            pdf_path = os.path.join(os.path.dirname(__file__), "invoices", pdf_filename)
            # Ensure the invoices directory exists
            os.makedirs(os.path.join(os.path.dirname(__file__), "invoices"), exist_ok=True)
            pdf_output.output(pdf_path)
            
            # Save PDF path to database
            new_monthly_invoice.pdfPath = f"/api/invoices/download/{pdf_filename}"
            db.session.commit()
            
            logging.info(f"Monthly invoice PDF generated: {pdf_filename}")
            return jsonify({
                "message": "Monthly invoice generated successfully", 
                "id": new_monthly_invoice.id, 
                "pdfPath": f"/api/invoices/download/{pdf_filename}"
            }), 201
        else:
            logging.warning("Monthly invoice generated, but PDF could not be created.")
            return jsonify({"message": "Monthly invoice generated, but PDF could not be created."}), 201
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error generating monthly invoice: {e}")
        return jsonify({"error": str(e)}), 500

@invoices_bp.route("/invoices/client/<int:client_id>/generate", methods=["POST"])
def generate_client_invoice(client_id):
    try:
        data = request.get_json()
        month = data.get("month")
        year = data.get("year")

        client = Client.query.get(client_id)
        if not client:
            logging.warning(f"Client with ID {client_id} not found.")
            return jsonify({"error": "Client not found"}), 404

        # Debug: Log client information with safe access
        client_first_name = safe_get_text(client, 'firstName', 'Unknown')
        client_last_name = safe_get_text(client, 'lastName', 'Client')
        logging.info(f"Generating invoice for client {client_id}: {client_first_name} {client_last_name}")

        # Get all bookings for this client first
        bookings = Booking.query.filter_by(client_id=client_id).all()
        logging.info(f"Found {len(bookings)} bookings for client {client_id}")

        # Get services from all bookings for this client
        services_query = db.session.query(Service).join(Booking).filter(
            Booking.client_id == client_id
        )

        # Apply month/year filter only if both are provided
        if month and year:
            services_query = services_query.filter(
                db.extract("month", Service.startDate) == month,
                db.extract("year", Service.startDate) == year
            )
            logging.info(f"Filtering services for month {month} and year {year}")

        services = services_query.all()
        logging.info(f"Found {len(services)} services for client {client_id}")

        # Debug: Log service details with safe access
        for service in services:
            service_name = safe_get_text(service, 'serviceName', 'Unknown Service')
            service_type = safe_get_text(service, 'serviceType', 'Unknown Type')
            start_date = getattr(service, 'startDate', None)
            start_date_str = start_date.strftime('%Y-%m-%d') if start_date else 'N/A'
            logging.info(f"Service: {service_name}, Type: {service_type}, Start: {start_date_str}")

        if not services:
            # Additional debug: Check if there are any services at all for this client
            all_services = db.session.query(Service).join(Booking).filter(Booking.client_id == client_id).all()
            logging.info(f"Total services for client {client_id} (without date filter): {len(all_services)}")
            
            if all_services:
                logging.info("Services exist but don't match the date filter")
                for service in all_services:
                    service_name = safe_get_text(service, 'serviceName', 'Unknown Service')
                    start_date = getattr(service, 'startDate', None)
                    start_date_str = start_date.strftime('%Y-%m-%d') if start_date else 'N/A'
                    logging.info(f"Available service: {service_name}, Date: {start_date_str}")
            
            return jsonify({"message": "No services found for this client in the specified period"}), 200

        # Prepare client data for PDF generation with safe access
        client_name = f"{client_first_name} {client_last_name}".strip()
        if not client_name:
            client_name = "Unknown Client"
        
        client_email = safe_get_text(client, 'email', 'No email provided')
        
        # Get earliest start date with safe access
        start_dates = []
        for service in services:
            start_date = getattr(service, 'startDate', None)
            if start_date:
                start_dates.append(start_date)
        
        arrival_date = min(start_dates).strftime("%Y-%m-%d") if start_dates else "N/A"
        
        client_data = {
            "clientName": client_name,
            "email": client_email,
            "arrivalDate": arrival_date,
            "services": [],
            "totalSellingPrice": 0
        }

        for service in services:
            # Categorize services with safe access
            service_type = safe_get_text(service, 'serviceType', 'Unknown')
            service_category = "Tours and Car Rentals"
            if service_type == "Hotel":
                service_category = "Hotels"
            
            start_date = getattr(service, 'startDate', None)
            end_date = getattr(service, 'endDate', None)
            total_selling_price = getattr(service, 'totalSellingPrice', 0) or 0
            
            service_data = {
                "serviceName": safe_get_text(service, 'serviceName', 'Unknown Service'),
                "serviceType": service_type,
                "serviceCategory": service_category,
                "startDate": start_date.strftime("%Y-%m-%d") if start_date else "N/A",
                "endDate": end_date.strftime("%Y-%m-%d") if end_date else "N/A",
                "totalSellingPrice": float(total_selling_price),
                "nights": getattr(service, 'numNights', None) if service_type == "Hotel" else None,
                "hours": getattr(service, 'hours', None) if getattr(service, 'is_hourly', False) else None,
                "hotelName": safe_get_text(service, 'hotelName', None) if service_type == "Hotel" else None,
                "hotelCity": safe_get_text(service, 'hotelCity', None) if service_type == "Hotel" else None
            }
            client_data["services"].append(service_data)
            client_data["totalSellingPrice"] += total_selling_price

        # Generate PDF
        pdf_output = generate_client_detailed_invoice_pdf(client_data)
        
        if pdf_output:
            # Use safe_text for filename to avoid encoding issues
            client_name_safe = safe_text(f"{client_first_name}_{client_last_name}").replace(" ", "_")
            pdf_filename = f"client_invoice_{client_name_safe}_{client_id}.pdf"
            if month and year:
                pdf_filename = f"client_invoice_{client_name_safe}_{month}_{year}.pdf"
            
            pdf_path = os.path.join(os.path.dirname(__file__), "invoices", pdf_filename)
            # Ensure the invoices directory exists
            os.makedirs(os.path.join(os.path.dirname(__file__), "invoices"), exist_ok=True)
            pdf_output.output(pdf_path)
            
            # Create invoice record in database
            new_invoice = Invoice(
                booking_id=services[0].booking_id,  # Use first service's booking
                invoiceType="client",
                totalAmount=client_data["totalSellingPrice"],
                status="completed",  # Set status to completed instead of generated
                invoice_date=date.today(),
                pdfPath=f"/api/invoices/download/{pdf_filename}"
            )
            db.session.add(new_invoice)
            db.session.commit()
            
            logging.info(f"Client invoice PDF generated: {pdf_filename}")
            return jsonify({
                "message": "Client invoice generated successfully", 
                "id": new_invoice.id, 
                "pdfPath": f"/api/invoices/download/{pdf_filename}"
            }), 201
        else:
            logging.warning("Client invoice could not be created.")
            return jsonify({"message": "Client invoice could not be created."}), 500
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error generating client invoice: {e}")
        return jsonify({"error": str(e)}), 500

@invoices_bp.route("/invoices/download/<filename>", methods=["GET"])
def download_invoice(filename):
    try:
        pdf_path = os.path.join(os.path.dirname(__file__), "invoices", filename)
        if os.path.exists(pdf_path):
            return send_file(pdf_path, as_attachment=True, download_name=filename)
        else:
            return jsonify({"error": "File not found"}), 404
    except Exception as e:
        logging.error(f"Error downloading invoice: {e}")
        return jsonify({"error": str(e)}), 500

@invoices_bp.route("/invoices/<int:invoice_id>", methods=["DELETE"])
def delete_invoice(invoice_id):
    """Delete an invoice by ID"""
    try:
        # Find the invoice
        invoice = Invoice.query.get(invoice_id)
        if not invoice:
            return jsonify({"error": "Invoice not found"}), 404
        
        # Delete the PDF file if it exists
        if invoice.pdfPath:
            try:
                # Extract filename from pdfPath
                filename = invoice.pdfPath.split("/")[-1]
                pdf_path = os.path.join(os.path.dirname(__file__), "invoices", filename)
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
                    logging.info(f"Deleted PDF file: {pdf_path}")
            except Exception as e:
                logging.warning(f"Could not delete PDF file: {e}")
        
        # Delete the invoice from database
        db.session.delete(invoice)
        db.session.commit()
        
        logging.info(f"Invoice {invoice_id} deleted successfully")
        return jsonify({"message": "Invoice deleted successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting invoice {invoice_id}: {e}")
        return jsonify({"error": str(e)}), 500


# ==========================================
# NEW FEATURES: Excel-like Monthly Invoices
# ==========================================

# PDF Classes for new invoice types
class ExcelLikeInvoicePDF(MyFPDF):
    def header(self):
        company_name, company_logo = get_company_settings()
        
        if company_logo and os.path.exists(company_logo):
            try:
                self.image(company_logo, 10, 8, 33)
                self.ln(25)
            except Exception as e:
                logging.error(f"Could not load logo: {e}")
                self.ln(10)
        else:
            self.ln(10)
        
        add_unicode_fonts(self)
        self.set_font("NotoArabic", "B", 15) if add_unicode_fonts(self) else self.set_font("Helvetica", "B", 15)
        self.cell(0, 10, safe_text(company_name), 0, 1, "C")
        self.cell(0, 10, "Monthly Company Invoice - Excel Style", 0, 1, "C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        add_unicode_fonts(self)
        self.set_font("NotoArabic", "I", 8) if add_unicode_fonts(self) else self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")

class MyCompanyDetailedInvoicePDF(MyFPDF):
    def header(self):
        company_name, company_logo = get_company_settings()
        
        if company_logo and os.path.exists(company_logo):
            try:
                self.image(company_logo, 10, 8, 33)
                self.ln(25)
            except Exception as e:
                logging.error(f"Could not load logo: {e}")
                self.ln(10)
        else:
            self.ln(10)
        
        add_unicode_fonts(self)
        self.set_font("NotoArabic", "B", 15) if add_unicode_fonts(self) else self.set_font("Helvetica", "B", 15)
        self.cell(0, 10, safe_text(company_name), 0, 1, "C")
        self.cell(0, 10, "My Company Detailed Invoice", 0, 1, "C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        add_unicode_fonts(self)
        self.set_font("NotoArabic", "I", 8) if add_unicode_fonts(self) else self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")

# NEW FUNCTION: Generate Excel-like monthly invoice PDF
def generate_excel_like_monthly_invoice_pdf(company_data, excel_data):
    """Generate Excel-like monthly invoice PDF showing payment status for each client"""
    pdf = ExcelLikeInvoicePDF()
    add_unicode_fonts(pdf)
    pdf.add_page()
    
    # Company and period information
    pdf.set_font("NotoArabic", "B", 14) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, f"Company: {safe_text(company_data['name'])}", 0, 1, "L")
    pdf.cell(0, 10, f"Period: {excel_data['period']['monthName']} {excel_data['period']['year']}", 0, 1, "L")
    pdf.ln(10)
    
    # Table header
    pdf.set_font("NotoArabic", "B", 10) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 10)
    
    # Column widths
    col_widths = [40, 25, 25, 25, 25, 20]  # Client, Date, Amount, Paid, Due, Status
    
    pdf.cell(col_widths[0], 8, "Client Name", 1, 0, "C")
    pdf.cell(col_widths[1], 8, "Arrival Date", 1, 0, "C")
    pdf.cell(col_widths[2], 8, "Amount(USD)", 1, 0, "C")
    pdf.cell(col_widths[3], 8, "Paid", 1, 0, "C")
    pdf.cell(col_widths[4], 8, "Due", 1, 0, "C")
    pdf.cell(col_widths[5], 8, "Status", 1, 1, "C")
    
    # Table data
    pdf.set_font("NotoArabic", "", 9) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "", 9)
    
    for client in excel_data['clients']:
        # Determine row color based on payment status
        if client['paymentStatus'] == 'paid':
            pdf.set_fill_color(144, 238, 144)  # Light green
        elif client['paymentStatus'] == 'partial':
            pdf.set_fill_color(255, 255, 0)   # Yellow
        else:
            pdf.set_fill_color(255, 182, 193)  # Light red
        
        client_name = safe_text(client['clientName'][:25])
        arrival_date = client['arrivalDate'][:10] if client['arrivalDate'] else "N/A"
        
        pdf.cell(col_widths[0], 6, client_name, 1, 0, "L", True)
        pdf.cell(col_widths[1], 6, arrival_date, 1, 0, "C", True)
        pdf.cell(col_widths[2], 6, f"${client['totalAmount']:.0f}", 1, 0, "R", True)
        pdf.cell(col_widths[3], 6, f"${client['paidAmount']:.0f}", 1, 0, "R", True)
        pdf.cell(col_widths[4], 6, f"${client['dueAmount']:.0f}", 1, 0, "R", True)
        
        status_text = "PAID" if client['paymentStatus'] == 'paid' else "DUE"
        pdf.cell(col_widths[5], 6, status_text, 1, 1, "C", True)
    
    # Summary section
    pdf.ln(5)
    pdf.set_font("NotoArabic", "B", 12) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 12)
    
    # Summary table
    summary_col_widths = [80, 40]
    
    pdf.set_fill_color(173, 216, 230)  # Light blue
    pdf.cell(summary_col_widths[0], 8, "SUMMARY", 1, 0, "L", True)
    pdf.cell(summary_col_widths[1], 8, "Amount (USD)", 1, 1, "C", True)
    
    pdf.set_fill_color(255, 255, 255)  # White
    pdf.cell(summary_col_widths[0], 6, "Total Amount", 1, 0, "L", True)
    pdf.cell(summary_col_widths[1], 6, f"${excel_data['summary']['totalAmount']:.0f}", 1, 1, "R", True)
    
    pdf.set_fill_color(144, 238, 144)  # Light green
    pdf.cell(summary_col_widths[0], 6, "Total Paid", 1, 0, "L", True)
    pdf.cell(summary_col_widths[1], 6, f"${excel_data['summary']['totalPaid']:.0f}", 1, 1, "R", True)
    
    pdf.set_fill_color(255, 182, 193)  # Light red
    pdf.cell(summary_col_widths[0], 6, "Total Due", 1, 0, "L", True)
    pdf.cell(summary_col_widths[1], 6, f"${excel_data['summary']['totalDue']:.0f}", 1, 1, "R", True)
    
    return pdf

# NEW FUNCTION: Generate detailed invoice for my company
def generate_my_company_detailed_invoice_pdf(company_data, excel_data):
    """Generate detailed invoice for my company showing costs, profits, etc."""
    pdf = MyCompanyDetailedInvoicePDF()
    add_unicode_fonts(pdf)
    pdf.add_page()
    
    # Company and period information
    pdf.set_font("NotoArabic", "B", 14) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, f"Partner Company: {safe_text(company_data['name'])}", 0, 1, "L")
    pdf.cell(0, 10, f"Period: {excel_data['period']['monthName']} {excel_data['period']['year']}", 0, 1, "L")
    pdf.cell(0, 10, f"Invoice Date: {date.today().strftime('%Y-%m-%d')}", 0, 1, "L")
    pdf.ln(10)
    
    # Detailed breakdown by client
    pdf.set_font("NotoArabic", "B", 12) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "Detailed Service Breakdown", 0, 1, "C")
    pdf.ln(5)
    
    # For each client, show detailed services
    for client in excel_data['clients']:
        pdf.set_font("NotoArabic", "B", 11) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, f"Client: {safe_text(client['clientName'])}", 0, 1, "L")
        pdf.cell(0, 6, f"Arrival: {client['arrivalDate'][:10] if client['arrivalDate'] else 'N/A'}", 0, 1, "L")
        pdf.ln(2)
        
        # Service details table header
        pdf.set_font("NotoArabic", "B", 9) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 9)
        service_col_widths = [60, 30, 30, 30]
        
        pdf.cell(service_col_widths[0], 6, "Service", 1, 0, "C")
        pdf.cell(service_col_widths[1], 6, "Cost", 1, 0, "C")
        pdf.cell(service_col_widths[2], 6, "Selling", 1, 0, "C")
        pdf.cell(service_col_widths[3], 6, "Profit", 1, 1, "C")
        
        # Here you would get actual service details for the client
        # For now, we'll show a summary row
        pdf.set_font("NotoArabic", "", 9) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "", 9)
        
        # Calculate estimated cost (70% of selling price for example)
        estimated_cost = client['totalAmount'] * 0.7
        estimated_profit = client['totalAmount'] - estimated_cost
        
        pdf.cell(service_col_widths[0], 6, "Service Package", 1, 0, "L")
        pdf.cell(service_col_widths[1], 6, f"${estimated_cost:.0f}", 1, 0, "R")
        pdf.cell(service_col_widths[2], 6, f"${client['totalAmount']:.0f}", 1, 0, "R")
        pdf.cell(service_col_widths[3], 6, f"${estimated_profit:.0f}", 1, 1, "R")
        
        pdf.ln(5)
    
    # Overall summary
    pdf.set_font("NotoArabic", "B", 12) if add_unicode_fonts(pdf) else pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "Monthly Summary", 0, 1, "C")
    pdf.ln(2)
    
    # Calculate totals
    total_revenue = excel_data['summary']['totalAmount']
    estimated_total_cost = total_revenue * 0.7
    estimated_total_profit = total_revenue - estimated_total_cost
    
    summary_col_widths = [100, 40]
    
    pdf.set_fill_color(173, 216, 230)  # Light blue
    pdf.cell(summary_col_widths[0], 8, "Financial Summary", 1, 0, "L", True)
    pdf.cell(summary_col_widths[1], 8, "Amount (USD)", 1, 1, "C", True)
    
    pdf.set_fill_color(255, 255, 255)  # White
    pdf.cell(summary_col_widths[0], 6, "Total Revenue", 1, 0, "L", True)
    pdf.cell(summary_col_widths[1], 6, f"${total_revenue:.0f}", 1, 1, "R", True)
    
    pdf.cell(summary_col_widths[0], 6, "Estimated Total Cost", 1, 0, "L", True)
    pdf.cell(summary_col_widths[1], 6, f"${estimated_total_cost:.0f}", 1, 1, "R", True)
    
    pdf.set_fill_color(144, 238, 144)  # Light green
    pdf.cell(summary_col_widths[0], 6, "Estimated Profit", 1, 0, "L", True)
    pdf.cell(summary_col_widths[1], 6, f"${estimated_total_profit:.0f}", 1, 1, "R", True)
    
    return pdf

# NEW ROUTE: Generate Excel-like monthly invoice
@invoices_bp.route("/invoices/monthly-excel/generate", methods=["POST"])
def generate_excel_like_monthly_invoice():
    """Generate Excel-like monthly invoice PDF"""
    try:
        data = request.get_json()
        company_id = data.get('companyId')
        month = data.get('month', datetime.now().month)
        year = data.get('year', datetime.now().year)
        
        if not company_id:
            return jsonify({"error": "Company ID is required"}), 400
        
        # Get company data
        company = Company.query.get_or_404(company_id)
        
        # Get Excel-like data (this would call the companies endpoint)
        from flask import current_app
        with current_app.test_client() as client:
            response = client.get(f'/api/companies/{company_id}/monthly-invoice-excel?month={month}&year={year}')
            excel_data = response.get_json()
        
        # Generate PDF
        pdf = generate_excel_like_monthly_invoice_pdf(company.__dict__, excel_data)
        
        # Save PDF
        invoices_dir = os.path.join(os.path.dirname(__file__), "invoices")
        if not os.path.exists(invoices_dir):
            os.makedirs(invoices_dir)
        
        pdf_filename = f"excel_invoice_{company.name}_{month}_{year}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = os.path.join(invoices_dir, pdf_filename)
        pdf.output(pdf_path)
        
        return jsonify({
            "message": "Excel-like monthly invoice generated successfully",
            "pdfPath": f"/api/invoices/download/{pdf_filename}",
            "filename": pdf_filename
        }), 201
        
    except Exception as e:
        logging.error(f"Error generating Excel-like monthly invoice: {e}")
        return jsonify({"error": str(e)}), 500

# NEW ROUTE: Generate detailed invoice for my company
@invoices_bp.route("/invoices/my-company-detailed/generate", methods=["POST"])
def generate_my_company_detailed_invoice():
    """Generate detailed invoice for my company"""
    try:
        data = request.get_json()
        company_id = data.get('companyId')
        month = data.get('month', datetime.now().month)
        year = data.get('year', datetime.now().year)
        
        if not company_id:
            return jsonify({"error": "Company ID is required"}), 400
        
        # Get company data
        company = Company.query.get_or_404(company_id)
        
        # Get Excel-like data (this would call the companies endpoint)
        from flask import current_app
        with current_app.test_client() as client:
            response = client.get(f'/api/companies/{company_id}/monthly-invoice-excel?month={month}&year={year}')
            excel_data = response.get_json()
        
        # Generate PDF
        pdf = generate_my_company_detailed_invoice_pdf(company.__dict__, excel_data)
        
        # Save PDF
        invoices_dir = os.path.join(os.path.dirname(__file__), "invoices")
        if not os.path.exists(invoices_dir):
            os.makedirs(invoices_dir)
        
        pdf_filename = f"my_company_detailed_{company.name}_{month}_{year}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = os.path.join(invoices_dir, pdf_filename)
        pdf.output(pdf_path)
        
        return jsonify({
            "message": "My company detailed invoice generated successfully",
            "pdfPath": f"/api/invoices/download/{pdf_filename}",
            "filename": pdf_filename
        }), 201
        
    except Exception as e:
        logging.error(f"Error generating my company detailed invoice: {e}")
        return jsonify({"error": str(e)}), 500

# ==========================================
# END OF NEW FEATURES
# ==========================================

