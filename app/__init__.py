from flask import Flask
from flask_pymongo import PyMongo
from flask_swagger_ui import get_swaggerui_blueprint
from app.config import Config

# Initialize MongoDB client
mongo = PyMongo()

def create_app(config_class=Config):
    """
    Factory function to create and configure the Flask application.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize PyMongo with the app
    mongo.init_app(app)
    
    # Import models and utils inside the function to avoid circular imports
    from app import models, utils
    
    # Register blueprints
    from app.api.subscription import subscription_bp
    from app.api.webhook import webhook_bp
    from app.api.status import status_bp
    
    # Register the blueprints with a URL prefix
    app.register_blueprint(subscription_bp, url_prefix='/api/subscriptions')
    app.register_blueprint(webhook_bp, url_prefix='/api/webhooks')
    app.register_blueprint(status_bp, url_prefix='/api/status')
    
    # Configure Swagger UI for API documentation
    SWAGGER_URL = '/api/docs'
    API_URL = '/static/swagger.json'
    
    swaggerui_blueprint = get_swaggerui_blueprint(
        SWAGGER_URL,
        API_URL,
        config={
            'app_name': "Webhook Delivery Service API"
        }
    )
    app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)
    
    # Define a simple route for the index page
    @app.route('/')
    def index():
        return """
        <h1>Webhook Delivery Service</h1>
        <p>API is running. Visit <a href="/api/docs">API Documentation</a> for more information.</p>
        """
    
    return app
