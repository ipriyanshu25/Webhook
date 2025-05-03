from flask import Blueprint

# Create API Blueprint
api_bp = Blueprint('api', __name__)

# Import all API routes here
from .subscription import subscription_bp
from .webhook import webhook_bp
from .status import status_bp
