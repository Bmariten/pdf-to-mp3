from flask import Flask, render_template, request, send_file, redirect, url_for, flash
import os
import pdfplumber
from fpdf import FPDF
import edge_tts
import asyncio

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
AUDIO_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "audio")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)

# Voice mapping for different languages (female voices)
VOICE_MAPPING = {
    'english': 'en-US-JennyNeural',
    'hindi': 'hi-IN-SwaraNeural',
    'french': 'fr-FR-DeniseNeural',
    'swahili': 'sw-KE-ZuriNeural',
    'zulu': 'zu-ZA-ThandoNeural',
    'igbo': 'ig-NG-EzinneNeural',
    'yoruba': 'yo-NG-AyoNeural'
}

def extract_text_from_pdf_with_headers(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                lines = page.extract_text().splitlines()
                for line in lines:
                    if len(line.strip()) > 0 and len(line.strip()) <= 60:
                        text += f"{line.strip()}\n"
                    else:
                        text += f"{line.strip()} "
        return text.strip()
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""

def save_text_to_pdf(text, output_pdf_path):
    try:
        sanitized_text = text.encode('latin-1', 'replace').decode('latin-1')
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        lines = sanitized_text.splitlines()
        for line in lines:
            pdf.cell(200, 10, txt=line, ln=True, align='L')
        pdf.output(output_pdf_path)
    except Exception as e:
        print(f"Error saving text to PDF: {e}")
        raise

async def generate_audio_with_edge_tts(text, language):
    try:
        voice = VOICE_MAPPING.get(language, 'en-US-JennyNeural')
        audio_filename = f"{language}_audio_{os.urandom(4).hex()}.mp3"
        audio_file = os.path.join(AUDIO_FOLDER, audio_filename)
        
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(audio_file)
        
        if os.path.exists(audio_file) and os.path.getsize(audio_file) > 0:
            return audio_filename
        else:
            raise Exception("Audio file was not generated properly")
    except Exception as e:
        print(f"Error generating audio: {e}")
        raise

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            flash("No file part")
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash("No selected file")
            return redirect(request.url)
        
        language = request.form.get('language', 'english')
        
        if file:
            pdf_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(pdf_path)

            extracted_text = extract_text_from_pdf_with_headers(pdf_path)
            if not extracted_text:
                flash("No text extracted from the PDF!")
                return redirect(request.url)

            output_pdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extracted_text.pdf")
            save_text_to_pdf(extracted_text, output_pdf_path)

            try:
                audio_filename = asyncio.run(generate_audio_with_edge_tts(extracted_text, language))
                
                audio_path = os.path.join(AUDIO_FOLDER, audio_filename)
                if not os.path.exists(audio_path):
                    raise Exception("Audio file not found after generation")
                
                return send_file(
                    audio_path,
                    as_attachment=True,
                    download_name=audio_filename,
                    mimetype='audio/mp3'
                )
            except Exception as e:
                flash(f"Error generating audio: {str(e)}")
                return redirect(request.url)
                
    except Exception as e:
        flash(f"An error occurred: {str(e)}")
        return redirect(request.url)

if __name__ == '__main__':
    app.run(debug=True)