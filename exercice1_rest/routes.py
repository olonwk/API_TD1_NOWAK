from flask import jsonify, request
from models import Item

_items = [Item(id=1, name="Item 1", description="Premier item")]


def register_routes(app):
    @app.route("/items", methods=["GET"])
    def get_items():
        return jsonify([item.__dict__ for item in _items])

    @app.route("/items", methods=["POST"])
    def create_item():
        data = request.json or {}
        item = Item(id=len(_items) + 1, name=data.get("name", ""), description=data.get("description", ""))
        _items.append(item)
        return jsonify(item.__dict__), 201
