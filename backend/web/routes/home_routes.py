from flask import Blueprint


def create_home_blueprint() -> Blueprint:
    bp = Blueprint('home', __name__)

    @bp.route('/')
    def home():
        return "WESAD Backend API działa"

    return bp
