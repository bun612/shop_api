from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Lưu database ở thư mục cố định
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'ShopDB.db')
DB_NAME = DB_PATH

# --- Init database ---
def init_db():
    try:
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
                    order_date TEXT,
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
        print("✅ Database initialized successfully.")
    except Exception as e:
        print("❌ Error during DB initialization:", e)

# --- Helper ---
def connect_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# Thay thế before_first_request bằng câu lệnh thực thi khi khởi động
with app.app_context():
    if not os.path.exists(DB_NAME):
        init_db()
        print("Database created for the first time")

# --- Home ---
@app.route('/')
def home():
    return jsonify({
        "message": "Welcome to Shop API",
        "endpoints": {
            "/products": "List all products",
            "/init-sample-data": "Init sample data (Warning: this deletes existing data)",
            "/customers": "POST new customer",
            "/orders": "POST new order",
            "/orders/<id>": "GET order detail"
        }
    })

# --- Init sample data (RENAMED to be more explicit that it resets data) ---
@app.route('/init-sample-data')
def init_sample_data():
    try:
        with connect_db() as conn:
            # CLEAR WARNING: This deletes all existing data
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
        return jsonify({"message": "Sample data initialized", "count": len(products), 
                       "warning": "All existing data was deleted"})
    except Exception as e:
        print("❌ Error initializing sample data:", e)
        return jsonify({"error": str(e)}), 500

# --- GET all products ---
@app.route('/products', methods=['GET'])
def get_products():
    try:
        with connect_db() as conn:
            cursor = conn.execute('SELECT * FROM products')
            rows = cursor.fetchall()
            products = [dict(row) for row in rows]
        return jsonify(products)
    except Exception as e:
        print("❌ Error in /products:", e)
        return jsonify({"error": str(e)}), 500

# --- GET a specific product ---
@app.route('/products/<int:id>', methods=['GET'])
def get_product(id):
    try:
        with connect_db() as conn:
            cursor = conn.execute('SELECT * FROM products WHERE id = ?', (id,))
            product = cursor.fetchone()
            if product is None:
                return jsonify({"error": "Product not found"}), 404
        return jsonify(dict(product))
    except Exception as e:
        print("❌ Error in GET /products/<id>:", e)
        return jsonify({"error": str(e)}), 500

# --- POST create product ---
@app.route('/products', methods=['POST'])
def create_product():
    try:
        data = request.get_json()
        with connect_db() as conn:
            cursor = conn.execute('''
                INSERT INTO products (name, price, image, description)
                VALUES (?, ?, ?, ?)
            ''', (data['name'], data['price'], data['image'], data['description']))
            product_id = cursor.lastrowid
        return jsonify({"message": "Product created", "id": product_id}), 201
    except Exception as e:
        print("❌ Error in POST /products:", e)
        return jsonify({"error": str(e)}), 500

# --- PUT update product ---
@app.route('/products/<int:id>', methods=['PUT'])
def update_product(id):
    try:
        data = request.get_json()
        with connect_db() as conn:
            cursor = conn.execute('''
                UPDATE products
                SET name = ?, price = ?, image = ?, description = ?
                WHERE id = ?
            ''', (data['name'], data['price'], data['image'], data['description'], id))
            if cursor.rowcount == 0:
                return jsonify({"error": "Product not found"}), 404
        return jsonify({"message": "Product updated"})
    except Exception as e:
        print("❌ Error in PUT /products:", e)
        return jsonify({"error": str(e)}), 500

# --- DELETE product ---
@app.route('/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    try:
        with connect_db() as conn:
            # Kiểm tra xem sản phẩm có trong đơn hàng nào không
            cursor = conn.execute('''
                SELECT COUNT(*) as count FROM order_details WHERE product_id = ?
            ''', (id,))
            count = cursor.fetchone()['count']
            if count > 0:
                return jsonify({"error": "Cannot delete product used in orders"}), 400

            cursor = conn.execute('DELETE FROM products WHERE id = ?', (id,))
            if cursor.rowcount == 0:
                return jsonify({"error": "Product not found"}), 404
        return jsonify({"message": "Product deleted"})
    except Exception as e:
        print("❌ Error in DELETE /products:", e)
        return jsonify({"error": str(e)}), 500

# --- GET all customers ---
@app.route('/customers', methods=['GET'])
def get_customers():
    try:
        with connect_db() as conn:
            cursor = conn.execute('SELECT * FROM customers')
            rows = cursor.fetchall()
            customers = [dict(row) for row in rows]
        return jsonify(customers)
    except Exception as e:
        print("❌ Error in GET /customers:", e)
        return jsonify({"error": str(e)}), 500

# --- GET a specific customer ---
@app.route('/customers/<int:id>', methods=['GET'])
def get_customer(id):
    try:
        with connect_db() as conn:
            cursor = conn.execute('SELECT * FROM customers WHERE id = ?', (id,))
            customer = cursor.fetchone()
            if customer is None:
                return jsonify({"error": "Customer not found"}), 404
        return jsonify(dict(customer))
    except Exception as e:
        print("❌ Error in GET /customers/<id>:", e)
        return jsonify({"error": str(e)}), 500

# --- POST create customer ---
@app.route('/customers', methods=['POST'])
def create_customer():
    try:
        data = request.get_json()
        if not data or 'name' not in data or 'phone' not in data:
            return jsonify({"error": "Missing name or phone"}), 400
        
        with connect_db() as conn:
            cursor = conn.execute('''
                INSERT INTO customers (name, phone)
                VALUES (?, ?)
            ''', (data['name'], data['phone']))
            customer_id = cursor.lastrowid
        
        return jsonify({"message": "Customer created", "id": customer_id}), 201
    except Exception as e:
        print("❌ Error in POST /customers:", e)
        return jsonify({"error": str(e)}), 500

# --- PUT update customer ---
@app.route('/customers/<int:id>', methods=['PUT'])
def update_customer(id):
    try:
        data = request.get_json()
        with connect_db() as conn:
            cursor = conn.execute('''
                UPDATE customers
                SET name = ?, phone = ?
                WHERE id = ?
            ''', (data['name'], data['phone'], id))
            if cursor.rowcount == 0:
                return jsonify({"error": "Customer not found"}), 404
        return jsonify({"message": "Customer updated"})
    except Exception as e:
        print("❌ Error in PUT /customers/<id>:", e)
        return jsonify({"error": str(e)}), 500

# --- DELETE customer ---
@app.route('/customers/<int:id>', methods=['DELETE'])
def delete_customer(id):
    try:
        with connect_db() as conn:
            # Kiểm tra xem khách hàng có đơn hàng nào không
            cursor = conn.execute('SELECT COUNT(*) as count FROM orders WHERE customer_id = ?', (id,))
            count = cursor.fetchone()['count']
            if count > 0:
                return jsonify({"error": "Cannot delete customer with orders"}), 400
                
            cursor = conn.execute('DELETE FROM customers WHERE id = ?', (id,))
            if cursor.rowcount == 0:
                return jsonify({"error": "Customer not found"}), 404
        return jsonify({"message": "Customer deleted"})
    except Exception as e:
        print("❌ Error in DELETE /customers/<id>:", e)
        return jsonify({"error": str(e)}), 500

# --- GET all orders ---
@app.route('/orders', methods=['GET'])
def get_orders():
    try:
        with connect_db() as conn:
            cursor = conn.execute('''
                SELECT o.*, c.name AS customer_name, c.phone AS customer_phone
                FROM orders o
                JOIN customers c ON o.customer_id = c.id
            ''')
            rows = cursor.fetchall()
            orders = [dict(row) for row in rows]
        return jsonify(orders)
    except Exception as e:
        print("❌ Error in GET /orders:", e)
        return jsonify({"error": str(e)}), 500

# --- POST create order ---
@app.route('/orders', methods=['POST'])
def create_order():
    try:
        data = request.get_json()
        print("Received order data:", data)  # Debug log
        
        if not data or 'products' not in data:
            return jsonify({"error": "Invalid order data"}), 400
        
        with connect_db() as conn:
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Kiểm tra khách hàng tồn tại
            cursor = conn.execute('SELECT id FROM customers WHERE id = ?', (data['customer_id'],))
            customer = cursor.fetchone()
            if not customer:
                return jsonify({"error": f"Customer ID {data['customer_id']} not found"}), 404
            
            # Tính toán tổng tiền từ các sản phẩm để đảm bảo chính xác
            total = 0
            for product in data['products']:
                total += product['price'] * product['quantity']
            
            # Tạo đơn hàng mới với tổng tiền được tính lại
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor = conn.execute('''
                INSERT INTO orders (customer_id, order_date, total)
                VALUES (?, ?, ?)
            ''', (data['customer_id'], current_time, total))
            order_id = cursor.lastrowid
            
            # Tạo chi tiết đơn hàng
            for product in data['products']:
                # Kiểm tra sản phẩm tồn tại
                cursor = conn.execute('SELECT id FROM products WHERE id = ?', (product['product_id'],))
                if not cursor.fetchone():
                    return jsonify({"error": f"Product ID {product['product_id']} not found"}), 404
                
                conn.execute('''
                    INSERT INTO order_details (order_id, product_id, quantity, price)
                    VALUES (?, ?, ?, ?)
                ''', (order_id, product['product_id'], product['quantity'], product['price']))
            
        return jsonify({"message": "Order created", "order_id": order_id, "total": total}), 201
    except Exception as e:
        print("❌ Error in POST /orders:", e)
        return jsonify({"error": str(e)}), 500

# --- GET order details ---
@app.route('/orders/<int:id>', methods=['GET'])
def get_order(id):
    try:
        with connect_db() as conn:
            # Lấy thông tin đơn hàng
            cursor = conn.execute('''
                SELECT o.id, o.order_date, o.total, c.id as customer_id, c.name as customer_name, c.phone as customer_phone
                FROM orders o
                JOIN customers c ON o.customer_id = c.id
                WHERE o.id = ?
            ''', (id,))
            order = cursor.fetchone()
            
            if not order:
                return jsonify({"error": "Order not found"}), 404
            
            order_dict = dict(order)
            
            # Lấy chi tiết đơn hàng
            cursor = conn.execute('''
                SELECT od.id, od.quantity, od.price, p.id as product_id, p.name as product_name, 
                       p.image as product_image, p.description as product_description
                FROM order_details od
                JOIN products p ON od.product_id = p.id
                WHERE od.order_id = ?
            ''', (id,))
            
            details = [dict(row) for row in cursor.fetchall()]
            order_dict['details'] = details
            
            # Kiểm tra và sửa total nếu bằng 0
            if order_dict['total'] == 0 and details:
                calculated_total = sum(detail['price'] * detail['quantity'] for detail in details)
                if calculated_total > 0:
                    # Cập nhật tổng tiền trong database
                    conn.execute('UPDATE orders SET total = ? WHERE id = ?', 
                               (calculated_total, id))
                    order_dict['total'] = calculated_total
                    print(f"Fixed zero total for order {id}, new total: {calculated_total}")
            
        return jsonify(order_dict)
    except Exception as e:
        print("❌ Error in GET /orders/<id>:", e)
        return jsonify({"error": str(e)}), 500

# --- PUT update order ---
@app.route('/orders/<int:id>', methods=['PUT'])
def update_order(id):
    try:
        data = request.get_json()
        with connect_db() as conn:
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Kiểm tra đơn hàng tồn tại
            cursor = conn.execute('SELECT id FROM orders WHERE id = ?', (id,))
            if cursor.fetchone() is None:
                return jsonify({"error": "Order not found"}), 404
            
            # Kiểm tra khách hàng tồn tại
            if 'customer_id' in data:
                cursor = conn.execute('SELECT id FROM customers WHERE id = ?', (data['customer_id'],))
                if cursor.fetchone() is None:
                    return jsonify({"error": f"Customer ID {data['customer_id']} not found"}), 404
                
                # Cập nhật thông tin đơn hàng
                conn.execute('''
                    UPDATE orders
                    SET customer_id = ?, total = ?
                    WHERE id = ?
                ''', (data['customer_id'], data['total'], id))
            
            # Nếu có update chi tiết đơn hàng
            if 'products' in data:
                # Xóa chi tiết cũ
                conn.execute('DELETE FROM order_details WHERE order_id = ?', (id,))
                
                # Thêm chi tiết mới
                for product in data['products']:
                    # Kiểm tra sản phẩm tồn tại
                    cursor = conn.execute('SELECT id FROM products WHERE id = ?', (product['product_id'],))
                    if not cursor.fetchone():
                        return jsonify({"error": f"Product ID {product['product_id']} not found"}), 404
                    
                    conn.execute('''
                        INSERT INTO order_details (order_id, product_id, quantity, price)
                        VALUES (?, ?, ?, ?)
                    ''', (id, product['product_id'], product['quantity'], product['price']))
            
        return jsonify({"message": "Order updated"})
    except Exception as e:
        print("❌ Error in PUT /orders/<id>:", e)
        return jsonify({"error": str(e)}), 500

# --- DELETE order ---
@app.route('/orders/<int:id>', methods=['DELETE'])
def delete_order(id):
    try:
        with connect_db() as conn:
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Kiểm tra đơn hàng tồn tại
            cursor = conn.execute('SELECT id FROM orders WHERE id = ?', (id,))
            if cursor.fetchone() is None:
                return jsonify({"error": "Order not found"}), 404
            
            # Xóa chi tiết đơn hàng
            conn.execute('DELETE FROM order_details WHERE order_id = ?', (id,))
            
            # Xóa đơn hàng
            conn.execute('DELETE FROM orders WHERE id = ?', (id,))
        return jsonify({"message": "Order deleted"})
    except Exception as e:
        print("❌ Error in DELETE /orders/<id>:", e)
        return jsonify({"error": str(e)}), 500

@app.route('/fix-orders-with-zero-total', methods=['GET'])
def fix_orders_with_zero_total():
    try:
        with connect_db() as conn:
            # Tìm tất cả các đơn hàng có total = 0
            cursor = conn.execute('SELECT id FROM orders WHERE total = 0')
            zero_total_orders = [row['id'] for row in cursor.fetchall()]
            
            updated_count = 0
            for order_id in zero_total_orders:
                # Tính tổng tiền dựa trên chi tiết đơn hàng
                cursor = conn.execute('''
                    SELECT SUM(quantity * price) as total 
                    FROM order_details 
                    WHERE order_id = ?
                ''', (order_id,))
                calculated_total = cursor.fetchone()['total'] or 0
                
                if calculated_total > 0:
                    # Cập nhật tổng tiền
                    conn.execute('UPDATE orders SET total = ? WHERE id = ?', 
                               (calculated_total, order_id))
                    updated_count += 1
            
            return jsonify({
                "message": f"Fixed {updated_count} orders with zero total",
                "orders_fixed": zero_total_orders
            })
    except Exception as e:
        print("❌ Error fixing orders with zero total:", e)
        return jsonify({"error": str(e)}), 500

# --- Start server ---
if __name__ == '__main__':
    # Chỉ khởi tạo DB nếu chưa tồn tại
    if not os.path.exists(DB_NAME):
        init_db()
        print("Database created at startup")
    
    # Kiểm tra xem có sản phẩm nào trong DB chưa
    try:
        with connect_db() as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM products')
            count = cursor.fetchone()[0]
            if count == 0:
                print("No products found, you may want to call /init-sample-data")
    except Exception as e:
        print("Error checking products:", e)
    
    app.run(host='0.0.0.0', port=1234, debug=True)