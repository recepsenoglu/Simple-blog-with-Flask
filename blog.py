from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps

# Kullanıcı Giriş Decorator'ı
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapın",category="danger")
            return redirect(url_for("login"))
    return decorated_function
# Kullanıcı Kayıt Formu
class RegisterForm(Form):
    name = StringField("İsim Soyisim",
    validators=[validators.length(min = 4,max = 25)])
    username = StringField("Kullanıcı Adı",
    validators=[validators.length(min = 4,max = 35)])
    email = StringField("Email Adresi",
    validators=[validators.Email(message="Lütfen Geçerli Bir Email Adresi Girin.")])
    password = PasswordField("Parola",
    validators=[validators.DataRequired(message="Lütfen bir parola belirleyin."),
    validators.EqualTo(fieldname = "confirm",message="Parolanız Uyuşmuyor.")])
    confirm = PasswordField("Parola Doğrula")
class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")

app = Flask(__name__)
app.secret_key = "recblog"

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "recblog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)

@app.route("/")
def index():
    return render_template("index.html")
@app.route("/about")
def about():
    return render_template("about.html")

# Makale Sayfası
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    sorgu = "Select * From articles"
    result = cursor.execute(sorgu)

    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html",articles = articles)
    else:
        return render_template("articles.html")

@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    sorgu = "Select * From articles Where author = %s"
    result = cursor.execute(sorgu,(session["username"],))

    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles = articles)
    else:
        return render_template("dashboard.html")
  
#Kayıt Olma
@app.route("/register",methods = ["GET","POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()

        sorgu = "Insert Into users(name,email,username,password) Values(%s,%s,%s,%s)"
        cursor.execute(sorgu,(name,email,username,password))
        mysql.connection.commit()

        cursor.close()

        flash("Kayıt işlemi başarılı...","success")
        return redirect(url_for("login"))
    else:       
        return render_template("register.html",form = form)

#login işlemi
@app.route("/login",methods = ["GET","POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST" and form.validate():
        username = form.username.data
        password_entered = form.password.data

        cursor = mysql.connection.cursor()
        sorgu = "Select * From users Where username = %s"
        result = cursor.execute(sorgu,(username,)) 

        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password_entered,real_password):
                flash("Başarıyla Giriş Yaptınız...","success")
                session["logged_in"] = True
                session["username"] = username

                return redirect(url_for("index"))
            else:
                flash("Parolanızı Yanlış Girdiniz...","danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle bir kullanıcı bulunmuyor...","danger")
            return redirect(url_for("login"))
    else:
        return render_template("login.html",form = form)

#log out
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# Detay Sayfası
@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    sorgu = "Select * From articles where id = %s"
    result = cursor.execute(sorgu,(id,))

    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html",article = article)
    else:
        return render_template("article.html")

# Makale Ekleme
@app.route("/addarticle",methods = ["GET","POST"])
def addarticle():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data 
        content = form.content.data

        cursor = mysql.connection.cursor()
        sorgu = "Insert Into articles(title,author,content) Values(%s,%s,%s)"
        cursor.execute(sorgu,(title,session["username"],content))
        mysql.connection.commit()
        cursor.close()
        flash("Makale Başarıyla Eklendi","success")
        return redirect(url_for("dashboard"))

    return render_template("addarticle.html",form = form)

# Makale Silme
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu = "Select * From articles Where author = %s and id = %s"
    result = cursor.execute(sorgu,(session["username"],id))

    if result > 0:
        sorgu2 = "Delete From articles where id=%s"
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()
        flash("Makale başarıyla silindi.","success")
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok.","danger")
        return redirect(url_for("index"))

# Makale Güncelleme
@app.route("/edit/<string:id>",methods = ["GET","POST"])
@login_required
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        sorgu = "Select * From articles where id = %s and author = %s"
        result = cursor.execute(sorgu,(id,session["username"]))

        if result == 0:
            flash("Böyle bir makale yok.","danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html",form = form)
    else:
        #POST REQUEST
        form = ArticleForm(request.form)

        newTitle = form.title.data
        newContent = form.content.data
        sorgu2 = "Update articles Set title = %s,content = %s where id = %s"
        cursor = mysql.connection.cursor()
        cursor.execute(sorgu2,(newTitle,newContent,id))
        mysql.connection.commit()
        flash("Makale başarıyla güncellendi.","success")
        return redirect(url_for("dashboard"))

# Arama URL
@app.route("/search",methods = ["GET","POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")
        cursor = mysql.connection.cursor()
        sorgu = "Select * From articles where title Like '%" + keyword + "%'"
        result = cursor.execute(sorgu)

        if result == 0:
            flash("Aranan kelimeye uygun makale bulunamadı.","warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("articles.html",articles = articles)

# Makale Form
class ArticleForm(Form):
    title = StringField("Makale Başlığı",validators=[validators.length(min=5,max=100)])
    content = TextAreaField("Makale İçeriği",validators=[validators.Length(min=10)])


if __name__ == "__main__":
    app.run(debug=True)