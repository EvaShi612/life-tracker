from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash,check_password_hash
# date 用来自动取得今天的日期
from datetime import date

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
    SELECT id, habit_name, details, category, frequency, goal_minutes, color
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
        category = request.form.get("category", "Other")
        frequency = request.form.get("frequency", "Daily")
        goal_minutes = request.form.get("goal_minutes", 30)
        color = request.form.get("color", "#2f7a57")

        conn = sqlite3.connect("life_tracker.db")
        conn.execute(
    """
    INSERT INTO habits
    (user_email, habit_name, details, category, frequency, goal_minutes, color)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
    (
        session["user_email"],
        habit_name,
        details,
        category,
        frequency,
        goal_minutes,
        color
    )
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

# 只删除属于当前登录用户的 Habit
    conn.execute(
        """
        DELETE FROM habits
        WHERE id = ? AND user_email = ?
        """,
        (habit_id, session["user_email"])
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

    # 如果用户提交修改后的 Habit。从 edit_habit.html 获取新的资料。然后 UPDATE 数据库里对应的 Habit
    if request.method == "POST":
        habit_name = request.form.get("habit_name")
        details = request.form.get("details")
        category = request.form.get("category", "Other")
        frequency = request.form.get("frequency", "Daily")
        goal_minutes = request.form.get("goal_minutes", 30)
        color = request.form.get("color", "#071a11")
        
# 根据 habit_id 找到原来的 Habit，并更新所有资料
        conn.execute(
            """
            UPDATE habits
            SET habit_name = ?, details = ?, category = ?, frequency = ?, goal_minutes = ?, color = ?
            WHERE id = ? AND user_email = ?
            """,
            ( 
                habit_name,
                details,
                category,
                frequency,
                goal_minutes,
                color,
                habit_id,
                session["user_email"]
            )
        )

        conn.commit()
        conn.close()
        return redirect(url_for("dashboard"))
    habit = conn.execute(
        """
        SELECT *
        FROM habits
        WHERE id = ? AND user_email = ?
        """,
        (habit_id,session["user_email"])
    ).fetchone()
    conn.close()

    return render_template("edit_habit.html", habit=habit)


# Quick Actions 页面
# 从 actions 表读取所有预设活动，并显示在 quick_actions.html
@app.route("/quick_actions")
def quick_actions():

    # 没有登录就不能进入
    if "user_email" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("life_tracker.db")

    actions = conn.execute(
        """
        SELECT id, name, description, icon, color,
               benefit_1, benefit_2, benefit_3,
               default_goal_minutes
        FROM actions
        ORDER BY id
        """
    ).fetchall()

    conn.close()

    return render_template(
        "quick_actions.html",
        actions=actions
    )



# Log Activity 页面
# 用户选择一个 Activity 后，可以记录这次活动的资料
@app.route("/log_activity/<int:action_id>", methods=["GET", "POST"])
def log_activity(action_id):

    # 没有登录就不能进入
    if "user_email" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("life_tracker.db")

    # 根据 action_id 找到用户选择的 Activity
    action = conn.execute(
        """
        SELECT id, name, description, icon, color,
               benefit_1, benefit_2, benefit_3,
               default_goal_minutes
        FROM actions
        WHERE id = ?
        """,
        (action_id,)
    ).fetchone()

    # 如果找不到这个 Activity，就回到 Quick Actions
    if not action:
        conn.close()
        return redirect(url_for("quick_actions"))

    # 用户点击 Save Activity 后
    if request.method == "POST":

        duration_minutes = request.form.get("duration_minutes")
        log_date = request.form.get("log_date")
        notes = request.form.get("notes")
        mood = request.form.get("mood")
        productivity = request.form.get("productivity")
        energy = request.form.get("energy")

        # 把这一次 Activity 存进 logs 表
        conn.execute(
            """
            INSERT INTO logs
            (
                user_email,
                action_id,
                duration_minutes,
                log_date,
                notes,
                mood,
                productivity,
                energy
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["user_email"],
                action_id,
                duration_minutes,
                log_date,
                notes,
                mood,
                productivity,
                energy
            )
        )

        conn.commit()
        conn.close()

        # 保存完成后直接回到 Dashboard
        return redirect(url_for("dashboard"))

# 如果用户是从 Timer 页面来的，
# duration 会通过网址传过来
    timer_duration = request.args.get("duration")
# 自动取得今天的日期
# isoformat() 会变成 HTML date input 可以使用的格式
# 例如 2026-08-19
    today = date.today().isoformat()
    conn.close()

    return render_template(
        "log_activity.html",
        action=action,
        timer_duration=timer_duration,
        today=today
)



# Activities 页面
# 从 actions 表读取所有 Activity，然后显示在 activities.html
@app.route("/activities")
def activities():

    # 没有登录就不能进入
    if "user_email" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("life_tracker.db")

    actions = conn.execute(
        """
        SELECT id, name, description, icon, color,
               benefit_1, benefit_2, benefit_3,
               default_goal_minutes
        FROM actions
        ORDER BY id
        """
    ).fetchall()

    conn.close()

    return render_template(
        "activities.html",
        actions=actions
    )



# Activity Detail 页面
# 根据 action_id 显示某一个 Activity 的详细资料
@app.route("/activity/<int:action_id>")
def activity_detail(action_id):

    # 没有登录就不能进入
    if "user_email" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("life_tracker.db")

    # 找到用户点击的 Activity
    action = conn.execute(
        """
        SELECT id, name, description, icon, color,
               benefit_1, benefit_2, benefit_3,
               default_goal_minutes
        FROM actions
        WHERE id = ?
        """,
        (action_id,)
    ).fetchone()

    conn.close()

    # 如果这个 Activity 不存在，就回到 Activities
    if not action:
        return redirect(url_for("activities"))

    return render_template(
        "activity_detail.html",
        action=action
    )


# Activity Timer 页面
# 用户可以选择一个 Activity 后开始计时
@app.route("/timer/<int:action_id>")
def activity_timer(action_id):

    # 没有登录就不能进入 Timer
    if "user_email" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("life_tracker.db")

    # 根据 action_id 找到用户选择的 Activity
    action = conn.execute(
        """
        SELECT id, name, description, icon, color,
               benefit_1, benefit_2, benefit_3,
               default_goal_minutes
        FROM actions
        WHERE id = ?
        """,
        (action_id,)
    ).fetchone()

    conn.close()

    # 如果 Activity 不存在，就回到 Activities
    if not action:
        return redirect(url_for("activities"))

    return render_template(
        "timer.html",
        action=action
    )


# History 页面
# 显示当前登录用户以前记录过的所有 Activities
@app.route("/history")
def history():

    # 没有登录就不能进入
    if "user_email" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("life_tracker.db")

    # logs 保存用户的记录
    # actions 保存 Activity 的名字、icon 和颜色
    # JOIN 可以根据 action_id 把两个表连接起来
    logs = conn.execute(
        """
        SELECT
            logs.id,
            actions.name,
            actions.icon,
            actions.color,
            logs.duration_minutes,
            logs.log_date,
            logs.notes,
            logs.mood,
            logs.productivity,
            logs.energy
        FROM logs
        JOIN actions
            ON logs.action_id = actions.id
        WHERE logs.user_email = ?
        ORDER BY logs.log_date DESC, logs.id DESC
        """,
        (session["user_email"],)
    ).fetchall()

    conn.close()

    return render_template(
        "history.html",
        logs=logs
    )

if __name__ == "__main__":
    app.run(debug=True)