# Multi-Client Online Quiz System with Real-Time Ranking

A comprehensive online quiz platform that supports multiple concurrent clients, featuring secure authentication, real-time scoring, and live rankings. Built using socket programming with SSL/TLS encryption for secure communication over TCP/IP networks.

## Table of Contents
- [Features](#features)
- [Project Structure](#project-structure)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Architecture](#architecture)
- [Quiz Topics](#quiz-topics)
- [How It Works](#how-it-works)
- [Code Snippets](#code-snippets)
- [User Interface Flow with Screenshots](#user-interface-flow-with-screenshots)
- [Performance Characteristics](#performance-characteristics)
- [Troubleshooting](#troubleshooting)

## Features

✨ **Core Features:**
- 🔐 **Secure Authentication** - User registration and login with CSV-based credential management
- 🔒 **SSL/TLS Encryption** - Secure socket communication between clients and server
- 👥 **Multi-Client Support** - Concurrent socket handling for multiple simultaneous users
- 🎯 **Multiple Quiz Topics** - 5+ subjects with varying difficulty levels
- ⏱️ **Timed Quizzes** - Configurable quiz duration with timer management
- 🏆 **Real-Time Ranking** - Live leaderboard showing top performers
- 📊 **User Statistics** - Score tracking and performance analytics
- 🎨 **Modern GUI** - Dark-themed Tkinter interface for both server and client
- 📝 **Question Bank** - Comprehensive CSV-based question database
- 🔄 **Persistent Data** - User stats and results stored in CSV format

## Project Structure

```
├── certs/                          # SSL/TLS certificates directory
│   ├── server.crt                  # Server certificate
│   └── server.key                  # Server private key
├── screenshots/                    # Screenshots directory
├── c_questions.csv                 # C Programming questions
├── client_gui.py                   # Client GUI for quiz interface
├── client_network.py               # Network communication layer (SSL/TLS)
├── epd_questions.csv               # EPD questions
├── generate_cert.py                # SSL certificate generation utility
├── maths_questions.csv             # Mathematics questions
├── mental_ability_questions.csv    # Mental Ability questions
├── python_questions.csv            # Python questions
├── quiz.py                         # Core quiz logic and MCQ class
├── README.md                       # This file
├── server_gui.py                   # Server GUI and connection handling
├── user_stats.csv                  # User performance statistics
└── users.txt                       # User credentials (username, password)
```

## System Requirements

### Minimum Requirements
- **Operating System:** Windows 10/11, macOS 10.14+, or Linux (Ubuntu 18.04+)
- **Python Version:** Python 3.7 or higher
- **RAM:** 512 MB minimum, 1 GB recommended
- **Storage:** 50 MB free space
- **Network:** Active internet connection for SSL certificate validation

### Python Dependencies
All dependencies are part of Python's standard library (no external packages required):
- `tkinter` - GUI framework (included with Python)
- `socket` - Network socket programming
- `ssl` - SSL/TLS encryption support
- `json` - JSON data handling
- `csv` - CSV file processing
- `threading` - Multi-threading support
- `struct` - Binary data handling
- `os` - Operating system interface
- `sys` - System-specific parameters
- `time` - Time functions

### Hardware Requirements
- **Processor:** 1 GHz or faster processor
- **Display:** 1024x768 resolution or higher
- **Network Interface:** Ethernet or Wi-Fi adapter

### Software Prerequisites
- Python 3.7+ installed and added to PATH
- OpenSSL (usually pre-installed on most systems)
- Firewall configured to allow port 5000 (or custom port)

**Note:** No additional software installation required beyond Python itself.

## Installation

### Step 1: Clone/Download the Project
```bash
cd CN-Mini-Project
```

### Step 2: Generate SSL Certificates
If certificates don't exist, run the certificate generation utility:
```bash
python generate_cert.py
```

This creates:
- `certs/server.crt` - Server certificate
- `certs/server.key` - Server private key

### Step 3: Verify Project Structure
Ensure all question CSV files and Python scripts are in the project root directory.

## Usage

### Starting the Server

Run the server GUI application:
```bash
python server_gui.py
```

**Server Interface:**
- Displays active connections
- Shows real-time quiz statistics
- Displays live leaderboard with rankings
- Logs all client activities and scores
- Configure quiz settings (duration, number of questions, topic, difficulty)

### Connecting Clients

In a separate terminal/machine, run:
```bash
python client_gui.py
```

**Client Interface:**
- User registration and login
- Select quiz topic and difficulty
- Answer multiple-choice questions
- View real-time timer
- Submit quiz and view results
- See ranking/leaderboard

### Default Configuration

```python
HOST = "0.0.0.0"          # Server listens on all interfaces
PORT = 5000               # Server port
QUIZ_DURATION = 60        # Quiz time limit (seconds)
NUM_QUESTIONS = 5         # Questions per quiz
```

**To change settings:** Edit the constants in `server_gui.py` and `client_gui.py`

## Architecture

### System Design

```
┌─────────────────────────────────────────────────────┐
│                   SERVER SIDE                       │
│  ┌──────────────────────────────────┐               │
│  │  Quiz Question Database (CSV)    │               │
│  │  • C Programming                 │               │
│  │  • Python                        │               │
│  │  • Mathematics                   │               │
│  │  • Mental Ability                │               │
│  │  • EPD                           │               │
│  └──────────────────────────────────┘               │
│           ↓                                         │
│  ┌──────────────────────────────────┐               │
│  │  Quiz Server Engine              │               │
│  │  • Session Management            │               │
│  │  • Real-Time Scoring             │               │
│  │  • Leaderboard Management        │               │
│  └──────────────────────────────────┘               │
│           ↓                                         │
│  ┌──────────────────────────────────┐               │
│  │  SSL/TLS Socket Layer (Port 5000)│               │
│  │  • Accept Connections            │               │
│  │  • Encrypted Communication       │               │
│  │  • Multi-client Handling         │               │
│  └──────────────────────────────────┘               │
└─────────────────────────────────────────────────────┘
          ↕ Secure TCP/IP ↕
┌─────────────────────────────────────────────────────┐
│              CLIENT SIDE (Multiple)                 │
│  ┌──────────────────────────────────┐               │
│  │  User Interface (Tkinter GUI)    │               │
│  │  • Login/Signup                  │               │
│  │  • Quiz Selection                │               │
│  │  • Question Display              │               │
│  │  • Timer & Progress              │               │
│  │  • Results & Ranking             │               │
│  └──────────────────────────────────┘               │
│           ↓                                         │
│  ┌──────────────────────────────────┐               │
│  │  SSL/TLS Socket Connection       │               │
│  │  • Secure Authentication         │               │
│  │  • Question Requests             │               │
│  │  • Answer Submission             │               │
│  │  • Score Retrieval               │               │
│  └──────────────────────────────────┘               │
└─────────────────────────────────────────────────────┘
```

### Communication Protocol

All client-server communication uses:
- **Protocol:** TCP/IP over SSL/TLS
- **Message Format:** JSON with 4-byte length prefix
- **Structure:** Length header + JSON payload

**Message Types:**
1. `login` - User authentication
2. `signup` - New user registration
3. `get_quiz` - Request quiz questions
4. `submit_answer` - Submit user answer
5. `end_quiz` - Complete quiz session
6. `get_ranking` - Retrieve leaderboard

## Quiz Topics

The system includes 5 different quiz topics:

| Topic | File | Difficulty Levels | Description |
|-------|------|-------------------|-------------|
| **C Programming** | c_questions.csv | Easy, Medium, Hard | C language fundamentals and advanced concepts |
| **Python** | python_questions.csv | Easy, Medium, Hard | Python syntax, OOP, and libraries |
| **Mathematics** | maths_questions.csv | Easy, Medium, Hard | Algebra, Geometry, Calculus, and Integration |
| **Mental Ability** | mental_ability_questions.csv | Easy, Medium, Hard | Logical reasoning and problem-solving |
| **EPD** | epd_questions.csv | Easy, Medium, Hard | Electronic & Power Devices engineering |

Each question contains:
- Question ID
- Topic classification
- Difficulty level
- Question text (4 options: A, B, C, D)
- Correct answer

## Data Management

### User Credentials (`users.txt`)
```
username,password
user1,pass123
user2,pass456
```

### User Statistics (`user_stats.csv`)
```
username,total_correct,total_incorrect,total_skipped
user1,15,5,3
user2,20,2,1
```

## How It Works

### Quiz Session Flow

1. **Client Connection**
   - Client initiates SSL/TLS connection to server
   - Server accepts and authenticates connection

2. **User Authentication**
   - New users register with username/password
   - Returning users login with credentials
   - Credentials validated against `users.txt`

3. **Quiz Selection**
   - User selects topic (C, Python, Math, Mental Ability, EPD)
   - User selects difficulty (Easy, Medium, Hard)
   - User can choose number of questions

4. **Quiz Execution**
   - Server sends question set to client
   - Client displays questions with timer
   - User selects answers and submits
   - Server verifies answers and calculates score

5. **Real-Time Ranking**
   - Server maintains live leaderboard
   - Scores updated immediately upon quiz completion
   - All clients see current top performers
   - Rankings persist in user statistics

6. **Results & Analytics**
   - User receives final score and accuracy percentage
   - Statistics saved to `user_stats.csv`
   - User can view personal performance history
   - Server displays aggregate statistics

## Key Implementation Details

- **Socket Programming**: Raw socket creation, binding, listening, accepting, and connection management
- **Concurrent Connections**: Multi-threaded server handles multiple clients simultaneously
- **SSL/TLS Encryption**: Standard library `ssl` module with certificate-based authentication
- **JSON Protocol**: Structured message exchange with length-prefixed encoding
- **CSV Database**: Lightweight question and statistics storage
- **Tkinter GUI**: Cross-platform graphical interface for user interaction
- **Real-time Updates**: Live score tracking and instant leaderboard updates

## Network Configuration

To run on different machines:

1. **Server:**
   - Update `HOST` in `server_gui.py` to server's IP address
   - Keep `PORT = 5000` or change as needed

2. **Client:**
   - Update `SERVER_IP` in `client_network.py` to server's IP address
   - Update `PORT` to match server port

Example for LAN:
```python
# In server_gui.py
HOST = "192.168.1.100"  # Server's actual IP

# In client_network.py  
SERVER_IP = "192.168.1.100"  # Same as server
PORT = 5000
```

## Code Snippets

### 1. MCQ Class and Quiz Logic (`quiz.py`)

The core quiz data structure manages individual questions:

```python
class MCQ:
    def __init__(self, id, topic, difficulty, question, option_a, option_b, option_c, option_d, correct_option):
        self.id = id
        self.topic = topic
        self.difficulty = difficulty
        self.question = question
        self.option_a = option_a
        self.option_b = option_b
        self.option_c = option_c
        self.option_d = option_d
        self.correct_option = correct_option.upper()
        self.user_option = ' '
        self.is_correct = 0
```

### 2. QuizClient SSL/TLS Connection (`client_network.py`)

Secure socket initialization with certificate verification:

```python
class QuizClient:
    def __init__(self):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_verify_locations("certs/server.crt")
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn = context.wrap_socket(sock, server_hostname=SERVER_IP)
        self.conn.connect((SERVER_IP, PORT))
```

### 3. Secure JSON Message Protocol

Length-prefixed JSON encoding for reliable message transmission:

```python
def send_json(sock, data):
    message = json.dumps(data).encode()
    length = struct.pack("!I", len(message))
    sock.sendall(length + message)

def recv_json(sock):
    raw_length = sock.recv(4)
    if not raw_length:
        return None
    length = struct.unpack("!I", raw_length)[0]
    data = b""
    while len(data) < length:
        packet = sock.recv(length - len(data))
        if not packet:
            return None
        data += packet
    return json.loads(data.decode())
```

### 4. User Authentication (`server_gui.py`)

Credential validation against user database:

```python
def authenticate(username, password):
    try:
        with open("users.txt", "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2 and row[0] == username and row[1] == password:
                    return True
    except FileNotFoundError:
        pass
    return False

def register_user(username, password):
    USERS_FILE = "users.txt"
    if not os.path.exists(USERS_FILE):
        open(USERS_FILE, "w").close()
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            stored = line.split(",", 1)[0].strip()
            if stored == username:
                return "exists"
    with open(USERS_FILE, "a", encoding="utf-8") as f:
        f.write(f"{username},{password}\n")
```

### 5. Login API Call

Client-side login request:

```python
def login(self, username, password):
    req = {
        "type": "login",
        "username": username,
        "password": password
    }
    send_json(self.conn, req)
    res = recv_json(self.conn)
    return res["status"] == "success"
```

### 6. Quiz Request and Answer Submission

```python
def get_quiz(self, topic, difficulty):
    req = {
        "type": "get_quiz",
        "topic": topic,
        "difficulty": difficulty
    }
    send_json(self.conn, req)
    # Server responds with list of MCQ objects
```

---

## User Interface Flow with Screenshots

### Screenshot 1: Server Startup Page
![Server Startup](screenshots/01_server_startup.png)

**Description:** Server GUI displaying:
- Active connection count
- Server status (Online/Offline)
- Port information (5000)
- Multiplayer-Quiz configuration options (topic, difficulty, duration)
- Start/Stop Quiz button
- Lobby players list
- All-time Leaderboard

---

### Screenshot 2: Client Home Page
![Client Home](screenshots/02_client_home.png)

**Description:** Initial client application interface displaying:
- Application title: "Multi-Client Online Quiz System"
- Welcome message and brief description
- **Login button** - For existing users
- **Sign Up button** - For new user registration
- Exit button

---

### Screenshot 3: Client Sign Up Page
![Client Signup](screenshots/03_client_signup.png)

**Description:** Client signup interface with:
- Username input field
- Password input field
- Confirm password field
- Sign up button
- Link to login page
- Validation messages

---

### Screenshot 4: Client Login Page
![Client Login](screenshots/04_client_login.png)

**Description:** Client login interface with:
- Username input field
- Password input field
- Login button
- Option to create new account
- Authentication status message

---

### Screenshot 5: Client Home Page After Login
![Client Home After Login](screenshots/05_client_home_logged_in.png)

**Description:** Post-login dashboard interface displaying:
- Welcome message with username
- User profile information and statistics
- **Single Player Quiz button** - Start individual quiz
- **Multiplayer Quiz button** - Join multiplayer session
- **View Cumulative Performance button** - Check overall stats
- **View Leaderboard button** - Check rankings
- **Logout button** - Sign out of account

---

### Screenshot 6: Quiz Topic Selection
![Quiz Topic Selection](screenshots/06_topic_selection.png)

**Description:** Topic selection interface showing:
- 5 available topics:
  - C Programming
  - Python
  - Mathematics
  - Mental Ability
  - EPD
- Difficulty level selector (Easy, Medium, Hard)
- Number of questions dropdown
- Start Quiz button

---

### Screenshot 7: Quiz Question Display Page
![Quiz Questions](screenshots/07_quiz_questions.png)

**Description:** Active quiz interface displaying:
- Question number (e.g., "Question 1 of 5")
- Question text
- 4 multiple-choice options (A, B, C, D)
- Option selection buttons
- **Real-time timer** showing remaining time
- Question navigation buttons (Previous, Next)
- Skip question option
- Submit quiz button
- Question Panel showing status of questions (e.g., marked for review, not visited, answered, etc.)

---

### Screenshot 8: Quiz Results Page
![Quiz Results](screenshots/08_results.png)

**Description:** Results summary page showing:
- Final score (e.g., "Score: 4/5")
- Accuracy percentage (e.g., "80%")
- Correct answers count
- Incorrect answers count
- Skipped questions count

---

### Screenshot 9: Answer Review Page
![Answer Review](screenshots/09_answer_review.png)

**Description:** Detailed answer review interface displaying:
- Question-by-question breakdown
- User's selected answer vs correct answer
- Question difficulty indicator
- Navigation between questions
- Correct/incorrect status indicators

---

### Screenshot 10: Cumulative Performance Page
![Cumulative Performance](screenshots/10_cumulative_performance.png)

**Description:** Comprehensive performance analytics dashboard showing:
- Overall statistics across all quizzes taken
- Average scores and accuracy percentages
- Overall percentage, accuracy including all the quizes given till that point
- No. of correct, incoorect and skipped questions stat
- Rank among all the users
- **Back to Home button**

---

### Screenshot 11: Real-Time Leaderboard/Rankings
![Leaderboard](screenshots/11_leaderboard.png)

**Description:** Live ranking interface displaying:
- Top performers leaderboard
- Rank column (Position 1, 2, 3, etc.)
- Username column
- Score column
- Refresh button
- Return to home button

---

### Screenshot 12: Multiplayer Quiz - Client Waiting Lobby
![Multiplayer Waiting Lobby](screenshots/12_multiplayer_waiting.png)

**Description:** Multiplayer lobby interface after player joins showing:
- "Successfully joined lobby!" confirmation message
- "Waiting for host to start the quiz..." message
- **Back button** to exit the lobby

---

### Screenshot 13: Multiplayer Quiz - Client In Lobby
![Multiplayer In Lobby](screenshots/13_multiplayer_lobby.png)

**Description:** Pre-quiz countdown interface displaying:
- "Quiz starting in..." countdown timer (e.g., "5... 4... 3... 2... 1...")
- **Back button**
- Animated countdown display

---

### Screenshot 14: Server Side During Multiplayer Quiz
![Server Multiplayer Quiz](screenshots/14_server_multiplayer.png)

**Description:** Server interface during multiplayer quiz session:
- Active multiplayer session indicator
- Selection of topic, difficulty, number of questions and duration of the quiz
- List of all participating players in the lobby
- Real-time progress tracking for each player
- Player completion status
- Live score updates as quiz submitted
- Emergency stop/cancel options

---

### Screenshot 15: Multiplayer Quiz Results
![Multiplayer Results](screenshots/15_multiplayer_results.png)

**Description:** Multiplayer quiz results interface displaying:
- Individual player rankings (1st, 2nd, 3rd, 4th place)
- Player names with final scores
- Accuracy percentages for each player
- Winner announcement and congratulations
- **Return to Home button**
- Session statistics (total questions correct, incorrect, skipped, etc.)

---

### Screenshot 16: Server Monitoring Dashboard
![Server Dashboard](screenshots/16_server_dashboard.png)

**Description:** Server admin interface showing:
- Active connections count
- Total users registered
- Current quizzes in progress
- Real-time activity log:
  - User login/logout events
  - Quiz start/completion notifications
  - Score updates with timestamps
- Top scores section
- Server statistics (uptime, total quizzes taken)
- Configuration panel

---

## Performance Characteristics

- **Concurrent Clients:** Supports 50+ simultaneous connections (limited by system resources)
- **Quiz Latency:** <100ms average response time
- **Data Throughput:** Minimal bandwidth usage (~1KB per quiz submission)
- **Scalability:** Easily handles 100+ registered users

## Troubleshooting

| Issue | Solution |
|-------|----------|
| SSL Certificate Error | Run `python generate_cert.py` to generate certificates |
| Connection Refused | Ensure server is running and firewall allows port 5000 |
| Module Not Found | Verify all Python files are in the same directory |
| Question File Error | Check CSV files are in project root with correct names |
| SSL Certificate Expired | Regenerate certificates using `generate_cert.py` |
| Port Already in Use | Change PORT constant in `server_gui.py` and `client_network.py` |
| Login Failed | Verify username/password are registered and match exactly |

---

**Developed as a Computer Networks Mini Project with focus on socket programming, SSL/TLS encryption, concurrent client handling, and real-time distributed systems design.**
