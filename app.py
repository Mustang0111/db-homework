from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

# 连接数据库
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# 初始化数据库
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    # 删除旧表
    cur.execute("DROP TABLE IF EXISTS orders")
    cur.execute("DROP TABLE IF EXISTS item")
    cur.execute("DROP TABLE IF EXISTS user")

    # 用户表
    cur.execute("""
    CREATE TABLE user (
        user_id TEXT PRIMARY KEY,
        user_name TEXT NOT NULL,
        phone TEXT
    )
    """)

    # 商品表
    cur.execute("""
    CREATE TABLE item (
        item_id TEXT PRIMARY KEY,
        item_name TEXT NOT NULL,
        category TEXT,
        price REAL,
        seller_id TEXT,
        status INTEGER DEFAULT 0,
        FOREIGN KEY (seller_id) REFERENCES user(user_id)
    )
    """)

    # 订单表
    cur.execute("""
    CREATE TABLE orders (
        order_id TEXT PRIMARY KEY,
        buyer_id TEXT,
        item_id TEXT UNIQUE,
        order_date TEXT,
        FOREIGN KEY (buyer_id) REFERENCES user(user_id),
        FOREIGN KEY (item_id) REFERENCES item(item_id)
    )
    """)

    # 插入用户数据
    users = [
        ('u001', '张三', '111111'),
        ('u002', '李四', '222222'),
        ('u003', '王五', '333333')
    ]

    cur.executemany(
        "INSERT INTO user VALUES (?, ?, ?)",
        users
    )

    # 插入商品数据
    items = [
        ('i001', '高数教材', '学习用品', 25, 'u001', 0),
        ('i002', '台灯', '生活用品', 35, 'u001', 1),
        ('i003', '键盘', '电子产品', 80, 'u002', 0),
        ('i004', '水杯', '生活用品', 20, 'u003', 1)
    ]

    cur.executemany(
        "INSERT INTO item VALUES (?, ?, ?, ?, ?, ?)",
        items
    )

    # 插入订单数据
    orders = [
        ('o001', 'u002', 'i002', '2026-05-01'),
        ('o002', 'u001', 'i004', '2026-05-03')
    ]

    cur.executemany(
        "INSERT INTO orders VALUES (?, ?, ?, ?)",
        orders
    )

    # 删除旧视图
    cur.execute("DROP VIEW IF EXISTS sold_items")
    cur.execute("DROP VIEW IF EXISTS unsold_items")

    # 创建视图
    cur.execute("""
    CREATE VIEW sold_items AS
    SELECT item.item_name, orders.buyer_id
    FROM item
    JOIN orders ON item.item_id = orders.item_id
    """)

    cur.execute("""
    CREATE VIEW unsold_items AS
    SELECT * FROM item
    WHERE status = 0
    """)

    conn.commit()
    conn.close()

# 首页
@app.route('/')
def index():
    return render_template('index.html')

# 商品列表
@app.route('/items')
def items():
    conn = get_db_connection()
    items = conn.execute("SELECT * FROM item").fetchall()
    conn.close()
    return render_template('items.html', items=items)

# 用户列表
@app.route('/users')
def users():
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM user").fetchall()
    conn.close()
    return render_template('users.html', users=users)

# 订单列表
@app.route('/orders')
def orders():
    conn = get_db_connection()
    orders = conn.execute("SELECT * FROM orders").fetchall()
    conn.close()
    return render_template('orders.html', orders=orders)

# 查询页面
@app.route('/queries')
def queries():
    conn = get_db_connection()

    unsold = conn.execute(
        "SELECT * FROM item WHERE status = 0"
    ).fetchall()

    expensive = conn.execute(
        "SELECT * FROM item WHERE price > 30"
    ).fetchall()

    life_items = conn.execute(
        "SELECT * FROM item WHERE category = '生活用品'"
    ).fetchall()

    u001_items = conn.execute(
        "SELECT * FROM item WHERE seller_id = 'u001'"
    ).fetchall()

    sold_with_buyer = conn.execute("""
    SELECT item.item_name, user.user_name
    FROM orders
    JOIN item ON orders.item_id = item.item_id
    JOIN user ON orders.buyer_id = user.user_id
    """).fetchall()

    conn.close()

    return render_template(
        'queries.html',
        unsold=unsold,
        expensive=expensive,
        life_items=life_items,
        u001_items=u001_items,
        sold_with_buyer=sold_with_buyer
    )

# 统计页面
@app.route('/stats')
# 添加商品
@app.route('/add_item', methods=['GET', 'POST'])
def add_item():

    if request.method == 'POST':

        item_id = request.form['item_id']
        item_name = request.form['item_name']
        category = request.form['category']
        price = request.form['price']
        seller_id = request.form['seller_id']

        conn = get_db_connection()

        conn.execute("""
        INSERT INTO item
        (item_id, item_name, category, price, seller_id, status)
        VALUES (?, ?, ?, ?, ?, 0)
        """, (item_id, item_name, category, price, seller_id))

        conn.commit()
        conn.close()

        return redirect('/items')

    return render_template('add_item.html')


# 修改商品价格
@app.route('/update_price', methods=['GET', 'POST'])
def update_price():

    if request.method == 'POST':

        item_id = request.form['item_id']
        new_price = request.form['new_price']

        conn = get_db_connection()

        conn.execute("""
        UPDATE item
        SET price = ?
        WHERE item_id = ?
        """, (new_price, item_id))

        conn.commit()
        conn.close()

        return redirect('/items')

    return render_template('update_price.html')


# 删除未售商品
@app.route('/delete_item', methods=['GET', 'POST'])
def delete_item():

    if request.method == 'POST':

        item_id = request.form['item_id']

        conn = get_db_connection()

        conn.execute("""
        DELETE FROM item
        WHERE item_id = ?
        AND status = 0
        """, (item_id,))

        conn.commit()
        conn.close()

        return redirect('/items')

    return render_template('delete_item.html')


# 购买商品
@app.route('/buy_item', methods=['GET', 'POST'])
def buy_item():

    if request.method == 'POST':

        order_id = request.form['order_id']
        buyer_id = request.form['buyer_id']
        item_id = request.form['item_id']
        order_date = request.form['order_date']

        conn = get_db_connection()

        # 检查商品是否已售出
        item = conn.execute("""
        SELECT * FROM item
        WHERE item_id = ?
        """, (item_id,)).fetchone()

        if item['status'] == 1:
            conn.close()
            return "该商品已经售出！"

        # 插入订单
        conn.execute("""
        INSERT INTO orders
        (order_id, buyer_id, item_id, order_date)
        VALUES (?, ?, ?, ?)
        """, (order_id, buyer_id, item_id, order_date))

        # 修改商品状态
        conn.execute("""
        UPDATE item
        SET status = 1
        WHERE item_id = ?
        """, (item_id,))

        conn.commit()
        conn.close()

        return redirect('/orders')

    return render_template('buy_item.html')
def stats():
    conn = get_db_connection()

    total = conn.execute(
        "SELECT COUNT(*) AS total FROM item"
    ).fetchone()

    category = conn.execute("""
    SELECT category, COUNT(*) AS count
    FROM item
    GROUP BY category
    """).fetchall()

    avg_price = conn.execute(
        "SELECT AVG(price) AS avg FROM item"
    ).fetchone()

    top_user = conn.execute("""
    SELECT seller_id, COUNT(*) AS count
    FROM item
    GROUP BY seller_id
    ORDER BY count DESC
    LIMIT 1
    """).fetchone()

    conn.close()

    return render_template(
        'stats.html',
        total=total,
        category=category,
        avg_price=avg_price,
        top_user=top_user
    )

if __name__ == '__main__':

    import os

    # 数据库不存在时才初始化
    if not os.path.exists('database.db'):
        init_db()

    port = int(os.environ.get("PORT", 10000))

    app.run(host='0.0.0.0', port=port)