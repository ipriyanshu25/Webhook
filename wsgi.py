from app import create_app
from app import models
from app import utils
from app import tests
from app import api
from app import task

# Create the Flask application
app = create_app()

# Run the application if this is the main module
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)  # Run with debug mode for local development
