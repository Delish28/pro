from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import datetime
from plyer import notification
from apscheduler.schedulers.background import BackgroundScheduler
import requests
from bs4 import BeautifulSoup

# Initialize the Flask app
app = Flask(__name__)
app.secret_key = "medicine_secret_key"

# Database initialization
def init_db():
    conn = sqlite3.connect('medicine_reminder.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS reminders
                 (id INTEGER PRIMARY KEY, medicine_name TEXT, dosage TEXT, time TEXT, health_check TEXT)''')
    conn.commit()
    conn.close()

# Add reminder to the database
def add_reminder_to_db(medicine_name, dosage, reminder_time, health_check):
    conn = sqlite3.connect('medicine_reminder.db')
    c = conn.cursor()
    c.execute("INSERT INTO reminders (medicine_name, dosage, time, health_check) VALUES (?, ?, ?, ?)",
              (medicine_name, dosage, reminder_time, health_check))
    conn.commit()
    conn.close()

# Fetch medicine information from 1mg
def fetch_medicine_info(medicine_name):
    search_url = f"https://www.1mg.com/search/all?name={medicine_name.replace(' ', '-')}"
    
    try:
        response = requests.get(search_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            medicine_info = soup.find('div', class_='style__product-description___1vPQe')
            
            if medicine_info:
                return medicine_info.get_text()
            else:
                return "No information found for this medicine on 1mg."
        else:
            return "Error fetching data from 1mg."
    
    except Exception as e:
        return f"An error occurred: {str(e)}"

# Check reminders in the background
def check_reminders():
    conn = sqlite3.connect('medicine_reminder.db')
    c = conn.cursor()
    c.execute("SELECT * FROM reminders")
    reminders = c.fetchall()

    current_time = datetime.datetime.now().strftime('%H:%M')
    for reminder in reminders:
        if reminder[3] == current_time:
            notification.notify(
                title=f"Medicine Reminder: {reminder[1]}",
                message=f"Time to take {reminder[2]} of {reminder[1]}.",
                timeout=10
            )
    conn.close()

# Home route to render the web page
@app.route('/')
def index():
    return render_template('index.html')

# Route to handle adding reminders
@app.route('/add_reminder', methods=['POST'])
def add_reminder():
    medicine_name = request.form['medicine_name']
    dosage = request.form['dosage']
    reminder_time = request.form['reminder_time']
    health_check = request.form['health_check']

    add_reminder_to_db(medicine_name, dosage, reminder_time, health_check)
    flash('Reminder added successfully!')
    return redirect(url_for('index'))

# Route to fetch medicine info from 1mg
@app.route('/get_info', methods=['POST'])
def get_info():
    medicine_name = request.form['medicine_name']
    info = fetch_medicine_info(medicine_name)
    flash(info)
    return redirect(url_for('index'))

# Schedule background job to check reminders every minute
scheduler = BackgroundScheduler()
scheduler.add_job(func=check_reminders, trigger="interval", seconds=60)
scheduler.start()

# Run the Flask app
if __name__ == '__main__':
    init_db()
    try:
        app.run(debug=True)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
