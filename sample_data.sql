-- Sample data for Tourism Booking & Management System

-- Insert sample companies
INSERT INTO company (name, contact_person, email, phone) VALUES
('ABC Tours', 'Robert Johnson', 'contact@abctours.com', '+1-555-0100'),
('Travel Pro', 'Lisa Anderson', 'info@travelpro.com', '+1-555-0200'),
('Adventure Co', 'Mark Davis', 'hello@adventureco.com', '+1-555-0300');

-- Insert sample clients
INSERT INTO client (first_name, last_name, email, phone, company_id) VALUES
('John', 'Smith', 'john.smith@email.com', '+1-555-0123', 1),
('Sarah', 'Johnson', 'sarah.j@email.com', '+1-555-0124', 2),
('Mike', 'Wilson', 'mike.wilson@email.com', '+1-555-0125', 1),
('Emma', 'Davis', 'emma.davis@email.com', '+1-555-0126', 3),
('David', 'Brown', 'david.brown@email.com', '+1-555-0127', 2);

-- Insert sample drivers
INSERT INTO driver (first_name, last_name, phone, email, license_number) VALUES
('Ahmed', 'Hassan', '+90-555-0123', 'ahmed.hassan@email.com', 'DL123456789'),
('Mehmet', 'Yilmaz', '+90-555-0124', 'mehmet.y@email.com', 'DL987654321'),
('Ali', 'Demir', '+90-555-0125', 'ali.demir@email.com', 'DL456789123'),
('Mustafa', 'Kaya', '+90-555-0126', 'mustafa.kaya@email.com', 'DL789123456'),
('Osman', 'Celik', '+90-555-0127', 'osman.celik@email.com', 'DL321654987');

-- Insert sample vehicles
INSERT INTO vehicle (model, plate_number, category, capacity) VALUES
('Toyota Camry', 'ABC123', 'Sedan', 4),
('Mercedes Sprinter', 'XYZ789', 'Van', 15),
('BMW X5', 'DEF456', 'SUV', 7),
('Ford Transit', 'GHI789', 'Minibus', 12),
('Audi A6', 'JKL012', 'Sedan', 4);

-- Insert sample bookings
INSERT INTO booking (service_type, service_name, client_id, driver_id, vehicle_id, start_date, end_date, cost_to_company, selling_price, notes, status) VALUES
('Tour', 'Uzungöl Tour', 1, 1, 1, '2024-12-15', '2024-12-15', 150.00, 250.00, 'Pick up from hotel at 9 AM', 'confirmed'),
('Transfer', 'Airport Transfer', 2, 2, 2, '2024-12-16', '2024-12-16', 30.00, 50.00, 'Flight arrives at 14:30', 'pending'),
('Hotel', 'Hilton Hotel', 3, NULL, NULL, '2024-12-17', '2024-12-20', 120.00, 180.00, 'Standard room with breakfast', 'confirmed'),
('Vehicle', 'Car Rental', 4, 3, 3, '2024-12-18', '2024-12-20', 80.00, 120.00, 'Self-drive rental', 'pending'),
('Tour', 'Bosphorus Cruise', 5, 4, 4, '2024-12-19', '2024-12-19', 100.00, 150.00, 'Evening cruise with dinner', 'confirmed');

-- Insert sample admin user (password should be hashed in production)
INSERT INTO user (username, password, email, role) VALUES
('admin', 'admin123', 'admin@tourismmanager.com', 'admin'),
('staff', 'staff123', 'staff@tourismmanager.com', 'staff');

