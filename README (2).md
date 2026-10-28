# Tracker World – Warehouse Management & Order Tracking System

A full-stack warehouse and order tracking web application built with **Python, Flask and MySQL**. Customers place orders, and each order moves through a warehouse workflow handled by different employees: **Picking → Packing → Loading → Out for Delivery**.

**Live demo:** https://tracker-world.onrender.com

> The demo runs on free hosting, so the first page load can take up to a minute while the server wakes up.

## Features

- **Three role-based modules:** Customer, Employee and Admin, each with its own login
- **Customer:** registration/login, product listing, shopping cart with quantity updates, order placement and a My Orders tracking page
- **Employee:** department-based dashboards for Picking, Packing and Loading
- **Admin:** add and manage products
- **Automatic assignment:** when a stage is completed, the order is handed to the employee of the next department who has the fewest active orders
- **Barcode validation** at the picking stage
- **Order status tracking** for customers and administrators
- Responsive pages built with HTML5, CSS3, JavaScript and Bootstrap

## Try the demo

Open the live demo and follow the steps below. Orders only appear for employees after a customer places one, so start with the customer page.

| Role | Login page | Credentials |
| --- | --- | --- |
| Customer | `/customer/login` | Create your own account (email and password) at `/customer/register` |
| Employee | `/login` | `EMP001` to `EMP005`, password `1234` |
| Admin | `/admin/login` | `admin` / `admin123` |

Employee departments:

| Employee IDs | Department |
| --- | --- |
| `EMP001`, `EMP002` | Picking |
| `EMP003`, `EMP004` | Packing |
| `EMP005` | Loading |

**Walkthrough**

1. **Admin:** log in at `/admin/login` and check that products are listed (two sample products are already added). Add more if you like.
2. **Customer:** open `/customer/login`, click **Create Account** (or go to `/customer/register`), then log in with your email and password, add a product to the cart and place an order.
3. **Picking:** log in as `EMP001` or `EMP002` and open the order. The page shows the **Product ID**. To complete picking, enter the barcode, which is `BAR` (capital letters) + `0` + the Product ID. For example, Product ID `5` gives the barcode `BAR05`.
4. **Packing:** log in as `EMP003` or `EMP004` and complete packing.
5. **Loading:** log in as `EMP005` and complete loading.
6. **Customer:** open My Orders to see the updated status.

The demo accounts are for testing only.

## Tech stack

- **Backend:** Python, Flask
- **Database:** MySQL (`mysql-connector-python`)
- **Frontend:** HTML5, CSS3, JavaScript, Bootstrap
- **Hosting:** Render

## Run locally

1. Clone the repository and install the dependencies:

   ```bash
   git clone https://github.com/MRManiraj/tracker_world.git
   cd tracker_world
   pip install -r requirements.txt
   ```

2. Set the database environment variables:

   | Variable | Default |
   | --- | --- |
   | `MYSQL_HOST` | `localhost` |
   | `MYSQL_USER` | `root` |
   | `MYSQL_PASSWORD` | empty |
   | `MYSQL_DATABASE` | `warehouse_db` |
   | `MYSQL_PORT` | `4000` |

   The app connects over SSL using the certificate in the `certs/` folder.

3. Start the app:

   ```bash
   python app.py
   ```

## Project structure

```
tracker_world/
├── app.py             # Flask routes, database setup and workflow logic
├── templates/         # HTML templates
├── static/            # CSS, JavaScript and images
├── certs/             # SSL certificate for the database connection
├── requirements.txt
└── tracker.html
```

## Screenshots

<!-- Add screenshots of the customer page, employee dashboard and admin page here -->

## Author

**Manikandaraj G**, Python Developer, Chennai
GitHub: [MRManiraj](https://github.com/MRManiraj)
