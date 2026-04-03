from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime

app = Flask(__name__)

# --- データベース接続設定 ---
def get_db_connection():
    # Renderの環境変数にDATABASE_URLがあればPostgreSQL、なければSQLite
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        # PostgreSQL接続 (本番環境)
        return psycopg2.connect(db_url)
    else:
        # SQLite接続 (ローカル環境)
        conn = sqlite3.connect('kakeibo.db')
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # PostgreSQLではSERIAL、SQLiteではAUTOINCREMENTと、挙動を合わせるための記述
    if os.environ.get('DATABASE_URL'):
        cur.execute('''
            CREATE TABLE IF NOT EXISTS records (
                id SERIAL PRIMARY KEY,
                date TEXT NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT,
                amount INTEGER NOT NULL,
                is_income INTEGER NOT NULL
            )
        ''')
    else:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT,
                amount INTEGER NOT NULL,
                is_income INTEGER NOT NULL
            )
        ''')
    conn.commit()
    cur.close()
    conn.close()

# 起動時にテーブル作成
with app.app_context():
    init_db()

# --- メイン画面 ---
@app.route('/')
def index():
    target_month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    conn = get_db_connection()

    # プレースホルダ(? か %s)とCursorの形式を切り替え
    is_pg = os.environ.get('DATABASE_URL')
    placeholder = '%s' if is_pg else '?'
    cur = conn.cursor(cursor_factory=DictCursor) if is_pg else conn.cursor()

    cur.execute(f'SELECT * FROM records WHERE date LIKE {placeholder} ORDER BY date DESC', (f"{target_month}%",))
    records = cur.fetchall()

    total_balance = 0
    category_totals = {}
    for row in records:
        if row['is_income'] == 1:
            total_balance += row['amount']
        else:
            total_balance -= row['amount']
            cat = row['category']
            category_totals[cat] = category_totals.get(cat, 0) + row['amount']

    cur.close()
    conn.close()
    return render_template('index.html', records=records, total=total_balance,
                           current_month=target_month, labels=list(category_totals.keys()),
                           values=list(category_totals.values()))

# --- データ登録 ---
@app.route('/add', methods=['POST'])
def add():
    date = request.form['date']
    category = request.form['category']
    subcategory = request.form['subcategory']
    amount = int(request.form['amount'])
    is_income = int(request.form['is_income'])

    conn = get_db_connection()
    cur = conn.cursor()
    placeholder = '%s' if os.environ.get('DATABASE_URL') else '?'

    cur.execute(f'''
        INSERT INTO records (date, category, subcategory, amount, is_income)
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
    ''', (date, category, subcategory, amount, is_income))

    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('index'))

# --- データ削除 ---
@app.route('/delete/<int:id>')
def delete(id):
    conn = get_db_connection()
    cur = conn.cursor()
    placeholder = '%s' if os.environ.get('DATABASE_URL') else '?'

    cur.execute(f'DELETE FROM records WHERE id = {placeholder}', (id,))

    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
