import os
from flask import Flask, render_template, request, redirect, url_for, session
from models import db, User, Admin, Item
from models import db, User, Order, OrderItem,CartItem
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask import jsonify
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'static/uploads/'
db.init_app(app)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}



@app.before_first_request
def create_tables():
    db.create_all()
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    item_name = request.json.get('item_name')
    item_price = request.json.get('item_price')
    quantity = request.json.get('quantity')

    order = Order.query.filter_by(user_id=user_id, completed=False).first()
    if not order:
        order = Order(user_id=user_id, total_price=0, completed=False)
        db.session.add(order)
        db.session.commit()

    order_item = OrderItem(order_id=order.id, item_name=item_name, item_price=item_price, quantity=quantity)
    db.session.add(order_item)
    db.session.commit()

    order.total_price += item_price * quantity
    db.session.commit()

    return jsonify(success=True)

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    order = Order.query.filter_by(user_id=user_id, completed=False).first()
    if not order:
        return jsonify(items=[], total_price=0)

    items = [{'item_name': item.item_name, 'item_price': item.item_price, 'quantity': item.quantity} for item in order.items]
    return jsonify(items=items, total_price=order.total_price)

@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    order = Order.query.filter_by(user_id=user_id, completed=False).first()
    if order:
        order.completed = True
        db.session.commit()

    return redirect(url_for('cart'))

@app.route('/empty-cart', methods=['POST'])
def empty_cart():
    try:
        if 'user_id' not in session:
            return jsonify(success=False), 401

        user_id = session['user_id']
        order = Order.query.filter_by(user_id=user_id, completed=False).first()
        if order:
            for item in order.items:
                db.session.delete(item)
            db.session.delete(order)
            db.session.commit()

        return jsonify(success=True)
    except Exception as e:
        print(f"Error clearing cart: {e}")
        return jsonify(success=False, error=str(e)), 500




@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('index'))
        else:
            return "Invalid user credentials"
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        lastname = request.form['lastname']
        phone_number = request.form['phone_number']
        email = request.form['email']
        address = request.form['address']
        password = generate_password_hash(request.form['password'], method='sha256')
        new_user = User(name=name, lastname=lastname, phone_number=phone_number, email=email, address=address, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/admin/register', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'POST':
        name = request.form['name']
        lastname = request.form['lastname']
        phone_number = request.form['phone_number']
        email = request.form['email']
        resturent_name = request.form['resturent_name']
        address = request.form['address']
        password = generate_password_hash(request.form['password'], method='sha256')
        new_admin = Admin(name=name, lastname=lastname, phone_number=phone_number, email=email, resturent_name=resturent_name, address=address, password=password)
        db.session.add(new_admin)
        db.session.commit()
        return redirect(url_for('admin_login'))
    return render_template('admin_register.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        admin = Admin.query.filter_by(email=email).first()
        if admin and check_password_hash(admin.password, password):
            session['admin_id'] = admin.id
            return redirect(url_for('admin_dashboard'))
        else:
            return "Invalid admin credentials"
    return render_template('admin_login.html')



@app.route('/admin/dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    admin = Admin.query.get(session['admin_id'])
    items = admin.items

    if request.method == 'POST':
        if 'cover_image' in request.files or 'item_image' in request.files:
            cover_file = request.files.get('cover_image')
            item_file = request.files.get('item_image')

            if cover_file and allowed_file(cover_file.filename):
                cover_filename = secure_filename(cover_file.filename)
                cover_file.save(os.path.join(app.config['UPLOAD_FOLDER'], cover_filename))
                admin.cover_image = os.path.join(app.config['UPLOAD_FOLDER'], cover_filename)

            if item_file and allowed_file(item_file.filename):
                item_filename = secure_filename(item_file.filename)
                item_file.save(os.path.join(app.config['UPLOAD_FOLDER'], item_filename))
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], item_filename)
            else:
                image_path = None

            name = request.form.get('item_name')
            description = request.form.get('item_description')
            price = request.form.get('item_price')

            if name and description and price:
                new_item = Item(name=name, description=description, price=price, image=image_path, admin_id=session['admin_id'])
                db.session.add(new_item)
                db.session.commit()
                return jsonify(success=True, item={
                    'id': new_item.id,
                    'name': new_item.name,
                    'description': new_item.description,
                    'price': new_item.price,
                    'image': url_for('static', filename='uploads/' + os.path.basename(new_item.image)) if new_item.image else None
                })

            db.session.commit()
            return jsonify(success=True)

        elif request.form.get('delete_cover'):
            if admin.cover_image:
                try:
                    os.remove(admin.cover_image)
                except FileNotFoundError:
                    pass
                admin.cover_image = None
                db.session.commit()
            return jsonify(success=True)

        elif 'delete_item_id' in request.form:
            item_id = request.form['delete_item_id']
            item = Item.query.get(item_id)
            if item:
                db.session.delete(item)
                db.session.commit()
            return jsonify(success=True, item_id=item_id)

    return render_template('admin_dashboard.html', admin=admin, items=items)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    return redirect(url_for('admin_login'))

@app.route('/index')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    Users = User.query.get(user_id)
    admins = Admin.query.all()
    return render_template('index.html', admins=admins,Users=Users)

@app.route('/restaurant/<int:admin_id>/items', methods=['GET'])
def get_items(admin_id):
    items = Item.query.filter_by(admin_id=admin_id).all()
    items_list = [{'id': item.id, 'name': item.name, 'description': item.description, 'price': item.price, 'image': item.image} for item in items]
    return jsonify(items_list)

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/place-order', methods=['POST'])
def place_order():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'User not logged in'})

    user_id = session['user_id']
    order = Order.query.filter_by(user_id=user_id, completed=False).first()
    if not order or not order.items:
        return jsonify({'success': False, 'error': 'No items in cart'})

    try:
        # Mark the order as completed
        order.completed = True
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to place order'})



if __name__ == '__main__':
    app.run(debug=True)
