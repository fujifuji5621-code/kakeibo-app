from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

DATABASE = "kakeibo.db"

# データベース接続用の関数
def get_db_connection():
    conn = sqlite3.connect('kakeibo.db')
    # これを設定することで、結果を辞書形式（row['category']など）で取得できる
    conn.row_factory = sqlite3.Row
    return conn

# 起動時にテーブルを作成する関数
def init_db():
    conn = get_db_connection()
    conn.execute('''
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
    conn.close()

# アプリ起動時の初期化処理
with app.app_context():
    init_db()


# メイン画面（表示・集計）
@app.route('/')
def index():
    # ブラウザから表示月を取得（指定がなければ現在の月）
    target_month = request.args.get('month', datetime.now().strftime('%Y-%m'))

    conn = get_db_connection()
    # SQLの LIKE を使って、指定した月のデータのみを取得
    query = 'SELECT * FROM records WHERE date LIKE ? ORDER BY date DESC'
    records = conn.execute(query, (f"{target_month}%",)).fetchall()

    # --- 集計処理 ---
    total_balance = 0
    category_totals = {} # グラフ用の支出集計

    for row in records:
        amount = row['amount']
        if row['is_income'] == 1:
            total_balance += amount
        else:
            total_balance -= amount
            # 支出のみカテゴリごとに加算（グラフ用）
            cat = row['category']
            category_totals[cat] = category_totals.get(cat, 0) + amount

    conn.close()

    # Chart.jsに渡すために「ラベル」と「値」のリストに分ける
    chart_labels = list(category_totals.keys())
    chart_values = list(category_totals.values())

    return render_template('index.html',
                           records=records,
                           total=total_balance,
                           current_month=target_month,
                           labels=chart_labels,
                           values=chart_values)

# データ登録処理
@app.route('/add', methods=['POST'])
def add():
    date = request.form['date']
    category = request.form['category']
    subcategory = request.form['subcategory']
    amount = int(request.form['amount'])
    is_income = int(request.form['is_income'])

    conn = get_db_connection()
    conn.execute('''
        INSERT INTO records (date, category, subcategory, amount, is_income)
        VALUES (?, ?, ?, ?, ?)
    ''', (date, category, subcategory, amount, is_income))
    conn.commit()
    conn.close()

    # 登録後はトップページに戻る（登録したデータの月に合わせる場合は工夫が必要ですが、まずは簡易的に）
    return redirect(url_for('index'))

# データ削除処理
@app.route('/delete/<int:id>')
def delete(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM records WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # debug=True にするとコードを書き換えたときに自動で再起動してくれる
    app.run(debug=True)

