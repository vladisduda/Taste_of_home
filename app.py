import os
import secrets
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from datetime import timedelta

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Генерация безопасного секретного ключа

# Путь к папке для загрузки изображений
UPLOAD_FOLDER = os.path.join(app.root_path, "static", "img")  # Путь к папке static/img
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
# Создайте директорию, если она не существует
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Конфигурация MySQL
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "t_o_h_bd"

# Инициализация MySQL и LoginManager
mysql = MySQL(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"  # Название маршрута для входа


class User(UserMixin):

    def __init__(self, id_user, number, name, role):
        self.id = id_user
        self.number = number
        self.name = name
        self.role = role


@login_manager.user_loader
def load_user(id_user):
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT id_user, number, name, role FROM user WHERE id_user = %s",
        (id_user,),
    )
    user_data = cur.fetchone()
    cur.close()
    if user_data:
        return User(
            user_data[0],
            user_data[1],
            user_data[2],
            user_data[3],
        )  # id_user, number, name, role
    return None


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/login", methods=["POST"])
def login():
    error = None

    number = request.form["number"]
    password = request.form["password"]

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM user WHERE number = %s", (number,))
    user_data = cur.fetchone()
    cur.close()

    if user_data and check_password_hash(user_data[2], password):
        user = User(
            user_data[0],
            user_data[1],
            user_data[2],
            user_data[3],
        )
        login_user(user)
        return jsonify(success=True)
    else:
        error = "Неправильное имя пользователя или пароль."
        return jsonify(success=False, error=error)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        password = request.form["password"]
        number = request.form["number"]
        name = request.form.get("name", None)
        address = request.form["address"]
        role = request.form["role"]
        email = request.form.get("email", None)
        about_me = request.form.get("about_me", None)
        date_of_birth = request.form.get("date_of_birth", None)

        # Проверка на существующего пользователя
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM user WHERE number = %s", (number,))
        existing_user = cur.fetchone()

        if existing_user:
            print("Пользователь с таким номером уже существует.")
            return redirect(url_for("register"))

        # Хеширование пароля и добавление пользователя в БД
        hashed_password = generate_password_hash(password)
        cur.execute(
            """
            INSERT INTO user (number, password, name, address, role, date_of_birth, email, about_me)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                number,
                hashed_password,
                name,
                address,
                role,
                date_of_birth,
                email,
                about_me,
            ),
        )
        mysql.connection.commit()
        cur.close()

        print("Вы успешно зарегистрированы! Теперь вы можете войти в систему.")
        return redirect(url_for("index"))

    return render_template("register.html")


# ___________________
def get_notification_count():
    cur = mysql.connection.cursor()
    query = ""
    params = ()

    if current_user.role in ["chef", "admin"]:
        # Запрос для повара или администратора
        query = """
        SELECT COUNT(*) 
        FROM orders
        JOIN dish ON orders.id_dish = dish.id_dish
        JOIN status_order ON orders.id_orders = status_order.id_order
        WHERE dish.id_user = %s
        AND status_order.status = 'issued'
        """
        params = (current_user.id,)

    elif current_user.role == "courier":
        # Запрос для курьера
        query = """
        SELECT COUNT(*) 
        FROM orders
        JOIN dish ON orders.id_dish = dish.id_dish
        JOIN status_order ON orders.id_orders = status_order.id_order
        WHERE status_order.status = 'ready and awaiting delivery'
        """
        # Нет необходимости передавать current_user.id
        params = ()

    if query:
        cur.execute(query, params)
        notification_count = cur.fetchone()[0] if cur.rowcount > 0 else 0
    else:
        notification_count = 0

    cur.close()
    return notification_count


@app.context_processor
def inject_notification_count():
    if current_user.is_authenticated:
        notification_count = get_notification_count()
    else:
        notification_count = (
            0  # Для неавторизованных пользователей уведомления не отображаем
        )
    return dict(notification_count=notification_count)


# ___________________


@app.context_processor
def inject_dish():

    def get_dish_name_by_id(id_dish):
        try:
            cur = mysql.connection.cursor()
            query = "SELECT name FROM dish WHERE id_dish = %s"
            cur.execute(query, (id_dish,))
            result = cur.fetchone()
            cur.close()
            return result[0] if result else "Неизвестное блюдо (ИМЯ)"
        except Exception as e:
            print(f"(ИМЯ) Ошибка при выполнении запроса: {e}")
            return "(ИМЯ) Ошибка получения данных"

    def get_dish_address_by_id(id_dish):
        try:
            cur = mysql.connection.cursor()
            query = "SELECT address FROM dish WHERE id_dish = %s"
            cur.execute(query, (id_dish,))
            result = cur.fetchone()
            cur.close()
            return result[0] if result else "Неизвестное блюдо (Адрес)"
        except Exception as e:
            print(f"(Адрес) Ошибка при выполнении запроса: {e}")
            return "(Адрес) Ошибка получения данных"

    # Возвращаем функцию, чтобы она была доступна в шаблонах
    return dict(
        get_dish_name_by_id=get_dish_name_by_id,
        get_dish_address_by_id=get_dish_address_by_id,
    )


# ___________________
@app.context_processor
def inject_user_name():
    def get_user_name_by_id(id_user):
        try:
            cur = mysql.connection.cursor()
            query = "SELECT name FROM user WHERE id_user = %s"
            cur.execute(query, (id_user,))
            result = cur.fetchone()
            cur.close()
            return result[0] if result else "Отсутствует"
        except Exception as e:
            print(f"(ИМЯ) Ошибка при выполнении запроса: {e}")
            return "(ИМЯ) Ошибка получения данных"

    # Возвращаем функцию, чтобы она была доступна в шаблонах
    return dict(get_user_name_by_id=get_user_name_by_id)


# ___________________
@app.context_processor
def utility_processor():
    def format_time(time_obj):
        if not time_obj:
            return "Не указано"
        if isinstance(time_obj, timedelta):
            total_seconds = int(time_obj.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            if hours == 0:
                return f"{minutes} мин"
            return f"{hours}:{minutes:02} час"
        return str(time_obj)

    return dict(format_time=format_time)


# ___________________


@app.route("/notifications")
@login_required
def notifications():
    cur = (
        mysql.connection.cursor()
    )  # Используем dictionary=True для удобного доступа к данным

    if current_user.role == "chef":
        # Если пользователь — повар, берутся данные только его блюд
        query = """
        SELECT 
            orders.id_orders, 
            orders.id_user AS order_user, 
            orders.id_dish, 
            orders.id_courier, 
            orders.date, 
            orders.price, 
            orders.quantity, 
            orders.address, 
            orders.wish,
            status_order.status,
            status_order.estimated_time
        FROM orders
        JOIN dish ON orders.id_dish = dish.id_dish
        JOIN status_order ON orders.id_orders = status_order.id_order
        WHERE dish.id_user = %s
        """
        cur.execute(query, (current_user.id,))

    elif current_user.role == "courier":
        # Если пользователь — курьер, берутся все данные
        query = """
        SELECT 
            orders.id_orders, 
            orders.id_user AS order_user, 
            orders.id_dish, 
            orders.id_courier, 
            orders.date, 
            orders.price, 
            orders.quantity, 
            orders.address, 
            orders.wish,
            status_order.status,
            status_order.estimated_time
        FROM orders
        JOIN dish ON orders.id_dish = dish.id_dish
        JOIN status_order ON orders.id_orders = status_order.id_order
        """
        cur.execute(query)

    else:
        # Если роль пользователя не соответствует требованиям, возвращаем пустой список
        notifications = []
        cur.close()
        return render_template("notifications.html", notifications=notifications)

    # Получаем результаты
    notifications = cur.fetchall()
    cur.close()

    return render_template(
        "notifications.html",
        notifications=notifications,
    )


@app.route("/update_status/<int:id_order>", methods=["POST"])
@login_required
def update_status(id_order):
    new_status = request.form.get("status")

    if current_user.role == "courier":
        id_courier = current_user.id
        if new_status == "on the way":
            cur = mysql.connection.cursor()
            cur.execute(
                """
                UPDATE orders
                SET id_courier = %s
                WHERE id_orders = %s
            """,
                (id_courier, id_order),
            )
            mysql.connection.commit()
            cur.close()

            print("Курьер успешно откликнулся на заказ.")
        else:
            print("Ошибка добавления курьера.")

    if new_status:
        cur = mysql.connection.cursor()
        # Обновляем статус заказа в таблице status_order
        cur.execute(
            """
            UPDATE status_order
            SET status = %s
            WHERE id_order = %s
        """,
            (new_status, id_order),
        )
        mysql.connection.commit()
        cur.close()

        print("Статус заказа успешно обновлен.")
    else:
        print("Ошибка обновления статуса.")

    return redirect(url_for("notifications"))


@app.route("/")
def index():
    # Открываем соединение с базой данных
    cur = mysql.connection.cursor()

    # Выполняем запрос для получения всех блюд
    cur.execute("SELECT * FROM dish")
    dishes = cur.fetchall()  # Извлекаем все записи

    cur.close()

    # Передаем данные блюд на главную страницу

    return render_template("index.html", dishes=dishes)


@app.route("/dish/<int:id_dish>")
def detail_dish(id_dish):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM dish WHERE id_dish = %s", (id_dish,))
    dish = cur.fetchone()
    cur.close()

    return render_template("detail_dish.html", dish=dish)


@app.route("/add_order/<int:id_dish>", methods=["GET", "POST"])
@login_required
def add_order(id_dish):
    cur = mysql.connection.cursor()
    id_user = current_user.id
    if request.form.get("default address"):
        cur = mysql.connection.cursor()
        query = "SELECT address FROM user WHERE id_user = %s"
        cur.execute(query, (id_user,))
        address = cur.fetchone()

    else:
        address = request.form.get("address")
    try:
        # Получаем данные о блюде по его id
        cur.execute(
            "SELECT name, price, description FROM dish WHERE id_dish = %s", (id_dish,)
        )
        dish = cur.fetchone()

        if not dish:
            return jsonify(success=False, error="Блюдо не найдено."), 404

        if request.method == "POST":

            wish = request.form.get("wish", None)
            quantity = int(request.form.get("quantity", 1))

            price_per_item = float(dish[1])
            total_price = price_per_item * quantity

            # Добавляем новый заказ в таблицу orders
            cur.execute(
                """
                INSERT INTO orders (id_user, id_dish, id_courier, date, price, quantity, address, wish)
                VALUES (%s, %s, NULL, NOW(), %s, %s, %s, %s)
                """,
                (id_user, id_dish, total_price, quantity, address, wish),
            )
            mysql.connection.commit()

            # Получаем id последнего заказа для уведомления
            cur.execute(
                """
                SELECT id_orders FROM orders
                WHERE id_user = %s AND DATE(date) = CURDATE()
                ORDER BY id_orders DESC LIMIT 1
                """,
                (id_user,),
            )
            result = cur.fetchone()
            id_order = result[0] if result else None

            # Получаем время приготовления блюда
            cur.execute("SELECT time FROM dish WHERE id_dish = %s", (id_dish,))
            result = cur.fetchone()
            estimated_time = result[0] if result else None
            # Добавляем запись в таблицу status_order
            cur.execute(
                """
                    INSERT INTO status_order (id_order, status, estimated_time)
                    VALUES (%s, %s, %s)
                    """,
                (id_order, "issued", estimated_time),
            )
            mysql.connection.commit()

            print("Заказ успешно оформлен")
            return redirect(url_for("index"))

    except Exception as e:
        mysql.connection.rollback()
        return (
            jsonify(
                success=False, error=f"Произошла ошибка при оформлении заказа: {str(e)}"
            ),
            500,
        )

    finally:
        cur.close()

    # Передаем данные блюда в шаблон
    return render_template("add_order.html", id_dish=id_dish, dish=dish)


@app.route("/add_dish", methods=["GET", "POST"])
@login_required
def add_dish():
    if request.method == "POST":
        # Получаем данные из формы
        id_user = current_user.id  # Используем текущего пользователя
        name = request.form["name"]
        price = request.form["price"]
        description = request.form["description"]
        ingredients = request.form["ingredients"]
        alcohol = request.form.get("alcohol") == "on"

        if request.form.get("default address"):
            cur = mysql.connection.cursor()
            query = "SELECT address FROM user WHERE id_user = %s"
            cur.execute(query, (id_user,))
            address = cur.fetchone()
            cur.close()
            print(address)
        else:
            address = request.form["address"]

        time = request.form["time"]

        # Обработка изображений
        img_paths = []
        images = request.files.getlist("img")  # Получаем список файлов
        # Убедитесь, что директория для загрузки существует
        if not os.path.exists(app.config["UPLOAD_FOLDER"]):
            os.makedirs(app.config["UPLOAD_FOLDER"])

        for img in images:
            if img and img.filename != "":
                filename = secure_filename(img.filename)
                img_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                img.save(img_path)  # Сохраняем файл на диск
                img_paths.append(filename)  # Добавляем только имя файла в список

        # Преобразуем список путей в строку, разделенную запятыми
        img_paths_str = ",".join(img_paths)

        # Вставка нового блюда в базу данных вместе с путями к изображениям
        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO dish (id_user, name, price, description, ingredients, alcohol, address, time, img) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                id_user,
                name,
                price,
                description,
                ingredients,
                alcohol,
                address,
                time,
                img_paths_str,  # Сохраняем пути к изображениям в поле img
            ),
        )

        mysql.connection.commit()
        cur.close()
        print("Блюдо успешно добавлено.")
        return redirect(url_for("add_dish"))

    # Получение всех блюд для отображения
    cur = mysql.connection.cursor()
    # Проверяем роль текущего пользователя
    cur.execute("SELECT role FROM user WHERE id_user = %s", (current_user.id,))
    user = cur.fetchone()

    if user and user[0] == "admin":
        # Если пользователь - администратор, выбираем все блюда
        cur.execute("SELECT * FROM dish")
    else:
        # Если не администратор, выбираем только блюда текущего пользователя
        cur.execute("SELECT * FROM dish WHERE id_user = %s", (current_user.id,))
    dishes = cur.fetchall()
    cur.close()
    return render_template("add_dish.html", dishes=dishes)


@app.route("/edit_dish/<int:id_dish>", methods=["GET", "POST"])
@login_required
def edit_dish(id_dish):
    cur = mysql.connection.cursor()
    if request.method == "POST":
        # Получаем данные из формы
        id_user = current_user.id
        name = request.form["name"]
        price = request.form["price"]
        description = request.form["description"]
        ingredients = request.form["ingredients"]
        alcohol = request.form.get("alcohol") == "on"
        address = request.form["address"]
        time = request.form["time"]

        # Обработка изображений
        img_paths = []
        images = request.files.getlist("img")
        if not os.path.exists(app.config["UPLOAD_FOLDER"]):
            os.makedirs(app.config["UPLOAD_FOLDER"])

        # Если новые изображения были загружены, добавляем их
        if images:
            for img in images:
                if img and img.filename != "":
                    filename = secure_filename(img.filename)
                    img_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    img.save(img_path)
                    img_paths.append(filename)
            img_paths_str = ",".join(img_paths)
        else:
            # Если изображения не загружены, оставляем старые пути к изображениям
            cur.execute("SELECT img FROM dish WHERE id_dish = %s", (id_dish,))
            img_paths_str = cur.fetchone()[0]

        # Обновление существующего блюда
        cur.execute(
            "UPDATE dish SET id_user = %s, name = %s, price = %s, description = %s, ingredients = %s, alcohol = %s, address = %s, time = %s, img = %s WHERE id_dish = %s",
            (
                id_user,
                name,
                price,
                description,
                ingredients,
                alcohol,
                address,
                time,
                img_paths_str,
                id_dish,
            ),
        )

        mysql.connection.commit()
        cur.close()
        print("Блюдо успешно обновлено.")

        # Перенаправление на страницу блюда
        return redirect(url_for("detail_dish", id_dish=id_dish))

    # Получаем текущее состояние блюда для редактирования
    cur.execute("SELECT * FROM dish WHERE id_dish = %s", (id_dish,))
    dish = cur.fetchone()
    cur.close()
    return render_template("edit_dish.html", dish=dish)


@app.route("/delete_dish/<int:id_dish>", methods=["POST"])
@login_required
def delete_dish(id_dish):
    cur = mysql.connection.cursor()

    if cur.execute("SELECT * FROM orders WHERE id_dish  = %s", (id_dish,)):
        print("Блюдо связано с отзывами.", id_dish)
    else:
        cur.execute("DELETE FROM dish WHERE id_dish = %s", (id_dish,))
        mysql.connection.commit()
        cur.close()
        print("Блюдо успешно удалено.")
    return redirect(url_for("add_dish"))


@app.route("/orders")
@login_required
def orders():
    # Получение всех блюд для отображения
    cur = mysql.connection.cursor()
    # Проверяем роль текущего пользователя
    cur.execute("SELECT role FROM user WHERE id_user = %s", (current_user.id,))
    user = cur.fetchone()

    # Проверяем роль текущего пользователя
    if user and user[0] == "admin":
        # Если пользователь админ, возвращаем все заказы
        cur.execute(
            "SELECT orders.*, status_order.status FROM orders, status_order WHERE orders.id_orders = status_order.id_order"
        )

    else:
        # Если пользователь не админ, возвращаем только его заказы
        cur.execute(
            "SELECT orders.*, status_order.status FROM orders, status_order WHERE id_user = %s AND orders.id_orders = status_order.id_order",
            (current_user.id,),
        )

    orders = cur.fetchall()  # Получаем все заказы или только заказы пользователя
    cur.close()

    return render_template("orders.html", orders=orders)


if __name__ == "__main__":
    app.run(debug=True)
