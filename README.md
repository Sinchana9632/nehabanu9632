# MindCare AI

A mental wellness platform with AI-powered insights, mood tracking, and community support.

## Features

- **Mood Tracking**: Monitor your emotional well-being with AI-powered sentiment analysis and daily check-ins
- **Journaling**: Record your thoughts and feelings with AI analysis
- **Community Support**: Connect with others in a safe, anonymous environment
- **Emergency Care**: Advanced crisis detection with automatic alerts

## Setup Instructions

### Prerequisites

- Python 3.9+ installed
- pip package manager

### Installation

1. Clone the repository or download the source code
2. Navigate to the project directory
3. Run the setup script:

```bash
# Windows
run_mindcare.bat

# Linux/Mac
chmod +x run_mindcare.sh
./run_mindcare.sh
```

Or manually install dependencies and run:

```bash
# Create and activate virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```
# MindCare AI - Mental Wellness Platform  

## Running the Website  

You can run the MindCare AI website using one of the following methods:

### Method 1: Using Python HTTP Server (Recommended)  
1. **Run** `run_website_server.bat` (double-click).  
2. A local web server will start, opening the website in your default browser.  
3. Access the website at: [`http://localhost:8000/index.html`](http://localhost:8000/index.html).  
4. **Stop the server** with `Ctrl+C` in the command prompt window.  

### Method 2: Opening HTML Files Directly  
1. **Run** `open_website.bat` (double-click).  
2. The `index.html` file will open in your default browser.  
3. Navigate using the built-in links on the website.  

## Available Pages  
- **Home:** `index.html`  
- **Login:** `login.html`  
- **Register:** `register.html`  
- **Dashboard:** `dashboard.html`  
- **Journal:** `journal.html`  
- **Community:** `community.html`  
- **Wellness:** `wellness.html`  
- **Mood Check-in:** `mood-checkin.html`  

## Test Credentials  
- Use any **username** and **password**, as this demo version has no backend authentication.  

## Notes  
- **Recommended:** Use Python HTTP Server (Method 1) for the best experience.  
- If navigation or links fail, **switch to the server method**.  
- Fully **responsive** and mobile-friendly.  

## Contact  
For any issues or inquiries, reach out via email: [nbanu7337@gmail.com](mailto:nbanu7337@gmail.com)  

4. Open your web browser and navigate to http://localhost:5000

## Project Structure

- `main.py`: Application initialization and configuration
- `models.py`: Database models
- `routes.py`: Application routes and view functions
- `ai_analyzer.py`: AI-powered sentiment analysis
- `templates/`: HTML templates
- `static/`: CSS, JavaScript, and other static assets

## License

MIT License
