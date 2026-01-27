from routes.virtual.usage import load_usage_routes

# Register usage routes with the virtual blueprint
load_usage_routes()

# Import magic link routes to register them with the blueprint
from routes.virtual import magic_link  # noqa: F401
