from flask import Flask, jsonify, render_template, request, session, redirect, url_for
import json
import os

app = Flask(__name__)
app.secret_key = "dev-secret-key"

DATA_FILE = os.path.join(os.path.dirname(__file__), "automobileParts.json")


def load_parts():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_cart():
    return session.get("cart", {})


def save_cart(cart):
    session["cart"] = cart
    session.modified = True


def normalize_price(value):
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace("$", "").replace(",", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    return 0.0


@app.route("/")
def index():
    parts = load_parts()
    query = request.args.get("q", "").lower().strip()

    if query:
        def matches(part):
            return (
                query in str(part.get("name", "")).lower()
                or query in str(part.get("description", "")).lower()
                or query in str(part.get("manufacturer", "")).lower()
                or query in str(part.get("price", "")).lower()
            )
        parts = [p for p in parts if matches(p)]

    return render_template("index.html", parts=parts, query=query, cart_count=sum(get_cart().values()))


@app.route("/product/<int:part_id>")
def product_detail(part_id):
    parts = load_parts()
    part = next((p for p in parts if int(p.get("id", -1)) == part_id), None)
    if not part:
        return "Product not found", 404
    return render_template("product.html", part=part, cart_count=sum(get_cart().values()))


@app.route("/cart")
def cart():
    parts = load_parts()
    cart = get_cart()
    items = []
    total = 0.0

    for part in parts:
        pid = str(part.get("id"))
        if pid in cart:
            quantity = cart[pid]
            price = normalize_price(part.get("price", 0))
            subtotal = price * quantity
            total += subtotal
            items.append({
                "part": part,
                "quantity": quantity,
                "subtotal": subtotal
            })

    return render_template("cart.html", items=items, total=total, cart_count=sum(cart.values()))


@app.route("/cart/add/<int:part_id>", methods=["POST"])
def add_to_cart(part_id):
    cart = get_cart()
    key = str(part_id)
    cart[key] = cart.get(key, 0) + 1
    save_cart(cart)
    return redirect(request.referrer or url_for("index"))


@app.route("/cart/remove/<int:part_id>", methods=["POST"])
def remove_from_cart(part_id):
    cart = get_cart()
    key = str(part_id)
    if key in cart:
        cart[key] -= 1
        if cart[key] <= 0:
            del cart[key]
    save_cart(cart)
    return redirect(request.referrer or url_for("cart"))


@app.route("/api/parts", methods=["GET"])
def api_parts():
    parts = load_parts()
    offset = int(request.args.get("offset", 0))
    limit = int(request.args.get("limit", 10))
    return jsonify(parts[offset:offset + limit])


@app.route("/api/parts/<int:part_id>", methods=["GET"])
def api_part_detail(part_id):
    parts = load_parts()
    part = next((p for p in parts if int(p.get("id", -1)) == part_id), None)
    if not part:
        return jsonify({"error": "Part not found"}), 404
    return jsonify(part)


@app.route("/api/parts/search", methods=["GET"])
def api_search_parts():
    parts = load_parts()
    q = request.args.get("q", "").lower().strip()
    min_price = request.args.get("min_price")
    max_price = request.args.get("max_price")

    results = parts

    if q:
        results = [
            p for p in results
            if q in str(p.get("name", "")).lower()
            or q in str(p.get("description", "")).lower()
            or q in str(p.get("manufacturer", "")).lower()
            or q in str(p.get("price", "")).lower()
        ]

    if min_price is not None:
        try:
            min_price = float(min_price)
            results = [p for p in results if normalize_price(p.get("price", 0)) >= min_price]
        except ValueError:
            pass

    if max_price is not None:
        try:
            max_price = float(max_price)
            results = [p for p in results if normalize_price(p.get("price", 0)) <= max_price]
        except ValueError:
            pass

    return jsonify(results)


if __name__ == "__main__":
    app.run(debug=True)
