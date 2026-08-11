from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash,check_password_hash
#Flask：创建网站
#render_template：打开HTML页面
#request：获取用户提交的数据
#redirect：跳转页面
#url_for：根据函数名寻找网址
#session:记住当前登录的人
import sqlite3

app = Flask(__name__)
app.secret_key = "life-tracker-secret-key"

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
            "SELECT * FROM users WHERE email = ? ",
            (email,)
        ).fetchone()
        conn.close()
        print(user)
        if user and check_password_hash(user[3],password):
            session["user_email"] = email
            
            return redirect(url_for("dashboard"))
        else:
            return "Login failed"

    return render_template("login.html")

# 访问 /register，执行 register()，打开 register.html
# GET：显示注册页面
# POST：接收注册表单，把用户存进 users 表
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect("life_tracker.db")
        conn.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (name, email, hashed_password)
        )
        conn.commit()
        conn.close()

        print("User saved!")
        return redirect(url_for("login"))

    return render_template("register.html")

# 访问 /dashboard，执行 dashboard()，显示 dashboard.html
@app.route("/dashboard")
def dashboard():
    email = session.get("user_email")

    if not email:
        return redirect(url_for("login"))
    
    conn = sqlite3.connect("life_tracker.db")

    habits = conn.execute(
    """
    SELECT id, habit_name, details
    FROM habits
    WHERE user_email = ?
    """,
    (email,)
    ).fetchall()

    conn.close()
    
    return render_template(
        "dashboard.html",
        email=email,
        habits=habits
    )

# 访问 /logout，清除登录状态，然后回到 login 页面
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

#habit部分，接下两段包含delete和edit
@app.route("/create", methods=["GET", "POST"])
def create_habit():

    # 如果没有登录，就回到 Login
    if "user_email" not in session:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        habit_name = request.form.get("habit_name")
        details = request.form.get("details")

        conn = sqlite3.connect("life_tracker.db")
        conn.execute(
            """
            INSERT INTO habits (user_email, habit_name, details)
            VALUES (?, ?, ?)
            """,
            (session["user_email"], habit_name, details)
        )
        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))
    return render_template("create_habit.html")

#habit的delete
@app.route("/delete/<int:habit_id>")
def delete_habit(habit_id):

        # 如果没有登录，就回到 Login
    if "user_email" not in session:
        return redirect(url_for("login"))
    
    conn = sqlite3.connect("life_tracker.db")

    conn.execute(
        "DELETE FROM habits WHERE id = ?",
        (habit_id,)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))

#habit的edit
@app.route("/edit/<int:habit_id>", methods=["GET", "POST"])
def edit_habit(habit_id):

        # 如果没有登录，就回到 Login
    if "user_email" not in session:
        return redirect(url_for("login"))
    
    conn = sqlite3.connect("life_tracker.db")
    if request.method == "POST":
        habit_name = request.form.get("habit_name")
        details = request.form.get("details")
        conn.execute(
            """
            UPDATE habits
            SET habit_name = ?, details = ?
            WHERE id = ?
            """,
            (habit_name, details, habit_id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("dashboard"))
    habit = conn.execute(
        """
        SELECT *
        FROM habits
        WHERE id = ?
        """,
        (habit_id,)
    ).fetchone()
    conn.close()

    return render_template("edit_habit.html", habit=habit)

def update_habits_table():
    conn = sqlite3.connect("life_tracker.db")

    columns = conn.execute("PRAGMA table_info(habits)").fetchall()
    column_names = [column[1] for column in columns]

    if "category" not in column_names:
        conn.execute(
            "ALTER TABLE habits ADD COLUMN category TEXT DEFAULT 'Other'"
        )

    if "frequency" not in column_names:
        conn.execute(
            "ALTER TABLE habits ADD COLUMN frequency TEXT DEFAULT 'Daily'"
        )

    if "goal_minutes" not in column_names:
        conn.execute(
            "ALTER TABLE habits ADD COLUMN goal_minutes INTEGER DEFAULT 30"
        )

    if "color" not in column_names:
        conn.execute(
            "ALTER TABLE habits ADD COLUMN color TEXT DEFAULT '#2f7a57'"
        )

    conn.commit()
    conn.close()

if __name__ == "__main__":
    update_habits_table()
    app.run(debug=True)