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