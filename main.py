from flask import Flask, render_template, redirect, request, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
import os, stripe

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("KET")


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///products.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

stripe_keys = {
    "secret_key": os.environ.get("stripe_secret"),
    "publishable_key": os.environ.get("stripe_publish"),
}

stripe.api_key = stripe_keys["secret_key"]

app.config['SQLALCHEMY_BINDS'] = {
    'users': 'sqlite:///users.db',
    'cart_product': 'sqlite:///cart_product.db'
}

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), unique=True, nullable=False)
    brand = db.Column(db.String(250), unique=False, nullable=False)
    description = db.Column(db.String(5000), nullable=False)
    category = db.Column(db.String(5000), nullable=False)
    thumbnail_url = db.Column(db.String(5000), nullable=False)
    img_url = db.Column(db.String(5000), nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=True)
    rating = db.Column(db.Float, nullable=True)
    discount = db.Column(db.Float, nullable=True)
    stripe_price_id = db.Column(db.String(5000), nullable=True)
    stripe_prod_id = db.Column(db.String(5000), nullable=True)


class User(UserMixin, db.Model):
    __bind_key__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(250), nullable=False)
    tasks = db.relationship('CartProduct', backref='user')


class CartProduct(db.Model):
    __bind_key__ = 'cart_product'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), unique=False, nullable=False)
    brand = db.Column(db.String(250), unique=False, nullable=False)
    description = db.Column(db.String(5000), nullable=False)
    category = db.Column(db.String(5000), nullable=False)
    thumbnail_url = db.Column(db.String(5000), nullable=False)
    img_url = db.Column(db.String(5000), nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=True)
    rating = db.Column(db.Float, nullable=True)
    quantity = db.Column(db.Integer, nullable=True)
    discount = db.Column(db.Float, nullable=True)
    stripe_price_id = db.Column(db.String(5000), nullable=True)
    stripe_prod_id = db.Column(db.String(5000), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(username=email).first()

        if not user:
            flash("Enter the correct email address.")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, password):
            flash("please enter correct password")
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('home'))
    return render_template("login.html")


@app.route('/register', methods=["GET", "POST"])
def register():
    email = request.form.get("email")
    password = request.form.get("password")
    name = request.form.get("name")
    if request.method == "POST":

        # If user's email already exists
        if User.query.filter_by(username=email).first():
            # Send flash messsage
            flash("You've already signed up with that email, log in instead!")
            # Redirect to /login route.
            return redirect(url_for('login'))

        hash_and_salted_password = generate_password_hash(
            password,
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(
            username=email,
            name=name,
            password=hash_and_salted_password,
        )
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/")
def home():
    categories_list = []
    products = db.session.query(Product).all()
    for i in products:
        if i.category not in categories_list:
            categories_list.append(i.category)
    return render_template("index.html", content=products, categories=categories_list)


@app.route("/<the_pr>")
def the_product(the_pr):
    products = db.session.query(Product).all()
    for i in products:
        if i.name == the_pr:
            pr_imgs = i.img_url.split()
            return render_template("product.html", product=i, img=pr_imgs, len_of_pr_imgs=len(pr_imgs))
    return render_template("index.html")


@app.route("/filters/<cat>")
def specific_category(cat):
    product_list = []
    categories_list = []
    products = db.session.query(Product).all()
    for product in products:
        if product.category == cat:
            product_list.append(product)
    for k in products:
        if k.category not in categories_list:
            categories_list.append(k.category)
    return render_template("category.html", content=product_list, categories=categories_list)


@app.route("/cart")
def cart():
    total = None
    products = db.session.query(CartProduct).all()
    if len(products) == 0:
        message = "No items in your cart"
    else:
        message = []
        for product in products:
            if product.user_id == current_user.id:
                message.append(product)

    if message == "No items in your cart":
        l_o_m = 0
    else:
        a = 0
        for i in message:
            a += i.quantity
        l_o_m = a
        total = 0
        for m in message:
            s = m.price*m.quantity
            total += s

    return render_template("cart.html", message=message, len_of_msg=l_o_m, total=total)


@app.route("/mmm/<int:pr_id>")
def add_to_cart(pr_id):
    products = db.session.query(Product).all()
    added_product = None
    for k in products:
        if k.id==pr_id:
            added_product=k

    new_item = CartProduct(
        name=added_product.name,
        brand=added_product.brand,
        description=added_product.description,
        category=added_product.category,
        thumbnail_url=added_product.thumbnail_url,
        img_url=" ".join(added_product.img_url),
        stock=added_product.stock,
        price=added_product.price,
        rating=added_product.rating,
        discount=added_product.discount,
        user_id=current_user.id,
        stripe_price_id=added_product.stripe_price_id,
        stripe_prod_id=added_product.stripe_prod_id,
        quantity=1
    )
    db.session.add(new_item)
    db.session.commit()

    return redirect(url_for('cart'))


@app.route("/del/<int:id>")
def del_cart_pr(id):
    products = db.session.query(CartProduct).all()
    for i in products:
        if i.id == id and i.user_id == current_user.id:
            obj = CartProduct.query.filter_by(id=i.id).one()
            db.session.delete(obj)
            db.session.commit()
    return redirect(url_for("cart"))


@app.route("/add/<int:id>")
def plus_qty(id):
    products = db.session.query(CartProduct).all()

    for k in products:
        if k.id == id and k.user_id == current_user.id:
            qt = int(k.quantity)
            new = qt + 1
            k.quantity = new
            db.session.commit()

    return redirect(url_for("cart"))


@app.route("/minus/<int:id>")
def minus_qty(id):
    products = db.session.query(CartProduct).all()

    for k in products:
        if k.id == id and k.user_id == current_user.id:
            qt = int(k.quantity)
            if qt > 1:
                new = qt - 1
                k.quantity = new
                db.session.commit()

    return redirect(url_for("cart"))


@app.route("/checkout")
def checkout():
    products = db.session.query(CartProduct).all()
    items_list = []

    #currently checkout feature is disabled
    #stripe requires registration & paperwork to receive international payments

    # for i in products:
    #     if i.user_id == current_user.id:
    #         a = {
    #             "price": i.stripe_price_id,
    #             "quantity": i.quantity
    #         }
    #         items_list.append(a)
    #
    # stripe.checkout.Session.create(
    #     success_url="http://127.0.0.1:5000/success",
    #     cancel_url="http://127.0.0.1:5000/cancel",
    #     line_items=items_list,
    #     mode="payment",
    # )
    print(items_list)

    return redirect(url_for("cart"))


@app.route("/success")
def success():
    return render_template("success.html")


@app.route("/cancel")
def cancel():
    return render_template("cancel.html")


if __name__ == "__main__":
    app.run(debug=True)


























