from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
import sqlite3


# =========================================================
# Flask 基础设置
# =========================================================

# Flask：创建网站
# render_template：打开 HTML 页面
# request：获取用户提交的数据
# redirect：跳转页面
# url_for：根据函数名寻找网址
# session：记住当前登录的人

app = Flask(__name__)
app.secret_key = "life-tracker-secret-key"


# =========================================================
# Home
# =========================================================

@app.route("/")
def home():

    # 已经登录的用户直接回 Dashboard
    if "user_email" in session:
        return redirect(url_for("dashboard"))

    # 没登录时显示 Landing Page
    return render_template("home.html")


# =========================================================
# Login
# =========================================================

# 访问 /login，执行 login()，打开 login.html
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = sqlite3.connect("life_tracker.db")

        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        conn.close()

        # user[3] 是数据库里的 hashed password
        if user and check_password_hash(user[3], password):

            # 登录成功后，session 记住用户 email
            session["user_email"] = email

            return redirect(url_for("dashboard"))

        else:
            return "Login failed"

    return render_template("login.html")


# =========================================================
# Register
# =========================================================

# 访问 /register，执行 register()，打开 register.html
# GET：显示注册页面
# POST：接收注册表单，把用户存进 users 表
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        # 注册时不保存原密码，先加密
        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect("life_tracker.db")

        conn.execute(
            """
            INSERT INTO users (name, email, password)
            VALUES (?, ?, ?)
            """,
            (name, email, hashed_password)
        )

        conn.commit()
        conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")


# =========================================================
# Dashboard
# =========================================================

@app.route("/dashboard")
def dashboard():

    # 从 session 找当前登录用户
    email = session.get("user_email")

    # 如果没有登录，就回到 Login
    if not email:
        return redirect(url_for("login"))

    conn = sqlite3.connect("life_tracker.db")

    # -----------------------------------------------------
    # 查询当前用户所有 Habit
    # 同时计算每个 Habit 今天已经完成多少分钟
    # -----------------------------------------------------

    habits = conn.execute(
        """
        SELECT
            habits.id,
            habits.habit_name,
            habits.details,
            habits.category,
            habits.frequency,
            habits.goal_minutes,
            habits.color,
            habits.action_id,

            COALESCE(SUM(logs.duration_minutes), 0)
                AS today_habit_minutes

        FROM habits

        LEFT JOIN logs
            ON logs.habit_id = habits.id
            AND logs.log_date = ?

        WHERE habits.user_email = ?

        GROUP BY
            habits.id,
            habits.habit_name,
            habits.details,
            habits.category,
            habits.frequency,
            habits.goal_minutes,
            habits.color,
            habits.action_id
        """,
        (
            date.today().isoformat(),
            email
        )
    ).fetchall()

    # -----------------------------------------------------
    # 查询今天总共记录了多少分钟
    # -----------------------------------------------------

    today_minutes = conn.execute(
        """
        SELECT COALESCE(SUM(duration_minutes), 0)
        FROM logs
        WHERE user_email = ?
        AND log_date = ?
        """,
        (
            email,
            date.today().isoformat()
        )
    ).fetchone()[0]


    # -----------------------------------------------------
    # 查询今天记录了多少次 Activity
    # -----------------------------------------------------

    today_sessions = conn.execute(
        """
        SELECT COUNT(*)
        FROM logs
        WHERE user_email = ?
        AND log_date = ?
        """,
        (
            email,
            date.today().isoformat()
        )
    ).fetchone()[0]


    # -----------------------------------------------------
    # 查询当前用户一共有多少个 Habit
    # -----------------------------------------------------

    total_habits = conn.execute(
        """
        SELECT COUNT(*)
        FROM habits
        WHERE user_email = ?
        """,
        (email,)
    ).fetchone()[0]


    # -----------------------------------------------------
    # 查询最近一条 Activity
    # -----------------------------------------------------

    recent_activity = conn.execute(
        """
        SELECT
            actions.name,
            actions.icon,
            logs.duration_minutes,
            logs.log_date,
            logs.mood,
            logs.productivity
        FROM logs
        JOIN actions
            ON logs.action_id = actions.id
        WHERE logs.user_email = ?
        ORDER BY logs.log_date DESC, logs.id DESC
        LIMIT 1
        """,
        (email,)
    ).fetchone()


    # -----------------------------------------------------
    # 查询总 Active Days
    # 同一天有多个 Activity 也只算一天
    # -----------------------------------------------------

    active_days = conn.execute(
        """
        SELECT COUNT(DISTINCT log_date)
        FROM logs
        WHERE user_email = ?
        """,
        (email,)
    ).fetchone()[0]


    # -----------------------------------------------------
    # 取得所有有 Activity 的日期
    # 用来计算连续活跃天数 Streak
    # -----------------------------------------------------

    active_dates = conn.execute(
        """
        SELECT DISTINCT log_date
        FROM logs
        WHERE user_email = ?
        ORDER BY log_date DESC
        """,
        (email,)
    ).fetchall()

    # 把 [('2026-08-20',), ('2026-08-19',)]
    # 转换成 ['2026-08-20', '2026-08-19']
    active_dates = [row[0] for row in active_dates]


    # -----------------------------------------------------
    # 计算 Streak
    # 从今天开始往前检查连续有 Activity 的日期
    # -----------------------------------------------------

    streak = 0
    current_date = date.today()

    for active_date in active_dates:

        if active_date == current_date.isoformat():

            streak += 1

            current_date = current_date.fromordinal(
                current_date.toordinal() - 1
            )

        elif active_date < current_date.isoformat():

            break


    conn.close()


    # -----------------------------------------------------
    # 把所有 Dashboard 数据传给 dashboard.html
    # -----------------------------------------------------

    return render_template(
        "dashboard.html",
        email=email,
        habits=habits,
        today_minutes=today_minutes,
        today_sessions=today_sessions,
        total_habits=total_habits,
        recent_activity=recent_activity,
        active_days=active_days,
        streak=streak
    )



# =========================================================
# Logout
# =========================================================

@app.route("/logout")
def logout():

    # 清空 session = 用户退出登录
    session.clear()

    return redirect(url_for("login"))


# =========================================================
# Create Habit
# =========================================================

@app.route("/create", methods=["GET", "POST"])
def create_habit():

    # 如果没有登录，就回到 Login
    if "user_email" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("life_tracker.db")


    # -----------------------------------------------------
    # 读取所有 Activity
    # 让用户创建 Habit 时可以选择关联的 Activity
    # -----------------------------------------------------

    actions = conn.execute(
        """
        SELECT id, name
        FROM actions
        ORDER BY id
        """
    ).fetchall()


    # -----------------------------------------------------
    # POST：保存新 Habit
    # -----------------------------------------------------

    if request.method == "POST":

        habit_name = request.form.get("habit_name")
        details = request.form.get("details")
        category = request.form.get("category", "Other")
        frequency = request.form.get("frequency", "Daily")
        goal_minutes = request.form.get("goal_minutes", 30)
        color = request.form.get("color", "#2f7a57")

        # 取得用户选择的 Linked Activity
        action_id = request.form.get("action_id")

        # 如果用户没有选择 Activity，
        # 就存成 None
        if action_id == "":
            action_id = None

        conn.execute(
            """
            INSERT INTO habits
            (
                user_email,
                habit_name,
                details,
                category,
                frequency,
                goal_minutes,
                color,
                action_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["user_email"],
                habit_name,
                details,
                category,
                frequency,
                goal_minutes,
                color,
                action_id
            )
        )

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))


    # -----------------------------------------------------
    # GET：打开 Create Habit 页面
    # -----------------------------------------------------

    conn.close()

    return render_template(
        "create_habit.html",
        actions=actions
    )



# =========================================================
# Delete Habit
# =========================================================

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
        WHERE id = ?
        AND user_email = ?
        """,
        (
            habit_id,
            session["user_email"]
        )
    )

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))


# =========================================================
# Edit Habit
# =========================================================

@app.route("/edit/<int:habit_id>", methods=["GET", "POST"])
def edit_habit(habit_id):

    # 如果没有登录，就回到 Login
    if "user_email" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("life_tracker.db")


    # -----------------------------------------------------
    # POST：保存修改后的 Habit
    # -----------------------------------------------------

    if request.method == "POST":

        habit_name = request.form.get("habit_name")
        details = request.form.get("details")
        category = request.form.get("category", "Other")
        frequency = request.form.get("frequency", "Daily")
        goal_minutes = request.form.get("goal_minutes", 30)
        color = request.form.get("color", "#2f7a57")

        # 根据 habit_id 找到原来的 Habit，并更新所有资料
        # 同时检查 user_email，只允许修改自己的 Habit
        conn.execute(
            """
            UPDATE habits
            SET
                habit_name = ?,
                details = ?,
                category = ?,
                frequency = ?,
                goal_minutes = ?,
                color = ?
            WHERE id = ?
            AND user_email = ?
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


    # -----------------------------------------------------
    # GET：打开 Edit 页面
    # -----------------------------------------------------

    habit = conn.execute(
        """
        SELECT *
        FROM habits
        WHERE id = ?
        AND user_email = ?
        """,
        (
            habit_id,
            session["user_email"]
        )
    ).fetchone()

    conn.close()

    return render_template(
        "edit_habit.html",
        habit=habit
    )


# =========================================================
# Quick Actions
# =========================================================

@app.route("/quick_actions")
def quick_actions():

    # 没有登录就不能进入
    if "user_email" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("life_tracker.db")

    # 从 actions 表读取所有预设 Activity
    actions = conn.execute(
        """
        SELECT
            id,
            name,
            description,
            icon,
            color,
            benefit_1,
            benefit_2,
            benefit_3,
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


# =========================================================
# Log Activity
# =========================================================

@app.route("/log_activity/<int:action_id>", methods=["GET", "POST"])
def log_activity(action_id):

    # 没有登录就不能进入
    if "user_email" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("life_tracker.db")


    # -----------------------------------------------------
    # 找到用户选择的 Activity
    # -----------------------------------------------------

    action = conn.execute(
        """
        SELECT
            id,
            name,
            description,
            icon,
            color,
            benefit_1,
            benefit_2,
            benefit_3,
            default_goal_minutes
        FROM actions
        WHERE id = ?
        """,
        (action_id,)
    ).fetchone()


    # 如果 Activity 不存在
    if not action:
        conn.close()
        return redirect(url_for("quick_actions"))


    # -----------------------------------------------------
    # 先取得 Timer 和 Habit 传过来的资料
    # -----------------------------------------------------

    # Timer 自动传来的分钟数
    timer_duration = request.args.get("duration")

    # 如果是从 Habit 开始的，
    # URL 里会有 habit_id
    habit_id = request.args.get("habit_id")

    # 自动取得今天日期
    today = date.today().isoformat()


    # -----------------------------------------------------
    # POST：保存 Activity
    # -----------------------------------------------------

    if request.method == "POST":

        duration_minutes = request.form.get("duration_minutes")
        log_date = request.form.get("log_date")
        notes = request.form.get("notes")
        mood = request.form.get("mood")
        productivity = request.form.get("productivity")
        energy = request.form.get("energy")

        # hidden input 会把 habit_id 一起送回来
        habit_id = request.form.get("habit_id")

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
                energy,
                habit_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["user_email"],
                action_id,
                duration_minutes,
                log_date,
                notes,
                mood,
                productivity,
                energy,
                habit_id
            )
        )

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))


    conn.close()


    # -----------------------------------------------------
    # GET：打开 Log Activity 页面
    # -----------------------------------------------------

    return render_template(
        "log_activity.html",
        action=action,
        timer_duration=timer_duration,
        today=today,
        habit_id=habit_id
    )

# =========================================================
# Activities
# =========================================================

@app.route("/activities")
def activities():

    # 没有登录就不能进入
    if "user_email" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("life_tracker.db")

    actions = conn.execute(
        """
        SELECT
            id,
            name,
            description,
            icon,
            color,
            benefit_1,
            benefit_2,
            benefit_3,
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


# =========================================================
# Activity Detail
# =========================================================

@app.route("/activity/<int:action_id>")
def activity_detail(action_id):

    # 没有登录就不能进入
    if "user_email" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("life_tracker.db")

    # 根据 action_id 找 Activity
    action = conn.execute(
        """
        SELECT
            id,
            name,
            description,
            icon,
            color,
            benefit_1,
            benefit_2,
            benefit_3,
            default_goal_minutes
        FROM actions
        WHERE id = ?
        """,
        (action_id,)
    ).fetchone()

    conn.close()


    # 如果 Activity 不存在
    if not action:
        return redirect(url_for("activities"))


    return render_template(
        "activity_detail.html",
        action=action
    )


# =========================================================
# Activity Timer
# =========================================================

@app.route("/timer/<int:action_id>")
def activity_timer(action_id):

    # 没有登录就不能进入 Timer
    if "user_email" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("life_tracker.db")

    # 找到用户选择的 Activity
    action = conn.execute(
        """
        SELECT
            id,
            name,
            description,
            icon,
            color,
            benefit_1,
            benefit_2,
            benefit_3,
            default_goal_minutes
        FROM actions
        WHERE id = ?
        """,
        (action_id,)
    ).fetchone()

    conn.close()

    # 如果 Activity 不存在
    if not action:
        return redirect(url_for("activities"))

    # 如果是从 Habit 的 Start 按钮进来的，
    # URL 里会带着 habit_id
    habit_id = request.args.get("habit_id")

    return render_template(
        "timer.html",
        action=action,
        habit_id=habit_id
    )


# =========================================================
# History
# =========================================================

@app.route("/history")
def history():

    # 没有登录就不能进入
    if "user_email" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("life_tracker.db")


    # logs 保存用户 Activity records
    # actions 保存 Activity 的名字、icon、color
    # JOIN 根据 action_id 把两张表连接起来
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


# =========================================================
# Run Flask
# =========================================================

if __name__ == "__main__":
    app.run(debug=True)