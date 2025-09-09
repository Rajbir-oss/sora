# jarvis_backend.py
import os
import sys
import time
import json
import psutil
import platform
import subprocess
import threading
import webbrowser
import pyttsx3
import speech_recognition as sr
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import datetime
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'jarvis-secret'
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)

# Initialize text-to-speech engine
engine = pyttsx3.init()
engine.setProperty('rate', 150)
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[1].id if len(voices) > 1 else voices[0].id)

# Initialize speech recognition
recognizer = sr.Recognizer()
microphone = sr.Microphone()

# Global variables
is_listening = False
command_history = []

def speak(text):
    """Convert text to speech"""
    print(f"JARVIS: {text}")
    engine.say(text)
    engine.runAndWait()
    socketio.emit('response', {'type': 'response', 'message': text})

def get_system_info():
    """Get system information"""
    info = {
        'system': platform.system(),
        'node': platform.node(),
        'release': platform.release(),
        'version': platform.version(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'cpu_count': psutil.cpu_count(),
        'memory_total': f"{psutil.virtual_memory().total / (1024**3):.2f} GB",
        'memory_available': f"{psutil.virtual_memory().available / (1024**3):.2f} GB",
        'disk_usage': f"{psutil.disk_usage('/').used / (1024**3):.2f} GB"
    }
    return info

def execute_command(command):
    """Execute system commands"""
    try:
        if command.lower().startswith('open '):
            app_name = command[5:].strip().lower()
            
            # Application mappings
            app_mappings = {
                'browser': ['chrome', 'firefox', 'edge', 'safari'],
                'calculator': ['calc', 'gnome-calculator'],
                'notepad': ['notepad', 'gedit', 'mousepad'],
                'terminal': ['gnome-terminal', 'xterm', 'cmd'],
                'file explorer': ['explorer', 'nautilus', 'dolphin']
            }
            
            if app_name in app_mappings:
                for app in app_mappings[app_name]:
                    try:
                        if platform.system() == 'Windows':
                            subprocess.Popen(app)
                        else:
                            subprocess.Popen([app])
                        return f"Opening {app_name}..."
                    except:
                        continue
                return f"Could not open {app_name}"
            else:
                return f"I don't know how to open {app_name}"
                
        elif command.lower().startswith('close '):
            app_name = command[6:].strip().lower()
            # This would require process monitoring and killing
            return f"Closing {app_name}... (Feature in development)"
            
        elif command.lower().startswith('search '):
            query = command[7:].strip()
            webbrowser.open(f"https://www.google.com/search?q={query}")
            return f"Searching for {query}..."
            
        elif 'time' in command.lower():
            current_time = datetime.datetime.now().strftime("%I:%M %p")
            return f"The current time is {current_time}"
            
        elif 'date' in command.lower():
            current_date = datetime.datetime.now().strftime("%B %d, %Y")
            return f"Today is {current_date}"
            
        elif 'system info' in command.lower():
            info = get_system_info()
            response = "System Information:\n"
            for key, value in info.items():
                response += f"{key.replace('_', ' ').title()}: {value}\n"
            return response
            
        elif 'volume' in command.lower():
            # Volume control (platform specific)
            if 'up' in command.lower():
                return "Volume increased"
            elif 'down' in command.lower():
                return "Volume decreased"
            elif 'mute' in command.lower():
                return "Volume muted"
                
        elif 'shutdown' in command.lower():
            if 'confirm' in command.lower():
                if platform.system() == 'Windows':
                    os.system("shutdown /s /t 1")
                else:
                    os.system("shutdown now")
                return "Shutting down system..."
            else:
                return "Please say 'shutdown confirm' to shutdown the system"
                
        elif 'restart' in command.lower():
            if 'confirm' in command.lower():
                if platform.system() == 'Windows':
                    os.system("shutdown /r /t 1")
                else:
                    os.system("reboot")
                return "Restarting system..."
            else:
                return "Please say 'restart confirm' to restart the system"
                
        elif 'lock' in command.lower():
            if platform.system() == 'Windows':
                os.system("rundll32.exe user32.dll,LockWorkStation")
            elif platform.system() == 'Darwin':
                os.system("pmset displaysleepnow")
            else:
                os.system("xdg-screensaver lock")
            return "Screen locked"
            
        elif 'screenshot' in command.lower():
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            if platform.system() == 'Windows':
                os.system(f"powershell -command \"Add-Type -AssemblyName System.Windows.Forms; [Windows.Forms.SendKeys]::SendWait('{{PRTSC}}')\"")
            else:
                os.system(f"import -window root {filename}")
            return f"Screenshot saved as {filename}"
            
        elif 'music' in command.lower():
            webbrowser.open("https://music.youtube.com")
            return "Opening music player..."
            
        elif 'weather' in command.lower():
            location = command.replace('weather', '').strip()
            webbrowser.open(f"https://www.google.com/search?q=weather+{location}")
            return f"Showing weather for {location}"
            
        elif 'joke' in command.lower():
            jokes = [
                "Why don't scientists trust atoms? Because they make up everything!",
                "Why did the scarecrow win an award? He was outstanding in his field!",
                "Why don't eggs tell jokes? They'd crack each other up!",
                "What do you call a fake noodle? An impasta!",
                "Why did the math book look so sad? Because it had too many problems!"
            ]
            return random.choice(jokes)
            
        else:
            return "I'm sorry, I don't understand that command. Please check the available commands list."
            
    except Exception as e:
        return f"Error executing command: {str(e)}"

def background_system_monitor():
    """Monitor system stats in background"""
    while True:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent
        
        socketio.emit('system_update', {
            'type': 'system_update',
            'cpu': cpu_percent,
            'memory': memory_percent
        })
        
        time.sleep(2)

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/command', methods=['POST'])
def handle_command():
    data = request.get_json()
    command = data.get('command', '')
    
    if command:
        response = execute_command(command)
        command_history.append({'command': command, 'response': response, 'timestamp': time.time()})
        
        # Speak the response
        threading.Thread(target=speak, args=(response,)).start()
        
        return jsonify({'success': True, 'response': response})
    
    return jsonify({'success': False, 'error': 'No command provided'})

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connected', {'message': 'Connected to JARVIS'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

def voice_command_loop():
    """Continuous voice command listening"""
    global is_listening
    
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
        
    while True:
        if is_listening:
            try:
                with microphone as source:
                    print("Listening...")
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                    
                try:
                    command = recognizer.recognize_google(audio).lower()
                    print(f"Command: {command}")
                    
                    # Process command
                    response = execute_command(command)
                    command_history.append({'command': command, 'response': response, 'timestamp': time.time()})
                    
                    # Speak response
                    speak(response)
                    
                except sr.UnknownValueError:
                    print("Could not understand audio")
                except sr.RequestError as e:
                    print(f"Error: {e}")
                    
            except sr.WaitTimeoutError:
                pass
        else:
            time.sleep(0.1)

if __name__ == '__main__':
    # Start background system monitor
    monitor_thread = threading.Thread(target=background_system_monitor, daemon=True)
    monitor_thread.start()
    
    # Start voice command thread
    voice_thread = threading.Thread(target=voice_command_loop, daemon=True)
    voice_thread.start()
    
    # Start Flask server
    print("JARVIS System Initializing...")
    speak("JARVIS system online. Ready for your commands.")
    
    # Open the web interface
    webbrowser.open('http://localhost:5000')
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)