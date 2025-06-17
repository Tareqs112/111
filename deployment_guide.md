# Tourism Booking & Management System - Deployment Guide

## System Requirements
- Python 3.8 or higher
- SQLite (included with Python)
- Web server (Apache/Nginx) or shared hosting with Python support

## Deployment Steps for Hostinger/cPanel

### 1. Prepare Files
1. Upload all files from the `tourism_backend` directory to your hosting account
2. Upload all files from the `tourism-booking-system/dist` directory (after building) to the public_html folder

### 2. Backend Setup
1. Navigate to your hosting control panel
2. Create a Python application (if supported) or use the file manager
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 3. Database Setup
1. The system uses SQLite by default, which works on most shared hosting
2. The database file will be created automatically at `src/database/app.db`
3. To populate with sample data, run the SQL commands from `sample_data.sql`

### 4. Frontend Setup
1. Build the React application:
   ```bash
   cd tourism-booking-system
   npm run build
   ```
2. Upload the contents of the `dist` folder to your public_html directory
3. Update the API base URL in the frontend to point to your backend

### 5. Configuration
1. Update email settings in `src/routes/notifications.py`:
   - Set your SMTP server details
   - Configure sender email and password
2. Update the secret key in `src/main.py`
3. Set proper file permissions (755 for directories, 644 for files)

### 6. Testing
1. Access your website URL
2. Test all functionality:
   - Add clients, companies, drivers, vehicles
   - Create bookings
   - Generate invoices
   - Test notifications (if email is configured)

## Default Admin Credentials
- Username: admin
- Password: admin123

**Important: Change these credentials immediately after deployment!**

## File Structure
```
tourism_backend/
├── src/
│   ├── models/
│   ├── routes/
│   ├── static/
│   ├── database/
│   └── main.py
├── requirements.txt
├── sample_data.sql
└── deployment_guide.md

tourism-booking-system/
├── src/
├── public/
├── package.json
└── dist/ (after build)
```

## Troubleshooting
1. **Database Issues**: Ensure the database directory has write permissions
2. **Import Errors**: Check that all dependencies are installed
3. **CORS Issues**: Verify that flask-cors is properly configured
4. **File Upload Issues**: Check file permissions and directory structure

## Security Notes
- Change default passwords immediately
- Use environment variables for sensitive configuration
- Enable HTTPS in production
- Regularly backup the database
- Keep dependencies updated

## Support
For technical support, refer to the system documentation or contact your hosting provider for Python/Flask specific issues.

