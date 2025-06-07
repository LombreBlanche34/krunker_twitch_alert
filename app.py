from flask import Flask, request, render_template, g, redirect, url_for
import sqlite3
import json
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
DATABASE = os.getenv('DATABASE')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        c = db.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                host TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL
            )
        ''')
        db.commit()

@app.route('/')
def index():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM messages ORDER BY timestamp DESC LIMIT 100")
    messages = cursor.fetchall()

    cursor.execute("SELECT host, COUNT(*) FROM messages GROUP BY host ORDER BY COUNT(*) DESC")
    chart_data = cursor.fetchall()

    return render_template('index.html', messages=messages, chart_data=json.dumps(chart_data))

@app.route('/search')
def search():
    query = request.args.get('query', '')
    search_by = request.args.get('search_by', 'message')

    conn = get_db()
    cursor = conn.cursor()

    if search_by == 'host':
        cursor.execute("SELECT * FROM messages WHERE host LIKE ? ORDER BY timestamp DESC", (f'%{query}%',))
        messages = cursor.fetchall()
        cursor.execute("SELECT sender, COUNT(*) FROM messages WHERE host LIKE ? GROUP BY sender ORDER BY COUNT(*) DESC", (f'%{query}%',))
        chart_data = cursor.fetchall()
    elif search_by == 'sender':
        cursor.execute("SELECT * FROM messages WHERE sender LIKE ? ORDER BY timestamp DESC", (f'%{query}%',))
        messages = cursor.fetchall()
        cursor.execute("SELECT host, COUNT(*) FROM messages WHERE sender LIKE ? GROUP BY host ORDER BY COUNT(*) DESC", (f'%{query}%',))
        chart_data = cursor.fetchall()
    elif search_by == 'date':
        cursor.execute("SELECT * FROM messages WHERE timestamp LIKE ? ORDER BY timestamp DESC", (f'%{query}%',))
        messages = cursor.fetchall()
        chart_data = []
    else:
        cursor.execute("SELECT * FROM messages WHERE message LIKE ? ORDER BY timestamp DESC", (f'%{query}%',))
        messages = cursor.fetchall()
        chart_data = []

    return render_template('index.html', messages=messages, chart_data=json.dumps(chart_data))

@app.route('/alerts', methods=['GET', 'POST'])
def alerts():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        action = request.form.get('action')
        keyword = request.form.get('keyword')

        if action == 'add' and keyword:
            cursor.execute('INSERT INTO alerts (keyword) VALUES (?)', (keyword,))
            conn.commit()
        elif action == 'delete' and keyword:
            cursor.execute('DELETE FROM alerts WHERE keyword = ?', (keyword,))
            conn.commit()

        return redirect(url_for('alerts'))

    cursor.execute('SELECT keyword FROM alerts')
    alerts = [row[0] for row in cursor.fetchall()]

    return render_template('alerts.html', alerts=alerts)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
