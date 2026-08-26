# NEAT-Evolve

NEAT-Evolve is a Flappy Bird AI learning project. Python runs the original Pygame game and evolves neural networks with NEAT. A browser dashboard starts training, displays live training information and Pygame frames, and provides a Beat AI challenge for the player.

## Architecture

```text
Browser
  |
  | HTTP: page, CSS, JavaScript, assets
  v
Python HTTP server :8000
  |
  | WebSocket: commands, status JSON, binary game frames
  v
Python WebSocket server :8765
  |
  +--> Training thread
  |      +--> Pygame game loop
  |      +--> NEAT population and neural networks
  |      +--> JPEG frame encoder
  |
  +--> Shared application state
```

The browser is the presentation and control layer. Python is the source of truth for AI training, scoring, fitness, game physics, rendering, and target completion. The browser does not simulate the AI training run.

## Folder Structure

```text
NEAT-Evolve/
├── backend/
│   ├── flappy_bird.py          # Pygame, NEAT, WebSocket, and service startup
│   ├── config_feedforward.txt  # NEAT configuration
│   ├── routes/
│   │   └── __init__.py         # HTTP routes and static-file handler
│   └── tempCodeRunnerFile.py   # Temporary editor-generated file
├── frontend/
│   ├── index.html              # Page structure
│   ├── app.js                  # WebSocket client and Beat AI mode
│   ├── style.css               # Layout and visual design
│   └── imgs/                   # Pygame and browser game sprites
├── requirements.txt            # Python dependencies
├── README.md
└── .gitignore
```

## Backend Responsibilities

### `backend/flappy_bird.py`

This is the main application module. It:

- Loads Pygame assets from `frontend/imgs`.
- Creates the `Bird`, `Pipe`, and `Base` game objects.
- Runs the Pygame game loop at 30 updates per second.
- Creates and evaluates NEAT neural networks.
- Maintains shared training state.
- Captures Pygame frames and encodes them as JPEG.
- Starts the HTTP and WebSocket services.

### `backend/routes/__init__.py`

This module contains the HTTP handler factory. It serves the frontend and contains the legacy HTTP endpoints:

| Route | Method | Purpose |
| --- | --- | --- |
| `/` | GET | Serves `frontend/index.html` |
| `/api/status` | GET | Returns training state as JSON |
| `/api/start` | POST | Starts training through HTTP |
| `/api/stop` | POST | Requests training to stop |
| `/api/stream` | GET | Legacy MJPEG frame stream |

The current frontend uses WebSockets for training communication. The HTTP API remains available as a compatibility path.

## Frontend Responsibilities

### `frontend/index.html`

Defines the dashboard and controls:

- Target score form
- Training view
- Python game frame display
- Training metrics
- Completion overlay
- Train Again and Beat AI buttons
- Player canvas for the Beat AI challenge

### `frontend/app.js`

The browser client:

- Opens a WebSocket connection to Python.
- Sends `start` and `stop` commands.
- Receives JSON status messages.
- Receives binary JPEG frame messages.
- Updates dashboard values through the DOM.
- Runs the browser-side player challenge after Beat AI is clicked.

The Beat AI challenge is separate from AI training. It uses the same main gameplay settings but runs in the browser so the player receives immediate keyboard and pointer input.

### `frontend/style.css`

Contains the visual system, including CSS variables, responsive layout, overlays, buttons, and game viewport styling.

## WebSocket Communication

The local WebSocket endpoint is:

```text
ws://localhost:8765
```

The connection is bidirectional and remains open while the page is active.

### Browser to Python

Start training:

```json
{"action":"start","target":10}
```

Stop training:

```json
{"action":"stop"}
```

### Python to Browser: status

Python sends status as JSON:

```json
{
  "running": true,
  "status": "TRAINING IN PROGRESS",
  "target": 10,
  "generation": 4,
  "score": 3,
  "best": 8,
  "elapsed": 24.8,
  "population": 15,
  "alive": 7,
  "average_fitness": 12.4,
  "best_fitness": 30.1
}
```

### Python to Browser: game frames

Pygame renders to a `400x600` surface. Python copies the surface pixels to Pillow and sends a compressed JPEG as a binary WebSocket message. The browser receives the message as a `Blob` and assigns it to the game image element.

Only the latest frame is retained in Python. A frame version prevents sending the same frame repeatedly.

## Training Workflow

1. The user enters a target score.
2. The browser sends a WebSocket `start` command.
3. Python resets the training state and starts a background training thread.
4. NEAT creates a population of genomes.
5. Each genome becomes a neural network controlling one bird.
6. Birds move, jump, collide, receive fitness, and pass pipes.
7. Python sends status and rendered frames to the browser.
8. When the best score reaches the target, Python sends `TARGET BEATEN`.
9. The browser stops its elapsed-time display and shows the completion overlay.

## Game Logic

The current backend settings are:

```text
Window:        400 x 600
Bird start:    x=50, y=150
Pipe gap:      GAP=150
Pipe speed:    VEL=5
Pipe vertical: VEL_UP=2
Ground:        y=500
Jump velocity: -10
Frame rate:    30 FPS
```

The `Bird` class implements acceleration, terminal displacement, jumping, tilt, wing animation, and pixel-mask collision support.

The `Pipe` class implements horizontal movement, vertical oscillation, direction reversal, gap positioning, and pixel-mask collision detection.

The `Base` class creates the scrolling floor by moving two repeated base images.

## NEAT Concepts

NEAT stands for NeuroEvolution of Augmenting Topologies. It evolves neural networks using genetic operations instead of gradient-descent training.

### Genome

A genome represents a candidate neural network. It contains nodes, connections, weights, biases, and enabled or disabled connection states.

### Inputs and output

The configuration defines three inputs and one output:

```text
Inputs:
1. Bird vertical position
2. Distance to the top pipe
3. Distance to the bottom pipe

Output:
Jump decision
```

The bird jumps when the output is greater than `0.5`.

### Fitness

Fitness measures performance:

- Living increases fitness by `0.1` per game update.
- Collision decreases fitness by `1`.
- Passing a pipe increases fitness by `5`.

The dashboard reports current average fitness and best fitness.

### Generation

A generation evaluates the current population. NEAT then selects stronger genomes, preserves elite genomes, mutates connections and weights, and creates the next population.

The configuration currently uses a population size of `15`, three inputs, one output, `tanh` activation, and a feed-forward network.

## Concurrency and Shared State

Python uses threads because the HTTP server, WebSocket server, and training loop must operate at the same time.

Shared values are protected by `threading.Lock`. `threading.Event` objects coordinate stop and completion requests. A `threading.Condition` coordinates access to the newest rendered frame.

## Beat AI Mode

Beat AI starts after the Python AI reaches the selected target.

The browser player mode uses a `400x600` HTML canvas and mirrors the important Python settings: bird position and jump velocity, gravity, pipe gap and movement, vertical pipe movement, bird animation and rotation, and ground boundaries.

The AI training duration becomes the player time limit:

- A collision resets the player attempt to score `0`.
- The countdown does not reset after a collision.
- Reaching the target before time expires wins.
- Reaching zero seconds loses.

## Technology Concepts Used

| Concept | Use in this project |
| --- | --- |
| Python | Backend application and AI training |
| Pygame | Game loop, sprites, surfaces, physics, collision masks |
| NEAT-Python | Evolutionary neural-network training |
| HTTP | Frontend file serving and compatibility API |
| WebSockets | Bidirectional commands, status, and frame transfer |
| `asyncio` | Asynchronous WebSocket server and message tasks |
| Threading | Concurrent web servers and AI training |
| Locks | Safe access to shared state |
| Events | Stop and target-completion signaling |
| Conditions | Coordination around new rendered frames |
| Pillow | JPEG encoding of Pygame frames |
| HTML | Dashboard structure and controls |
| CSS | Layout, responsive design, and visual states |
| JavaScript | WebSocket client, DOM updates, canvas game, timers |
| Canvas API | Player-controlled Beat AI rendering |
| DOM API | Updating status, scores, fitness, and overlays |
| Git | Version control and GitHub publishing |
| Render | Possible hosting platform for the Python service |

## Installation

Use Python 3.11 or a compatible Python 3 version:

```powershell
python -m pip install -r requirements.txt
```

Dependencies:

- `pygame`: game rendering and input
- `neat-python`: NEAT implementation
- `websockets`: WebSocket server
- `Pillow`: JPEG frame encoding

## Run Locally

From the project root:

```powershell
python backend/flappy_bird.py
```

Open:

```text
http://localhost:8000
```

The Python process serves the frontend on port `8000` and the WebSocket server on port `8765`.

## Deployment Notes

Render is more suitable than Vercel for this application because the backend is a long-running Python process with Pygame rendering, background training, and WebSockets.

Before production deployment:

1. Bind HTTP to `0.0.0.0`.
2. Use Render's `PORT` environment variable.
3. Use headless Pygame with `SDL_VIDEODRIVER=dummy`.
4. Serve HTTP and WebSockets through one public Render port, or place a reverse proxy in front of the two local listeners.
5. Use `wss://` for secure production WebSockets.

The current local configuration uses separate ports `8000` and `8765`, which is convenient for development but should be adapted before deployment.

## Useful Commands

Run syntax checks:

```powershell
python -m py_compile backend/flappy_bird.py backend/routes/__init__.py
node --check frontend/app.js
```

Check Git status:

```powershell
git status
```
