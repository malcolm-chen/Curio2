# ChatCompletion Version of Curio2

A conversational AI system built with Flask backend and Vue.js frontend, designed for interactive storytelling and educational content generation.


## System Architecture

```
ChatCompletion System/
├── backend/           # Flask API server
│   ├── app.py        # Main Flask application
│   ├── knowledge/    # Knowledge graph data
│   ├── prompts/      # AI prompt templates
│   └── requirements.txt
├── frontend/         # Vue.js web application
│   ├── src/         # Source code
│   ├── public/      # Static assets
│   └── package.json
└── README.md
```

## Prerequisites

- **Python 3.8+** with pip
- **Node.js 16+** with npm/yarn
- **OpenAI API Key** (for AI functionality)

## Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/malcolm-chen/Curio2.git
cd Curio2
```

### 2. Backend Setup

Navigate to the backend directory and set up the Python environment:

#### Option A: Using Python venv (recommended)

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### Option B: Using Anaconda/Conda

```bash
cd backend

# Create conda environment
conda create -n curio2 python=3.8

# Activate conda environment
conda activate curio2

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file in the `backend/` directory:

```bash
# backend/.env
OPENAI_API_KEY=your_openai_api_key_here
VUE_APP_URL=http://localhost:5173
```
Then, create a `.env` file in the `frontend/` directory:

```bash
# frontend/.env
VITE_VUE_APP_URL=http://localhost:5000
VITE_OPENAI_API_KEY=your_openai_api_key_here
```

**Important**: Replace `your_openai_api_key_here` with your actual OpenAI API key.

### 4. Frontend Setup

Navigate to the frontend directory and install dependencies:

```bash
cd ../frontend

# Install dependencies
npm install
# or
yarn install
```

## Running the System

### Start the Backend Server

From the `backend/` directory:

```bash
# Make sure your virtual environment is activated
# For venv:
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows

# For conda:
conda activate curio2

# Start the server
python app.py
```

The backend server will start on `http://localhost:5000`

### Start the Frontend Development Server

From the `frontend/` directory:

```bash
npm run dev
# or
yarn dev
```

The frontend will be available at `http://localhost:5173`

## Usage

1. **Open your browser** and navigate to `http://localhost:5173`
2. **Start a conversation** by typing a message in the chat interface

## API Endpoints

The backend provides the following main endpoints:

- `POST /api/chat` - Send messages and receive AI responses
- `POST /api/evaluate` - Evaluate conversation quality
- `GET /api/health` - Health check endpoint

## Configuration

### Backend Configuration

The system uses several prompt templates located in `backend/prompts/`:

- `greet.txt` - Initial greeting messages
- `scienceqa.txt` - Science Q&A prompts
- `scaffolding.txt` - Educational scaffolding prompts
- `reflection.txt` - Reflection and evaluation prompts
- `knowledge_matching.txt` - Knowledge graph matching

## Running the System

### Start the Backend

```bash
cd backend
# Activate virtual environment
source venv/bin/activate
# Run in development mode
python app.py
```

### Start the Frontend

```bash
cd frontend
# Start development server with hot reload
npm run dev
```

### Building for Production

```bash
# Build frontend
cd frontend
npm run build

# The built files will be in dist/
```