from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

import mysql.connector
from functools import wraps
import uuid
import os


# ==================================================
# FLASK APPLICATION
# ==================================================

app = Flask(__name__)

app.secret_key = "warehouse_secret_key_123"

# Every time Flask starts, old browser session becomes invalid.
# So after closing terminal and starting again, login starts fresh.
app.config["SESSION_COOKIE_NAME"] = (
    "warehouse_session_" + uuid.uuid4().hex
)


# ==================================================
# MYSQL CONFIGURATION
# ==================================================


MYSQL_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "localhost"),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", ""),
    "database": os.environ.get("MYSQL_DATABASE", "warehouse_db"),
    "port": int(os.environ.get("MYSQL_PORT", "4000")),
    "ssl_verify_cert": True,
    "ssl_verify_identity": True
}


# ==================================================
# DATABASE CONNECTION
# ==================================================

def get_db():
    connection = mysql.connector.connect(
        host=MYSQL_CONFIG["host"],
        port=MYSQL_CONFIG["port"],
        user=MYSQL_CONFIG["user"],
        password=MYSQL_CONFIG["password"],
        database=MYSQL_CONFIG["database"],
        ssl_ca=os.path.join(
            os.path.dirname(__file__), "certs", "isrgrootx1.pem"
        ),
        ssl_verify_cert=True,
        ssl_verify_identity=True
    )
    return connection


# ==================================================
# CREATE DATABASE
# ==================================================

def create_database():

    connection = mysql.connector.connect(
        host=MYSQL_CONFIG["host"],
        port=int(MYSQL_CONFIG.get("port", 4000)),
        user=MYSQL_CONFIG["user"],
        password=MYSQL_CONFIG["password"]
    )

    cursor = connection.cursor()

    cursor.execute(
        "CREATE DATABASE IF NOT EXISTS warehouse_db"
    )

    cursor.close()
    connection.close()


# ==================================================
# CREATE DATABASE TABLES
# ==================================================

def init_db():

    connection = get_db()

    cursor = connection.cursor()

    # ==================================================
    # EMPLOYEES TABLE
    # ==================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (

            id INT AUTO_INCREMENT PRIMARY KEY,

            employee_id VARCHAR(50)
            UNIQUE NOT NULL,

            name VARCHAR(100)
            NOT NULL,

            password VARCHAR(255)
            NOT NULL,

            department VARCHAR(100)
            NOT NULL
        )
    """)


    # ==================================================
    # ORDERS TABLE
    # ==================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (

            id INT AUTO_INCREMENT PRIMARY KEY,

            order_number VARCHAR(100)
            UNIQUE NOT NULL,

            employee_id VARCHAR(50),

            item_name VARCHAR(200)
            NOT NULL,

            quantity INT
            NOT NULL,

            barcode VARCHAR(100),

            status VARCHAR(50)
            DEFAULT 'Assigned',

            FOREIGN KEY (employee_id)
            REFERENCES employees(employee_id)

            ON DELETE SET NULL

            ON UPDATE CASCADE
        )
    """)


    # ==================================================
    # ADMINS TABLE
    # ==================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (

            id INT AUTO_INCREMENT PRIMARY KEY,

            username VARCHAR(100)
            UNIQUE NOT NULL,

            password VARCHAR(255)
            NOT NULL
        )
    """)

    # ==================================================
# CUSTOMERS TABLE
# ==================================================

    cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                customer_id VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(150) UNIQUE NOT NULL,
                phone VARCHAR(20),
                password VARCHAR(255) NOT NULL
            )
""")


    # ==================================================
# PRODUCTS TABLE
# ==================================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (

        id INT AUTO_INCREMENT PRIMARY KEY,

        product_code VARCHAR(50)
        UNIQUE NOT NULL,

        product_name VARCHAR(150)
        NOT NULL,

        price DECIMAL(10,2)
        NOT NULL,

        stock INT
        DEFAULT 0,

        description VARCHAR(255),

        status VARCHAR(30)
        DEFAULT 'Available'

    )
""")


    # ==================================================
    # DEFAULT EMPLOYEE
    # ==================================================

    cursor.execute("""
        INSERT IGNORE INTO employees
        (
            employee_id,
            name,
            password,
            department
        )

        VALUES
        (
            %s,
            %s,
            %s,
            %s
        )
    """, (
        "EMP001",
        "Demo Employee",
        "1234",
        "Picking"
    ))


    # ==================================================
    # DEFAULT ADMIN
    # ==================================================

    cursor.execute("""
        INSERT IGNORE INTO admins
        (
            username,
            password
        )

        VALUES
        (
            %s,
            %s
        )
    """, (
        "admin",
        "admin123"
    ))


    connection.commit()

    cursor.close()
    connection.close()


# ==================================================
# EMPLOYEE LOGIN REQUIRED
# ==================================================

def employee_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "employee_id" not in session:

            return redirect(
                url_for("login")
            )

        return function(*args, **kwargs)

    return wrapper


# ==================================================
# ADMIN LOGIN REQUIRED
# ==================================================

def admin_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "admin" not in session:

            return redirect(
                url_for("admin_login")
            )

        return function(*args, **kwargs)

    return wrapper


# ==================================================
# FIND EMPLOYEE FOR NEXT DEPARTMENT
# ==================================================

def find_next_employee(cursor, department):

    """
    Find the employee in the requested department
    who currently has the fewest active orders.

    This allows orders to be distributed between
    EMP003 / EMP004 etc.
    """

    cursor.execute("""
        SELECT
            e.employee_id,
            COUNT(o.id) AS active_orders

        FROM employees e

        LEFT JOIN orders o
            ON e.employee_id = o.employee_id

            AND o.status IN (
                'Assigned',
                'Picking',
                'Picked',
                'Packed'
            )

        WHERE LOWER(e.department) = LOWER(%s)

        GROUP BY
            e.employee_id

        ORDER BY
            active_orders ASC,
            e.id ASC

        LIMIT 1

    """, (department,))

    employee = cursor.fetchone()

    if employee:
        return employee["employee_id"]

    return None

def reset_test_orders():

    connection = get_db()
    cursor = connection.cursor()

    # First 4 orders -> EMP001 Picking
    cursor.execute("""
        UPDATE orders
        SET employee_id = 'EMP001',
            status = 'Assigned'
        WHERE order_number IN (
            'ORD001',
            'ORD002',
            'ORD003',
            'ORD004'
        )
    """)

    # Next 4 orders -> EMP002 Picking
    cursor.execute("""
        UPDATE orders
        SET employee_id = 'EMP002',
            status = 'Assigned'
        WHERE order_number IN (
            'ORD005',
            'ORD006',
            'ORD007',
            'ORD008'
        )
    """)

    connection.commit()

    cursor.close()
    connection.close()

# ==================================================
# HOME
# ==================================================

@app.route("/")
def home():

    return redirect(
        url_for("login")
    )


# ==================================================
# EMPLOYEE LOGIN
# ==================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        employee_id = request.form["employee_id"].strip()

        password = request.form["password"]


        connection = get_db()

        cursor = connection.cursor(
            dictionary=True
        )


        cursor.execute("""
            SELECT *
            FROM employees

            WHERE employee_id = %s

            AND password = %s

        """, (
            employee_id,
            password
        ))


        employee = cursor.fetchone()


        cursor.close()
        connection.close()


        if employee:

            session.clear()

            session["employee_id"] = (
                employee["employee_id"]
            )

            session["employee_name"] = (
                employee["name"]
            )

            session["employee_department"] = (
                employee["department"]
            )


            return redirect(
                url_for("employee_dashboard")
            )


        flash(
            "Invalid Employee ID or Password"
        )


    return render_template(
        "login.html"
    )


# ==================================================
# EMPLOYEE DASHBOARD
# ==================================================

@app.route("/employee")
@employee_required
def employee_dashboard():

    employee_id = session["employee_id"]

    department = session.get(
        "employee_department",
        ""
    ).strip().lower()


    connection = get_db()

    cursor = connection.cursor(
        dictionary=True
    )


    # ==================================================
    # PICKING EMPLOYEE
    # ==================================================

    if department == "picking":

        cursor.execute("""
            SELECT *
            FROM orders

            WHERE employee_id = %s

            AND status IN (
                'Assigned',
                'Picking'
            )

            ORDER BY id DESC

        """, (employee_id,))


    # ==================================================
    # PACKING EMPLOYEE
    # ==================================================

    elif department == "packing":

        cursor.execute("""
            SELECT *
            FROM orders

            WHERE employee_id = %s

            AND status IN (
                'Assigned',
                'Picked'
            )

            ORDER BY id DESC

        """, (employee_id,))


    # ==================================================
    # LOADING EMPLOYEE
    # ==================================================

    elif department == "loading":

        cursor.execute("""
            SELECT *
            FROM orders

            WHERE employee_id = %s

            AND status IN (
                'Assigned',
                'Packed'
            )

            ORDER BY id DESC

        """, (employee_id,))


    else:

        cursor.execute("""
            SELECT *
            FROM orders

            WHERE employee_id = %s

            ORDER BY id DESC

        """, (employee_id,))


    orders = cursor.fetchall()


    cursor.close()
    connection.close()


    return render_template(
        "employee_dashboard.html",
        orders=orders,
        department=department
    )


# ==================================================
# PICKING PAGE
# ==================================================

@app.route(
    "/picking/<int:order_id>",
    methods=["GET", "POST"]
)
@employee_required
def picking(order_id):

    employee_id = session["employee_id"]

    department = session.get(
        "employee_department",
        ""
    ).strip().lower()


    # Only Picking employees can use Picking page.

    if department != "picking":

        flash(
            "You are not assigned to Picking."
        )

        return redirect(
            url_for("employee_dashboard")
        )


    connection = get_db()

    cursor = connection.cursor(
        dictionary=True
    )


    # ==================================================
    # GET ORDER
    # ==================================================

    cursor.execute("""
        SELECT *
        FROM orders

        WHERE id = %s

        AND employee_id = %s

    """, (
        order_id,
        employee_id
    ))


    order = cursor.fetchone()


    if not order:

        cursor.close()
        connection.close()

        flash(
            "Order not found."
        )

        return redirect(
            url_for("employee_dashboard")
        )


    # ==================================================
    # CHECK STATUS
    # ==================================================

    if order["status"] not in [
        "Assigned",
        "Picking"
    ]:

        cursor.close()
        connection.close()

        flash(
            "This order is not available for Picking."
        )

        return redirect(
            url_for("employee_dashboard")
        )


    # ==================================================
    # PICKING COMPLETE
    # ==================================================

    if request.method == "POST":

        entered_barcode = request.form.get(
            "barcode",
            ""
        ).strip()


        # Barcode checking

        if order["barcode"]:

            if entered_barcode != str(
                order["barcode"]
            ):

                cursor.close()
                connection.close()

                flash(
                    "Invalid barcode."
                )

                return redirect(
                    url_for(
                        "picking",
                        order_id=order_id
                    )
                )


        # ==================================================
        # FIND PACKING EMPLOYEE
        # ==================================================

        packing_employee_id = (
            find_next_employee(
                cursor,
                "Packing"
            )
        )


        if not packing_employee_id:

            cursor.close()
            connection.close()

            flash(
                "Packing employee is not available."
            )

            return redirect(
                url_for("employee_dashboard")
            )


        # ==================================================
        # MOVE ORDER TO PACKING
        # ==================================================

        cursor.execute("""
            UPDATE orders

            SET
                status = 'Picked',
                employee_id = %s

            WHERE id = %s

            AND employee_id = %s

            AND status IN (
                'Assigned',
                'Picking'
            )

        """, (
            packing_employee_id,
            order_id,
            employee_id
        ))


        connection.commit()


        cursor.close()
        connection.close()


        flash(
            "Picking completed. Order moved to Packing."
        )


        # IMPORTANT:
        # Do NOT open Packing page for the
        # Picking employee.
        #
        # Packing employee will see it in
        # their own dashboard.

        return redirect(
            url_for("employee_dashboard")
        )


    cursor.close()
    connection.close()


    return render_template(
        "picking.html",
        order=order
    )


# ==================================================
# PACKING PAGE
# ==================================================

@app.route(
    "/packing/<int:order_id>",
    methods=["GET", "POST"]
)
@employee_required
def packing(order_id):

    employee_id = session["employee_id"]

    department = session.get(
        "employee_department",
        ""
    ).strip().lower()


    # Only Packing employees

    if department != "packing":

        flash(
            "You are not assigned to Packing."
        )

        return redirect(
            url_for("employee_dashboard")
        )


    connection = get_db()

    cursor = connection.cursor(
        dictionary=True
    )


    # ==================================================
    # GET ORDER
    # ==================================================

    cursor.execute("""
        SELECT *
        FROM orders

        WHERE id = %s

        AND employee_id = %s

    """, (
        order_id,
        employee_id
    ))


    order = cursor.fetchone()


    if not order:

        cursor.close()
        connection.close()

        flash(
            "Order not found."
        )

        return redirect(
            url_for("employee_dashboard")
        )


    # ==================================================
    # ALLOWED PACKING STATUS
    # ==================================================

    if order["status"] not in [
        "Assigned",
        "Picked"
    ]:

        cursor.close()
        connection.close()

        flash(
            "This order is not ready for Packing."
        )

        return redirect(
            url_for("employee_dashboard")
        )


    # ==================================================
    # PACKING COMPLETE
    # ==================================================

    if request.method == "POST":


        # ==================================================
        # FIND LOADING EMPLOYEE
        # ==================================================

        loading_employee_id = (
            find_next_employee(
                cursor,
                "Loading"
            )
        )


        if not loading_employee_id:

            cursor.close()
            connection.close()

            flash(
                "Loading employee is not available."
            )

            return redirect(
                url_for("employee_dashboard")
            )


        # ==================================================
        # MOVE ORDER TO LOADING
        # ==================================================

        cursor.execute("""
            UPDATE orders

            SET
                status = 'Packed',
                employee_id = %s

            WHERE id = %s

            AND employee_id = %s

            AND status IN (
                'Assigned',
                'Picked'
            )

        """, (
            loading_employee_id,
            order_id,
            employee_id
        ))


        connection.commit()


        cursor.close()
        connection.close()


        flash(
            "Packing completed. Order moved to Loading."
        )


        # Do NOT open Loading page for Packing employee.

        return redirect(
            url_for("employee_dashboard")
        )


    cursor.close()
    connection.close()


    return render_template(
        "packing.html",
        order=order
    )


# ==================================================
# LOADING PAGE
# ==================================================

@app.route(
    "/loading/<int:order_id>",
    methods=["GET", "POST"]
)
@employee_required
def loading(order_id):

    employee_id = session["employee_id"]

    department = session.get(
        "employee_department",
        ""
    ).strip().lower()


    # Only Loading employees

    if department != "loading":

        flash(
            "You are not assigned to Loading."
        )

        return redirect(
            url_for("employee_dashboard")
        )


    connection = get_db()

    cursor = connection.cursor(
        dictionary=True
    )


    # ==================================================
    # GET ORDER
    # ==================================================

    cursor.execute("""
        SELECT *
        FROM orders

        WHERE id = %s

        AND employee_id = %s

    """, (
        order_id,
        employee_id
    ))


    order = cursor.fetchone()


    if not order:

        cursor.close()
        connection.close()

        flash(
            "Order not found."
        )

        return redirect(
            url_for("employee_dashboard")
        )


    # ==================================================
    # ALLOWED LOADING STATUS
    # ==================================================

    if order["status"] not in [
        "Assigned",
        "Packed"
    ]:

        cursor.close()
        connection.close()

        flash(
            "This order is not ready for Loading."
        )

        return redirect(
            url_for("employee_dashboard")
        )


    # ==================================================
    # LOADING COMPLETE
    # ==================================================

    if request.method == "POST":

        cursor.execute("""
            UPDATE orders

            SET status = 'Loaded'

            WHERE id = %s

            AND employee_id = %s

            AND status IN (
                'Assigned',
                'Packed'
            )

        """, (
            order_id,
            employee_id
        ))


        connection.commit()


        cursor.close()
        connection.close()


        flash(
            "Loading completed successfully."
        )


        # ==================================================
        # FINAL STEP
        # ==================================================

        return redirect(
            url_for(
                "order_out_for_delivery",
                order_id=order_id
            )
        )


    cursor.close()
    connection.close()


    return render_template(
        "loading.html",
        order=order
    )


# ==================================================
# ORDER OUT FOR DELIVERY
# ==================================================

@app.route(
    "/order-out-for-delivery/<int:order_id>"
)
@employee_required
def order_out_for_delivery(order_id):

    connection = get_db()

    cursor = connection.cursor(
        dictionary=True
    )


    cursor.execute("""
        SELECT *
        FROM orders

        WHERE id = %s

        AND employee_id = %s

        AND status = 'Loaded'

    """, (
        order_id,
        session["employee_id"]
    ))


    order = cursor.fetchone()


    cursor.close()
    connection.close()


    if not order:

        flash(
            "Order not found."
        )

        return redirect(
            url_for("employee_dashboard")
        )


    return render_template(
        "order_out_for_delivery.html",
        order=order
    )


# ==================================================
# ADMIN LOGIN
# ==================================================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        connection = get_db()

        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM admins
            WHERE username = %s
            AND password = %s
        """, (
            username,
            password
        ))

        admin = cursor.fetchone()

        cursor.close()
        connection.close()

        if admin:

            session.clear()

            session["admin"] = admin["username"]

            return redirect(
                url_for("admin_dashboard")
            )

        flash("Invalid Admin Username or Password")

    return render_template(
        "admin_login.html"
    )


# ==================================================
# ADMIN DASHBOARD
# ==================================================

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():

    connection = get_db()

    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM orders
    """)
    total_orders = cursor.fetchone()["total"]


    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM orders
        WHERE status IN ('Assigned', 'Picking')
    """)
    picking_orders = cursor.fetchone()["total"]


    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM orders
        WHERE status = 'Picked'
    """)
    packing_orders = cursor.fetchone()["total"]


    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM orders
        WHERE status = 'Packed'
    """)
    loading_orders = cursor.fetchone()["total"]


    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM orders
        WHERE status IN ('Loaded', 'Out for Delivery')
    """)
    completed_orders = cursor.fetchone()["total"]


    cursor.execute("""
        SELECT
            o.*,
            e.name AS employee_name,
            e.department AS department

        FROM orders o

        LEFT JOIN employees e
        ON o.employee_id = e.employee_id

        ORDER BY o.id ASC
    """)

    orders = cursor.fetchall()

    cursor.close()
    connection.close()


    return render_template(
        "admin_dashboard.html",
        orders=orders,
        total_orders=total_orders,
        picking_orders=picking_orders,
        packing_orders=packing_orders,
        loading_orders=loading_orders,
        completed_orders=completed_orders
    )


# ==================================================
# ADMIN ADD PRODUCT
# ==================================================

@app.route(
    "/admin/add-product",
    methods=["GET", "POST"]
)
@admin_required
def admin_add_product():

    if request.method == "POST":

        product_code = request.form.get(
            "product_code",
            ""
        ).strip()

        product_name = request.form.get(
            "product_name",
            ""
        ).strip()

        price = request.form.get(
            "price",
            ""
        ).strip()

        stock = request.form.get(
            "stock",
            "0"
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()


        connection = get_db()

        cursor = connection.cursor(
            dictionary=True
        )


        try:

            cursor.execute("""
                INSERT INTO products
                (
                    product_code,
                    product_name,
                    price,
                    stock,
                    description,
                    status
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    'Available'
                )
            """, (
                product_code,
                product_name,
                price,
                stock,
                description
            ))


            connection.commit()

            flash(
                "Product added successfully."
            )


        except mysql.connector.Error as error:

            flash(
                "Product could not be added: "
                + str(error)
            )


        cursor.close()
        connection.close()


        return redirect(
            url_for("admin_add_product")
        )


    return render_template(
        "admin_add_product.html"
    )
# ==================================================
# ADD ORDER
# ==================================================

@app.route(
    "/admin/add-order",
    methods=["POST"]
)
@admin_required
def add_order():

    order_number = (
        request.form["order_number"].strip()
    )

    employee_id = (
        request.form["employee_id"].strip()
    )

    item_name = (
        request.form["item_name"].strip()
    )

    quantity = request.form["quantity"]

    barcode = (
        request.form["barcode"].strip()
    )


    connection = get_db()

    cursor = connection.cursor(
        dictionary=True
    )


    # ==================================================
    # GET ASSIGNED EMPLOYEE DEPARTMENT
    # ==================================================

    cursor.execute("""
        SELECT department

        FROM employees

        WHERE employee_id = %s

    """, (
        employee_id,
    ))


    employee = cursor.fetchone()


    if not employee:

        cursor.close()
        connection.close()

        flash(
            "Employee not found."
        )

        return redirect(
            url_for("admin_dashboard")
        )


    department = (
        employee["department"]
        .strip()
        .lower()
    )


    # ==================================================
    # INITIAL ORDER STATUS
    # ==================================================

    if department == "picking":

        initial_status = "Assigned"


    elif department == "packing":

        # Directly ready for Packing

        initial_status = "Picked"


    elif department == "loading":

        # Directly ready for Loading

        initial_status = "Packed"


    else:

        initial_status = "Assigned"


    # ==================================================
    # INSERT ORDER
    # ==================================================

    cursor.execute("""
        INSERT INTO orders
        (
            order_number,
            employee_id,
            item_name,
            quantity,
            barcode,
            status
        )

        VALUES
        (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )

    """, (
        order_number,
        employee_id,
        item_name,
        quantity,
        barcode,
        initial_status
    ))


    connection.commit()


    cursor.close()
    connection.close()


    if department == "picking":

        message = (
            "Order assigned to Picking."
        )

    elif department == "packing":

        message = (
            "Order assigned directly to Packing."
        )

    elif department == "loading":

        message = (
            "Order assigned directly to Loading."
        )

    else:

        message = (
            "Order assigned successfully."
        )


    flash(message)


    return redirect(
        url_for("admin_dashboard")
    )


# ==================================================
# LOGOUT
# ==================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )

# ==================================================
# CUSTOMER REGISTER
# ==================================================

@app.route("/customer/register", methods=["GET", "POST"])
def customer_register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()

        if not name or not email or not password:
            flash("Please fill all required fields.")
            return redirect(url_for("customer_register"))

        connection = get_db()
        cursor = connection.cursor(dictionary=True)

        # Email already registered?
        cursor.execute(
            "SELECT id FROM customers WHERE email = %s",
            (email,)
        )

        existing_customer = cursor.fetchone()

        if existing_customer:

            cursor.close()
            connection.close()

            flash("Email already registered.")

            return redirect(
                url_for("customer_login")
            )

        # Customer ID create
        cursor.execute(
            "SELECT MAX(id) AS max_id FROM customers"
        )

        result = cursor.fetchone()

        next_number = (
            (result["max_id"] or 0) + 1
        )

        customer_id = f"CUS{next_number:03d}"

        # Insert customer
        cursor.execute("""
            INSERT INTO customers
            (
                customer_id,
                name,
                email,
                phone,
                password
            )
            VALUES (%s, %s, %s, %s, %s)
        """, (
            customer_id,
            name,
            email,
            phone,
            password
        ))

        connection.commit()

        cursor.close()
        connection.close()

        flash(
            "Registration successful. "
            "Your Customer ID is " + customer_id
        )

        return redirect(
            url_for("customer_login")
        )

    return render_template(
        "customer_register.html"
    )

# ==================================================
# CUSTOMER LOGIN
# ==================================================

@app.route("/customer/login", methods=["GET", "POST"])
def customer_login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()

        connection = get_db()

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute("""
            SELECT *
            FROM customers
            WHERE email = %s
            AND password = %s
        """, (
            email,
            password
        ))

        customer = cursor.fetchone()

        cursor.close()
        connection.close()

        if customer:

            session.clear()

            session["customer_id"] = (
                customer["customer_id"]
            )

            session["customer_name"] = (
                customer["name"]
            )

            return redirect(
                url_for("customer_dashboard")
            )

        flash(
            "Invalid Email or Password"
        )

    return render_template(
        "customer_login.html"
    )

# ==================================================
# CUSTOMER DASHBOARD
# ==================================================

@app.route("/customer/dashboard")
def customer_dashboard():

    if "customer_id" not in session:

        return redirect(
            url_for("customer_login")
        )

    return render_template(
        "customer_dashboard.html",
        customer_name=session["customer_name"]
    )


# ==================================================
# CUSTOMER PRODUCTS
# ==================================================

@app.route("/customer/products")
def customer_products():

    if "customer_id" not in session:

        return redirect(
            url_for("customer_login")
        )


    connection = get_db()

    cursor = connection.cursor(
        dictionary=True
    )


    cursor.execute("""
        SELECT *
        FROM products

        WHERE stock > 0

        AND status = 'Available'

        ORDER BY id ASC
    """)


    products = cursor.fetchall()


    cursor.close()
    connection.close()


    return render_template(
        "customer_products.html",
        products=products
    )
@app.route("/customer/add-to-cart/<int:product_id>", methods=["POST"])
def customer_add_to_cart(product_id):
    if "customer_id" not in session:
        return redirect(url_for("customer_login"))

    customer_id = session["customer_id"]
    quantity = int(request.form.get("quantity", 1))

    if quantity < 1:
        quantity = 1

    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM products
        WHERE id = %s
    """, (product_id,))

    product = cursor.fetchone()

    if not product:
        cursor.close()
        connection.close()
        flash("Product not found.")
        return redirect(url_for("customer_products"))

    if product["stock"] < quantity:
        cursor.close()
        connection.close()
        flash("Not enough stock.")
        return redirect(url_for("customer_products"))

    cursor.execute("""
        SELECT *
        FROM cart
        WHERE customer_id = %s
        AND product_id = %s
    """, (
        customer_id,
        product_id
    ))

    existing_item = cursor.fetchone()

    if existing_item:
        new_quantity = existing_item["quantity"] + quantity

        if new_quantity > product["stock"]:
            cursor.close()
            connection.close()
            flash("Not enough stock.")
            return redirect(url_for("customer_products"))

        cursor.execute("""
            UPDATE cart
            SET quantity = %s
            WHERE id = %s
        """, (
            new_quantity,
            existing_item["id"]
        ))

    else:
        cursor.execute("""
            INSERT INTO cart
            (
                customer_id,
                product_id,
                quantity
            )
            VALUES
            (
                %s,
                %s,
                %s
            )
        """, (
            customer_id,
            product_id,
            quantity
        ))

    connection.commit()

    cursor.close()
    connection.close()

    flash("Product added to cart.")

    return redirect(url_for("customer_products"))

@app.route("/customer/cart")
def customer_cart():

    if "customer_id" not in session:
        return redirect(url_for("customer_login"))

    customer_id = session["customer_id"]

    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            cart.id AS cart_id,
            cart.quantity,

            products.id AS product_id,
            products.product_name,
            products.price,
            products.stock,
            products.description

        FROM cart

        JOIN products
            ON cart.product_id = products.id

        WHERE cart.customer_id = %s

        ORDER BY cart.id DESC
    """, (customer_id,))

    cart_items = cursor.fetchall()

    cart_total = 0

    for item in cart_items:

        item["subtotal"] = (
            item["price"]
            * item["quantity"]
        )

        cart_total += item["subtotal"]

    cursor.close()
    connection.close()

    return render_template(
        "customer_cart.html",
        cart_items=cart_items,
        cart_total=cart_total
    )

# =====================================================
# UPDATE CART QUANTITY
# =====================================================

@app.route(
    "/customer/cart/update/<int:cart_id>",
    methods=["POST"]
)
def customer_update_cart(cart_id):

    if "customer_id" not in session:
        return redirect(url_for("customer_login"))

    customer_id = session["customer_id"]

    try:
        quantity = int(
            request.form.get("quantity", 1)
        )
    except ValueError:
        quantity = 1

    if quantity < 1:
        quantity = 1

    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            cart.id,
            cart.product_id,
            products.stock
        FROM cart

        JOIN products
            ON cart.product_id = products.id

        WHERE cart.id = %s
        AND cart.customer_id = %s
    """, (
        cart_id,
        customer_id
    ))

    item = cursor.fetchone()

    if not item:
        cursor.close()
        connection.close()

        flash("Cart item not found.")

        return redirect(
            url_for("customer_cart")
        )

    if quantity > item["stock"]:
        cursor.close()
        connection.close()

        flash("Quantity exceeds available stock.")

        return redirect(
            url_for("customer_cart")
        )

    cursor.execute("""
        UPDATE cart
        SET quantity = %s

        WHERE id = %s
        AND customer_id = %s
    """, (
        quantity,
        cart_id,
        customer_id
    ))

    connection.commit()

    cursor.close()
    connection.close()

    flash("Cart quantity updated.")

    return redirect(
        url_for("customer_cart")
    )


# =====================================================
# REMOVE PRODUCT FROM CART
# =====================================================

@app.route(
    "/customer/cart/remove/<int:cart_id>",
    methods=["POST"]
)
def customer_remove_cart(cart_id):

    if "customer_id" not in session:
        return redirect(url_for("customer_login"))

    customer_id = session["customer_id"]

    connection = get_db()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM cart

        WHERE id = %s
        AND customer_id = %s
    """, (
        cart_id,
        customer_id
    ))

    connection.commit()

    cursor.close()
    connection.close()

    flash("Product removed from cart.")

    return redirect(
        url_for("customer_cart")
    )


# =====================================================
# PLACE ORDER FROM CART
# =====================================================

@app.route(
    "/customer/cart/place-order",
    methods=["POST"]
)
def customer_cart_place_order():

    if "customer_id" not in session:
        return redirect(url_for("customer_login"))

    customer_id = session["customer_id"]

    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    try:

        # ---------------------------------------------
        # GET CUSTOMER CART ITEMS
        # ---------------------------------------------

        cursor.execute("""
            SELECT
                cart.id AS cart_id,
                cart.product_id,
                cart.quantity,
                products.product_name,
                products.stock,
                products.status

            FROM cart

            JOIN products
                ON cart.product_id = products.id

            WHERE cart.customer_id = %s

            ORDER BY cart.id ASC
        """, (customer_id,))

        cart_items = cursor.fetchall()

        if not cart_items:

            cursor.close()
            connection.close()

            flash("Your cart is empty.")

            return redirect(
                url_for("customer_cart")
            )

        # ---------------------------------------------
        # CHECK ALL PRODUCT STOCK FIRST
        # ---------------------------------------------

        for item in cart_items:

            if item["status"] != "Available":

                connection.rollback()

                cursor.close()
                connection.close()

                flash(
                    item["product_name"]
                    + " is currently unavailable."
                )

                return redirect(
                    url_for("customer_cart")
                )

            if item["quantity"] > item["stock"]:

                connection.rollback()

                cursor.close()
                connection.close()

                flash(
                    "Not enough stock for "
                    + item["product_name"]
                )

                return redirect(
                    url_for("customer_cart")
                )

        # ---------------------------------------------
        # GET CURRENT LAST ORDER NUMBER
        # ---------------------------------------------

        cursor.execute("""
            SELECT
                MAX(
                    CAST(
                        SUBSTRING(order_number, 4)
                        AS UNSIGNED
                    )
                ) AS max_number

            FROM orders

            WHERE order_number LIKE 'ORD%'
        """)

        result = cursor.fetchone()

        next_number = (
            (result["max_number"] or 0) + 1
        )

        created_orders = []

        # ---------------------------------------------
        # CREATE ORDER FOR EACH CART ITEM
        # ---------------------------------------------

        for item in cart_items:

            picking_employee_id = find_next_employee(
                cursor,
                "Picking"
            )

            if not picking_employee_id:

                connection.rollback()

                cursor.close()
                connection.close()

                flash(
                    "Picking employee not available."
                )

                return redirect(
                    url_for("customer_cart")
                )

            order_number = (
                f"ORD{next_number:03d}"
            )

            barcode = (
                f"BAR{next_number:06d}"
            )

            cursor.execute("""
                INSERT INTO orders
                (
                    order_number,
                    employee_id,
                    item_name,
                    quantity,
                    barcode,
                    status,
                    customer_id
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    'Assigned',
                    %s
                )
            """, (
                order_number,
                picking_employee_id,
                item["product_name"],
                item["quantity"],
                barcode,
                customer_id
            ))

            # -----------------------------------------
            # REDUCE PRODUCT STOCK
            # -----------------------------------------

            cursor.execute("""
                UPDATE products

                SET stock = stock - %s

                WHERE id = %s
            """, (
                item["quantity"],
                item["product_id"]
            ))

            created_orders.append(
                order_number
            )

            next_number += 1

        # ---------------------------------------------
        # CLEAR CUSTOMER CART
        # ---------------------------------------------

        cursor.execute("""
            DELETE FROM cart
            WHERE customer_id = %s
        """, (customer_id,))

        connection.commit()

        cursor.close()
        connection.close()

        flash(
            "Order placed successfully: "
            + ", ".join(created_orders)
        )

        return redirect(
            url_for("customer_orders")
        )

    except Exception as error:

        connection.rollback()

        cursor.close()
        connection.close()

        flash(
            "Order could not be placed: "
            + str(error)
        )

        return redirect(
            url_for("customer_cart")
        )

    
# ==================================================
# CUSTOMER PLACE ORDER
# ==================================================

@app.route(
    "/customer/place-order/<int:product_id>",
    methods=["POST"]
)
def customer_place_order(product_id):
    if "customer_id" not in session:
        return redirect(url_for("customer_login"))

    quantity = int(request.form.get("quantity", 1))

    customer_id = session["customer_id"]

    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM products
        WHERE id = %s
    """, (product_id,))

    product = cursor.fetchone()

    if not product:
        cursor.close()
        connection.close()
        flash("Product not found.")
        return redirect(url_for("customer_products"))

    if quantity < 1 or product["stock"] < quantity:
        cursor.close()
        connection.close()
        flash("Not enough stock.")
        return redirect(url_for("customer_products"))

    picking_employee_id = find_next_employee(
        cursor,
        "Picking"
    )

    if not picking_employee_id:
        cursor.close()
        connection.close()
        flash("Picking employee not available.")
        return redirect(url_for("customer_products"))

    cursor.execute("""
        SELECT MAX(id) AS max_id
        FROM orders
    """)

    result = cursor.fetchone()

    next_number = (
        (result["max_id"] or 0) + 1
    )

    order_number = f"ORD{next_number:03d}"
    barcode = f"BAR{next_number:06d}"

    cursor.execute("""
        INSERT INTO orders
        (
            order_number,
            employee_id,
            item_name,
            quantity,
            barcode,
            status,
            customer_id
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s,
            %s,
            'Assigned',
            %s
        )
    """, (
        order_number,
        picking_employee_id,
        product["product_name"],
        quantity,
        barcode,
        customer_id
    ))

    cursor.execute("""
        UPDATE products
        SET stock = stock - %s
        WHERE id = %s
    """, (
        quantity,
        product_id
    ))

    connection.commit()

    cursor.close()
    connection.close()

    flash(
        "Order placed successfully. "
        "Order Number: " + order_number
    )

    return redirect(
        url_for("customer_products")
    )


@app.route("/customer/orders")
def customer_orders():
    if "customer_id" not in session:
        return redirect(url_for("customer_login"))

    customer_id = session["customer_id"]

    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            id,
            order_number,
            item_name,
            quantity,
            barcode,
            status,
            employee_id,
            customer_id
        FROM orders
        WHERE customer_id = %s
        ORDER BY id DESC
    """, (customer_id,))

    orders = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "customer_orders.html",
        orders=orders
    )

# ==================================================
# CUSTOMER LOGOUT
# ==================================================

@app.route("/customer/logout")
def customer_logout():

    session.clear()

    return redirect(
        url_for("customer_login")
    )

# ==================================================
# START APPLICATION
# ==================================================

if __name__ == "__main__":

    create_database()

    init_db()

    reset_test_orders()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )