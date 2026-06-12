from flask import Flask, render_template, request, redirect, url_for
#Flask：创建网站
#render_template：打开HTML页面
#request：获取用户提交的数据
#redirect：跳转页面
#url_for：根据函数名寻找网址
import sqlite3

app = Flask(__name__)

@app.route("/")
def home():
    return "Life Tracker is running!"


# 访问 /login，执行 login()，打开 login.html
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = sqlite3.connect("life_tracker.db")
        user = conn.execute(
            "SELECT * FROM users WHERE email = ? AND password = ?",
            (email, password)
        ).fetchone()
        conn.close()

        if user:
            return redirect(url_for("dashboard", email=email))
        else:
            return "Login failed"

    return render_template("login.html")

# 访问 /register，执行 register()，打开 register.html
# GET：显示注册页面
# POST：接收注册表单，并把用户存进 users 表
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        conn = sqlite3.connect("life_tracker.db")
        conn.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (name, email, password)
        )
        conn.commit()
        conn.close()

        print("User saved!")

        return redirect(url_for("login"))

    return render_template("register.html")

# 访问 /dashboard，执行 dashboard()，显示 dashboard.html
@app.route("/dashboard")
def dashboard():
    email = request.args.get("email"
                             )
    return render_template(
        "dashboard.html",
        email=email
    )


if __name__ == "__main__":
    app.run(debug=True)