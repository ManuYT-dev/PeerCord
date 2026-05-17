# PeerCord 🚀

PeerCord is a modern, serverless Peer-to-Peer (P2P) chat and file-sharing application built with Python. It features a sleek, Discord-inspired dark theme UI and uses WebRTC for direct, encrypted connections between users without the need for a central backend server.

## ✨ Features
* **Serverless P2P Architecture:** Direct connections using WebRTC (`aiortc`).
* **Modern UI:** A beautiful, frameless, Discord-style UI built with `PyQt6`.
* **File Sharing:** Send and receive files directly over WebRTC DataChannels.
* **Encrypted:** All WebRTC traffic is inherently encrypted.
* **Custom Window Controls:** Draggable frameless window with custom minimize, maximize, and close buttons.

---

## 📂 Project Structure
The project is organized to separate source code from compiled binaries:
* `src/Host/` - The server/host application that accepts incoming peer connections.
* `src/Client/` - The client application that initiates the connection.
* `src/General/` - Shared resources (constants, colors, and the file transfer protocol) used by both Host and Client.
* `bin/` - The destination folder where the compiled `.exe` files and shortcuts are saved.
* `compile.bat` - An automated batch script to compile the Python code into standalone Windows executables.

---

## 🛠️ Installation

### Prerequisites
* Python 3.8 or higher installed on your system.

### 1. Clone or Download the Repository
Ensure you have the folder structure set up correctly on your machine.

### 2. Install Dependencies
Open your terminal or command prompt and install the required Python libraries using pip:

```bash
pip install PyQt6 aiortc pyperclip
```
*Note: `pyperclip` is used to automatically copy the connection codes to your clipboard.*

---

## 📦 Compiling to Standalone Executables (.exe)
If you want to run PeerCord without using the terminal or installing Python on every machine, you can compile it into standalone Windows executables using Nuitka. We provide an automated batch script to make this seamless.

### 1. Install the Compiler
First, ensure you have Nuitka installed via pip:
```bash
pip install nuitka
```
*(Note: During the first run, Nuitka might ask to download a C-Compiler or Dependency Walker. Simply type `Yes` and press Enter when prompted in the terminal).*

### 2. Run the Build Script
1. Navigate to the root folder of the project.
2. Double-click the **`compile.bat`** file.
3. The script will automatically clean up old builds, compile both the Host and Client into optimized `.exe` files, and organize them into the `bin` folder. *This process may take 5–15 minutes depending on your CPU.*

### 3. Launching the Compiled App
Once finished, open the newly created `bin` folder. 
* Simply double-click the **`Start PeerCord Host`** or **`Start PeerCord Client`** shortcuts to launch the applications instantly!

---

## 🚀 How to Start from Source
If you prefer to run the raw Python code instead of compiling it, you will need at least two instances running to test the chat (one Host and one Client). 

**To start the Host:**
```bash
python src/Host/main.py
```

**To start a Client:**
```bash
python src/Client/main.py
```

---

## 🔗 How to Connect (The Handshake)

Because PeerCord does not use a central server to match users, you must manually exchange connection codes (WebRTC Offer and Answer) to establish the direct P2P link. 

Here is the step-by-step guide on how to connect a Client to a Host:

### Step 1: Client generates an Offer
1. Open the **Client** application.
2. Click the yellow button: **"⬡ Schritt 1: Verbindungsanfrage generieren (Offer)"**.
3. The Client generates a long code (a JSON string) and **automatically copies it to your clipboard**.
4. **Share this code** with the person running the Host app (e.g., via WhatsApp, Email, SMS, or another messenger).

### Step 2: Host accepts and generates an Answer
1. The **Host** receives the Offer code and copies it to their clipboard.
2. The Host clicks into the input field at the bottom of the Host app.
3. The Host clicks the purple button: **"＋ Neuen User verbinden — Offer aus Zwischenablage"**.
4. The Host app processes the Offer, generates an Answer code, and **automatically copies the Answer to the Host's clipboard**.
5. The Host **shares this new Answer code** back to the Client.

### Step 3: Client applies the Answer
1. The **Client** receives the Answer code and copies it to their clipboard.
2. The Client clicks the new yellow button: **"⬡ Schritt 2: Answer vom Host aus Zwischenablage einfügen"**.
3. **Boom! 💥 You are connected!** The chat input will unlock, and you can now send text messages and files directly to each other.

---

## 📎 Sharing Files
Once connected, you can share files by clicking the **Paperclip (📎)** icon next to the chat input. 
* Files are sent in chunks directly over the P2P connection.
* Received files will appear in the chat history as a card with a "Download" button.

---

## ⚠️ Troubleshooting
* **Invalid Code Error:** Make sure you are copying the *entire* JSON string when sharing codes. Missing a single bracket `{}` will break the connection.
* **Cannot Connect Over Internet:** PeerCord uses public Google STUN servers to bypass basic routers. However, if you or your partner are behind a strict corporate firewall or symmetric NAT, a TURN server might be required (which is not configured by default).
