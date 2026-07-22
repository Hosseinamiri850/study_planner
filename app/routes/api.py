from flask import Blueprint, jsonify, request

from app.utils.auth import login_required
from translator import auto_translate, is_available as translator_available


api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/translate", methods=["POST"])
@login_required
def translate():
    text = (request.get_json(silent=True) or {}).get("text", "").strip()
    if not text:
        return jsonify({"error": "متن خالی است"}), 400
    return jsonify(auto_translate(text))


@api_bp.route("/translator-status")
def translator_status():
    return jsonify({"available": translator_available()})
