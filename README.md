# Flappy Bird AI with NEAT

This project is an implementation of the classic Flappy Bird game, where an AI learns to play using the NEAT (NeuroEvolution of Augmenting Topologies) algorithm. The game is built with Python and Pygame, and the AI evolves its neural network to improve its gameplay over generations.

## Features
- **Python & Pygame:** The game is fully coded in Python using the Pygame library for graphics and game logic.
- **NEAT Algorithm:** Uses the NEAT algorithm to evolve neural networks that control the bird, allowing it to learn how to play Flappy Bird autonomously.
- **Configurable:** The NEAT configuration is easily adjustable via `config_feedforward.txt`.

## How it Works
- The AI controls the bird, deciding when to jump based on its position and the pipes' positions.
- Each generation, a population of neural networks (birds) is evaluated.
- The best-performing networks are selected and evolved to improve performance over time.


2. **Add Game Assets:**
   - Place the required images (`bird1.png`, `bird2.png`, `bird3.png`, `pipe.png`, `base.png`, `bg.png`) in an `imgs` folder in the project directory.

   ```bash
   python flappy_bird.py
   ```

## Files
- `flappy_bird.py`: Main game and AI logic.
- `config_feedforward.txt`: NEAT configuration file.
- `.gitignore`: Standard Python and project ignores.


## Getting Started
1. **Install Requirements:**
   - Python 3.x
   - Pygame (`pip install pygame`)
   - NEAT-Python (`pip install neat-python`)

2. **Cloning the Project**
   To get started, clone this repository to your local machine:

   ```bash
   git clone https://github.com/Shivighn/NEAT-Evolve
   cd Flappybird_AI
   ```

3. **Run the Game:**
   After installing the requirements and adding the game assets, you can run the game with:

   ```bash
   python flappy_bird.py
   ```


- **Practical Application:** Able to integrate AI with real-time games and visualize the learning process.
- **Clean Code & Documentation:** Strive for readable, maintainable code and clear project documentation.

---

*Feel free to explore, fork, or contribute!* 