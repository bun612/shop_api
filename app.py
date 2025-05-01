from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)

DB_NAME = 'ShopDB.db'

# --- Database ---
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                image TEXT,
                description TEXT
            );
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                order_date DATETIME,
                total REAL,
                FOREIGN KEY(customer_id) REFERENCES customers(id)
            );
            CREATE TABLE IF NOT EXISTS order_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                product_id INTEGER,
                quantity INTEGER,
                price REAL,
                FOREIGN KEY(order_id) REFERENCES orders(id),
                FOREIGN KEY(product_id) REFERENCES products(id)
            );
        ''')

# --- Routes ---

@app.route('/')
def home():
    return jsonify({
        "message": "Welcome to Shop API",
        "endpoints": {
            "/products": "List all products",
            "/init-data": "Init sample data",
            "/customers": "POST new customer",
            "/orders": "POST new order",
            "/orders/<id>": "GET order detail"
        }
    })

@app.route('/init-data')
def init_sample_data():
    try:
        init_db()
        with sqlite3.connect(DB_NAME) as conn:
            conn.executescript('''
                DELETE FROM order_details;
                DELETE FROM orders;
                DELETE FROM customers;
                DELETE FROM products;
            ''')
            products = [
                ("iPhone 14 Pro Max", 27990000, 
                 "https://th.bing.com/th/id/OIP.HlFVZumCmO9aSI_w5x7tIgHaEK?rs=1&pid=ImgDetMain", 
                 "iPhone 14 Pro Max 128GB - Sang trọng, cao cấp"),
                ("Samsung Galaxy S23 Ultra", 23990000, 
                 "https://cdn.tgdd.vn/Products/Images/42/249948/samsung-galaxy-s23-ultra-thumb-xanh-600x600.jpg",
                 "Samsung Galaxy S23 Ultra - Siêu phẩm Galaxy với bút S-Pen"),
                ("Xiaomi 13 Pro", 19990000,
                 "https://cdn.tgdd.vn/Products/Images/42/267984/xiaomi-13-pro-thumb-1-600x600.jpg",
                 "Xiaomi 13 Pro - Camera Leica chuyên nghiệp")
            ]
            conn.executemany(
                'INSERT INTO products (name, price, image, description) VALUES (?, ?, ?, ?)', 
                products
            )
        return jsonify({"message": "Sample data initialized", "count": len(products)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/products')
def get_products():
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.execute('SELECT * FROM products')
            products = [
                {'id': row[0], 'name': row[1], 'price': row[2], 'image': row[3], 'description': row[4]}
                for row in cursor
            ]
        return jsonify(products)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/customers', methods=['POST'])
def create_customer():
    try:
        data = request.get_json()
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.execute('INSERT INTO customers (name, phone) VALUES (?, ?)',
                                  (data['name'], data['phone']))
            return jsonify({"message": "Customer created", "customer_id": cursor.lastrowid}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/products/<int:id>', methods=['PUT'])
def update_product(id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.execute('''
                UPDATE products
                SET name = ?, price = ?, image = ?, description = ?
                WHERE id = ?
            ''', (data['name'], data['price'], data['image'], data['description'], id))

            if cursor.rowcount == 0:
                return jsonify({"error": "Product not found"}), 404

            return jsonify({"message": "Product updated successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.execute('DELETE FROM products WHERE id = ?', (id,))
            if cursor.rowcount == 0:
                return jsonify({"error": "Product not found"}), 404
            return jsonify({"message": "Product deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#--------------------------------------------------#

@app.route('/orders', methods=['POST'])
def create_order():
    try:
        data = request.get_json()
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.execute('''
                INSERT INTO orders (customer_id, order_date, total)
                VALUES (?, datetime('now'), ?)
            ''', (data['customer_id'], data['total']))
            order_id = cursor.lastrowid
            for product in data['products']:
                conn.execute('''
                    INSERT INTO order_details (order_id, product_id, quantity, price)
                    VALUES (?, ?, ?, ?)
                ''', (order_id, product['product_id'], product['quantity'], product['price']))
            return jsonify({"message": "Order created", "order_id": order_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/orders/<int:order_id>')
def get_order(order_id):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            order_cursor = conn.execute('''
                SELECT o.id, o.customer_id, o.order_date, o.total,
                       c.name, c.phone
                FROM orders o
                JOIN customers c ON o.customer_id = c.id
                WHERE o.id = ?
            ''', (order_id,))
            order = order_cursor.fetchone()
            if not order:
                return jsonify({"error": "Order not found"}), 404

            details_cursor = conn.execute('''
                SELECT od.product_id, p.name, od.quantity, od.price
                FROM order_details od
                JOIN products p ON od.product_id = p.id
                WHERE od.order_id = ?
            ''', (order_id,))
            details = [
                {'product_id': row[0], 'product_name': row[1], 'quantity': row[2], 'price': row[3]}
                for row in details_cursor
            ]
            return jsonify({
                'order_id': order[0],
                'customer_id': order[1],
                'order_date': order[2],
                'total': order[3],
                'customer_name': order[4],
                'customer_phone': order[5],
                'details': details
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Start ---
if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=1234, debug=True)
