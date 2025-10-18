from flask import Flask, request, render_template, send_from_directory, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os
import subprocess
import uuid

# Config
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
ALLOWED_IMAGE_EXT = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_AUDIO_EXT = {'mp3', 'wav', 'm4a'}
MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200 MB max upload

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.secret_key = os.environ.get('FLASK_SECRET', 'cambia_questa_chiave_se_pubblica')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    image = request.files.get('image')
    audio = request.files.get('audio')

    if not image or not audio:
        flash('Devi caricare sia immagine che audio')
        return redirect(url_for('index'))

    if not allowed_file(image.filename, ALLOWED_IMAGE_EXT):
        flash('Formato immagine non supportato')
        return redirect(url_for('index'))

    if not allowed_file(audio.filename, ALLOWED_AUDIO_EXT):
        flash('Formato audio non supportato')
        return redirect(url_for('index'))

    # Salva con nomi unici
    uid = uuid.uuid4().hex
    image_name = secure_filename(f"{uid}_image.{image.filename.rsplit('.',1)[1]}")
    audio_name = secure_filename(f"{uid}_audio.{audio.filename.rsplit('.',1)[1]}")

    image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_name)
    audio_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_name)

    image.save(image_path)
    audio.save(audio_path)

    # Output file
    output_name = f"{uid}_output.mp4"
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_name)

    # Comando FFmpeg
    ffmpeg_cmd = [
        'ffmpeg',
        '-y',
        '-loop', '1',
        '-i', image_path,
        '-i', audio_path,
        '-c:v', 'libx264',
        '-tune', 'stillimage',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-pix_fmt', 'yuv420p',
        '-shortest',
        '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2',
        output_path
    ]

    try:
        subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError as e:
        err = e.stderr.decode('utf-8', errors='ignore')
        flash('Errore nella conversione con FFmpeg. Guarda i log del server.')
        logname = f"{uid}_ffmpeg_error.log"
        with open(os.path.join(app.config['UPLOAD_FOLDER'], logname), 'w', encoding='utf-8') as f:
            f.write(err)
        return redirect(url_for('index'))

    return redirect(url_for('download_file', filename=output_name))

@app.route('/uploads/<path:filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
