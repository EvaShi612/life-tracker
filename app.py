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


# 创建 actions 表
# actions 用来保存系统预设的活动类型
# 例如 Study Session、Exercise、Rest & Sleep、Social Time
def create_actions_table():
    conn = sqlite3.connect("life_tracker.db")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL,
            icon TEXT,
            color TEXT,
            benefit_1 TEXT,
            benefit_2 TEXT,
            benefit_3 TEXT,
            default_goal_minutes INTEGER DEFAULT 60
        )
    """)
    # 检查 actions 表里面有没有默认活动
    # 如果还是空的，就自动加入 4 个系统预设活动
    total = conn.execute(
        "SELECT COUNT(*) FROM actions"
    ).fetchone()[0]

    if total == 0:
        conn.executemany(
            """
            INSERT INTO actions
            (
                name,
                description,
                icon,
                color,
                benefit_1,
                benefit_2,
                benefit_3,
                default_goal_minutes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "Study Session",
                    "Focused learning and studying",
                    "📘",
                    "#2f7a57",
                    "Improves knowledge",
                    "Enhances focus",
                    "Career growth",
                    120
                ),
                (
                    "Exercise",
                    "Physical workout and fitness",
                    "🏋️",
                    "#3f8f62",
                    "Boosts energy",
                    "Improves health",
                    "Better mood",
                    60
                ),
                (
                    "Rest & Sleep",
                    "Quality rest and relaxation",
                    "🌙",
                    "#1f5c3f",
                    "Restores energy",
                    "Better focus",
                    "Mental clarity",
                    480
                ),
                (
                    "Social Time",
                    "Connecting with friends and family",
                    "👥",
                    "#6fae83",
                    "Reduces stress",
                    "Builds relationships",
                    "Happiness",
                    90
                )
            ]
        )
    conn.commit()
    conn.close()


# 创建 logs 表
# 用来记录用户每一次完成的 Activity
def create_logs_table():
    conn = sqlite3.connect("life_tracker.db")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_email TEXT NOT NULL,
            action_id INTEGER NOT NULL,

            duration_minutes INTEGER NOT NULL,
            log_date TEXT NOT NULL,

            notes TEXT,
            mood TEXT,
            productivity INTEGER,
            energy INTEGER,

            FOREIGN KEY (user_email)
                REFERENCES users(email),

            FOREIGN KEY (action_id)
                REFERENCES actions(id)
        )
    """)

    conn.commit()
    conn.close()

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

        return redirect(url_for("quick_actions"))

    conn.close()

    return render_template(
        "log_activity.html",
        action=action
    )

if __name__ == "__main__":
    update_habits_table()
    create_actions_table()
    create_logs_table()
    app.run(debug=True)