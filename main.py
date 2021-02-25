from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sbkadbha78w2hvjh2g32i2bbek2'
ckeditor = CKEditor(app)
Bootstrap(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(500), nullable=False)

    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="poster")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="blog_post")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

    poster_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    poster = relationship("User", back_populates="comments")
    blog_post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    blog_post = relationship("BlogPost", back_populates="comments")


# db.create_all()


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)

        return f(*args, **kwargs)

    return decorated_function


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def home():
    blog_posts = BlogPost.query.all()
    return render_template("index.html", posts=blog_posts, user=current_user)


@app.route("/about")
def about():
    return render_template("about.html", user=current_user)


@app.route("/contact")
def contact():
    # Check out project 71.60.2 to see the implementation of a contact form which can be used in combination with a database which stores the contact form data
    return render_template("contact.html", user=current_user)


@app.route('/register', methods=["GET", "POST"])
def register():
    register_form = RegisterForm()

    if register_form.validate_on_submit():
        user_exists = User.query.filter_by(email=register_form.email.data).first()

        if user_exists:
            flash("A user with this Email-Id already exists. Try Logging In instead!")
            return redirect(url_for("login"))

        hash_salted_password = generate_password_hash(register_form.password.data, method="pbkdf2:sha256", salt_length=8)
        new_user = User(name=register_form.name.data, email=register_form.email.data, password=hash_salted_password)

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(url_for("home"))

    return render_template("register.html", form=register_form, user=current_user)


@app.route('/login', methods=["GET", "POST"])
def login():
    login_form = LoginForm()

    if login_form.validate_on_submit():
        user = User.query.filter_by(email=login_form.email.data).first()

        if user:
            if check_password_hash(user.password, login_form.password.data):
                login_user(user)
                return redirect(url_for("home"))

            flash("Incorrect Password. Try Again!")
            return redirect(url_for("login"))

        flash("This Email-Id does not exist. Try Again or Register!")
        return redirect(url_for("login"))

    return render_template("login.html", form=login_form, user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def read_post(post_id):
    clicked_post = BlogPost.query.get(post_id)
    comment_form = CommentForm()

    if comment_form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment = Comment(text=comment_form.comment.data, poster=current_user, blog_post=clicked_post)
            db.session.add(new_comment)
            db.session.commit()
        else:
            flash("You must be logged in to comment on a post!")
            return redirect(url_for("login"))

    return render_template("post.html", post=clicked_post, user=current_user, form=comment_form)


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def create_post():
    create_post_form = CreatePostForm()

    if create_post_form.validate_on_submit():
        new_post = BlogPost(title=create_post_form.title.data, subtitle=create_post_form.subtitle.data,
                            date=date.today().strftime("%B %d, %Y"), body=create_post_form.body.data,
                            img_url=create_post_form.img_url.data, author=current_user)

        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("home"))

    return render_template("make-post.html", form=create_post_form, user=current_user)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post_to_edit = BlogPost.query.get(post_id)
    edit_post_form = CreatePostForm(title=post_to_edit.title, subtitle=post_to_edit.subtitle, body=post_to_edit.body,
                                    img_url=post_to_edit.img_url)

    if edit_post_form.validate_on_submit():
        post_to_edit.title = edit_post_form.title.data
        post_to_edit.subtitle = edit_post_form.subtitle.data
        post_to_edit.body = edit_post_form.body.data
        post_to_edit.img_url = edit_post_form.img_url.data

        db.session.commit()
        return redirect(url_for("read_post", post_id=post_to_edit.id))

    return render_template("make-post.html", editing=True, form=edit_post_form, user=current_user)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()

    return redirect(url_for("home"))


if __name__ == "__main__":
    # app.debug = True
    # app.run(host='0.0.0.0', port=5000)
    app.run()
