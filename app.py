from main import app

# This file is used to expose the app variable for imports in other modules
# The actual application configuration is in main.py

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)