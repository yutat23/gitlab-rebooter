from flask import Flask, render_template, request, redirect, url_for, session
from flask_httpauth import HTTPBasicAuth
from flask_apscheduler import APScheduler
import subprocess
import datetime
import uuid


app = Flask(__name__, static_folder='./templates/images')
app.secret_key = b"7ab56c834c5d4d53b9dfa68ec184a933"
auth = HTTPBasicAuth()
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

users = {
  "test": "test"
}

@auth.verify_password
def verify_password(username, password):
  if username in users and users[username] == password:
    return username

def execute_command():
  command = "sudo gitlab-ctl restart"
  try:
    output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
    print(output.decode('utf-8'))
  except subprocess.CalledProcessError as e:
    print(e.output.decode('utf-8'))

@app.route('/')
@auth.login_required
def index():
  output = session.pop('output', None)  # セッションから出力を取得し、その後削除
  # ジョブ実行時間リストを作成
  jobs = []
  for job in sorted(scheduler.get_jobs(), key=lambda x: x.next_run_time):
    jobs.append({
      'id': job.id,
      'next_run_time': job.next_run_time.strftime('%Y-%m-%d %H:%M')
    })

  return render_template('index.html', output=output, jobs=jobs)

@app.route('/run_command', methods=['POST'])
@auth.login_required
def run_command():
  execution_type = request.form['execution_type']
  if execution_type == 'immediate':
    execute_command()
    session['output'] = "Command executed immediately."  # 出力をセッションに保存
  elif execution_type == 'scheduled':
    execution_time = request.form['execution_time']
    execution_datetime = datetime.datetime.strptime(execution_time, '%Y-%m-%dT%H:%M')
    job_id = str(uuid.uuid4())  # 一意のIDを生成
    scheduler.add_job(func=execute_command, trigger='date', next_run_time=execution_datetime, id=job_id)
    session['output'] = f"Command scheduled for {execution_time}."  # 出力をセッションに保存
  else:
    session['output'] = "Invalid execution type."  # 出力をセッションに保存
  return redirect(url_for('index'))  # インデックスページにリダイレクト

@app.route('/cancel_command', methods=['POST'])
@auth.login_required
def cancel_command():
  job_id = request.form['job_id']
  scheduler.remove_job(job_id)
  session['output'] = f"Job canceled."  # 出力をセッションに保存
  return redirect(url_for('index'))  # インデックスページにリダイレクト

if __name__ == '__main__':
  app.run(host="0.0.0.0", debug=False)
