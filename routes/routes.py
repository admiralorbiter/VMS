from flask import render_template
from routes.auth.routes import auth_bp
from routes.history.routes import history_bp
from routes.volunteers.routes import volunteers_bp
from routes.organizations.routes import organizations_bp
from routes.job_board.routes import job_board_bp
from routes.upcoming_events.routes import upcoming_events_bp
from routes.events.routes import events_bp
from routes.job_board.filters import init_filters


def init_routes(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(volunteers_bp)
    app.register_blueprint(organizations_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(job_board_bp)
    app.register_blueprint(upcoming_events_bp)
    init_filters(app)

    @app.route('/')
    def index():
        return render_template('index.html')