const fields = {
  generation: document.querySelector("#generation"),
  alive: document.querySelector("#aliveCount"),
  best: document.querySelector("#bestScore"),
  population: document.querySelector("#population"),
  averageFitness: document.querySelector("#averageFitness"),
  bestFitness: document.querySelector("#bestFitness"),
  elapsed: document.querySelector("#elapsedTime"),
  status: document.querySelector("#statusText")
};
const gameStream = document.querySelector("#gameStream");
const streamPlaceholder = document.querySelector("#streamPlaceholder");
const clockState = { elapsed: 0, running: false, receivedAt: performance.now() };
const webTimer = { startedAt: 0, running: false };
const playerCanvas = document.querySelector("#playerCanvas");
const playerContext = playerCanvas.getContext("2d");
const playerImages = {
  background: "imgs/bg.png",
  pipe: "imgs/pipe.png",
  base: "imgs/base.png",
  birds: ["imgs/bird1.png", "imgs/bird2.png", "imgs/bird3.png"]
};
const player = { active: false, score: 0, target: 0, timeLimit: 0, startedAt: 0,
  bird: { x: 50, y: 150, velocity: 0, tick: 0, height: 150, tilt: 0, imgCount: 0 },
  pipes: [], lastFrame: 0 };
const loadedImages = Object.fromEntries(Object.entries(playerImages).map(([key, value]) => {
  if (Array.isArray(value)) return [key, value.map(loadImage)];
  return [key, loadImage(value)];
}));
let socket;
let previousFrameUrl;

function loadImage(source) {
  const image = new Image();
  image.src = source;
  return image;
}

function formatTime(seconds) {
  const minutes = Math.floor(seconds / 60).toString().padStart(2, "0");
  return `${minutes}:${(seconds % 60).toFixed(1).padStart(4, "0")}`;
}

function showStatus(data) {
  fields.generation.textContent = data.generation;
  fields.best.textContent = data.best;
  fields.population.textContent = data.population;
  fields.averageFitness.textContent = Number(data.average_fitness).toFixed(2);
  fields.bestFitness.textContent = Number(data.best_fitness).toFixed(2);
  clockState.elapsed = data.elapsed;
  clockState.running = data.running;
  clockState.receivedAt = performance.now();
  if (webTimer.running && (data.status === "TARGET BEATEN"
      || data.status === "RUN STOPPED"
      || (!data.running && data.status !== "READY TO TRAIN"))) {
    webTimer.running = false;
    clockState.elapsed = data.elapsed;
  }
  fields.elapsed.textContent = formatTime(clockState.elapsed);
  fields.alive.textContent = data.running ? "RUNNING" : "-";
  fields.status.textContent = data.status;
  if (!player.active && !webTimer.running && data.best >= data.target && !data.running) {
    document.querySelector("#learningLabel").textContent = "LEARNING COMPLETE";
    document.querySelector("#finalScore").textContent = data.best;
    document.querySelector("#completeOverlay").classList.remove("hidden");
  }
}

function connectSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  socket = new WebSocket(`${protocol}//${window.location.host}/ws`);
  socket.binaryType = "blob";
  socket.onmessage = (event) => {
    if (typeof event.data === "string") {
      showStatus(JSON.parse(event.data));
      return;
    }
    const oldFrameUrl = previousFrameUrl;
    previousFrameUrl = URL.createObjectURL(event.data);
    gameStream.onload = () => {
      if (oldFrameUrl) URL.revokeObjectURL(oldFrameUrl);
    };
    gameStream.src = previousFrameUrl;
    gameStream.classList.add("visible");
    streamPlaceholder.classList.add("hidden");
  };
  socket.onclose = () => window.setTimeout(connectSocket, 1000);
}

function makePlayerPipe(x) {
  return { x, height: 50 + Math.floor(Math.random() * 250), verticalVelocity: 3,
    passed: false };
}

function playerJump() {
  if (player.active) {
    player.bird.velocity = -10;
    player.bird.tick = 0;
    player.bird.height = player.bird.y;
  }
}

function playerCollides(pipe) {
  const bird = player.bird;
  return bird.x + 35 > pipe.x && bird.x + 5 < pipe.x + 104
    && (bird.y + 4 < pipe.height || bird.y + 27 > pipe.height + 140);
}

function drawPlayer() {
  const context = playerContext;
  const bird = player.bird;
  context.drawImage(loadedImages.background, 0, 0, 600, 900);
  player.pipes.forEach((pipe) => {
    context.save();
    context.translate(pipe.x + 52, pipe.height);
    context.scale(1, -1);
    context.drawImage(loadedImages.pipe, -52, 0, 104, 640);
    context.restore();
    context.drawImage(loadedImages.pipe, pipe.x, pipe.height + 140, 104, 640);
  });
  bird.imgCount += 1;
  let birdImageIndex = 0;
  if (bird.imgCount > 5 && bird.imgCount <= 10) birdImageIndex = 1;
  if (bird.imgCount > 10 && bird.imgCount <= 15) birdImageIndex = 2;
  if (bird.imgCount > 15 && bird.imgCount <= 20) birdImageIndex = 1;
  if (bird.imgCount > 20) bird.imgCount = 0;
  if (bird.tilt <= -80) {
    birdImageIndex = 1;
    bird.imgCount = 10;
  }
  context.save();
  context.translate(bird.x + 20, bird.y + 15);
  context.rotate(-bird.tilt * Math.PI / 180);
  context.drawImage(loadedImages.birds[birdImageIndex], -20, -15, 40, 30);
  context.restore();
  context.drawImage(loadedImages.base, 0, 500, 672, 224);
  context.fillStyle = "white";
  context.font = "bold 28px sans-serif";
  context.fillText(`Score: ${player.score}`, 270, 40);
}

function finishPlayer(success) {
  player.active = false;
  const remaining = Math.max(0, player.timeLimit
    - (performance.now() - player.startedAt) / 1000);
  fields.elapsed.textContent = formatTime(remaining);
  const outcomeTitle = document.querySelector("#outcomeTitle");
  outcomeTitle.textContent = success ? "YOU BEAT THE AI" : "YOU LOST";
  outcomeTitle.classList.toggle("win", success);
  outcomeTitle.classList.toggle("loss", !success);
  document.querySelector("#outcomeMessage").textContent = success
    ? "Humanity is safe."
    : "The AI keeps the crown. Time ran out.";
  document.querySelector("#learningLabel").textContent = success ? "AI BEATEN" : "TIME EXPIRED";
  document.querySelector("#finalScore").textContent = player.score;
  document.querySelector("#completeOverlay").classList.remove("hidden");
}

function resetPlayerAttempt() {
  player.score = 0;
  player.bird = { x: 50, y: 150, velocity: 0, tick: 0, height: 150, tilt: 0, imgCount: 0 };
  player.pipes = [makePlayerPipe(300)];
}

function playerFrame(timestamp) {
  if (!player.active) return;
  const remaining = Math.max(0, player.timeLimit
    - (performance.now() - player.startedAt) / 1000);
  fields.elapsed.textContent = formatTime(remaining);
  if (!player.lastFrame) player.lastFrame = timestamp;
  if (timestamp - player.lastFrame >= 1000 / 30) {
    player.lastFrame = timestamp;
    const bird = player.bird;
    bird.tick += 1;
    let displacement = bird.velocity * bird.tick + 0.5 * 3 * bird.tick ** 2;
    if (displacement >= 16) displacement = 16;
    if (displacement < 0) displacement -= 2;
    bird.y += displacement;
    if (displacement < 0 || bird.y < bird.height + 50) {
      bird.tilt = Math.min(25, bird.tilt + 25);
    } else {
      bird.tilt = Math.max(-90, bird.tilt - 20);
    }
    player.pipes.forEach((pipe) => {
      pipe.x -= 5;
      pipe.height += pipe.verticalVelocity;
      if (pipe.height <= 50 || pipe.height >= 300) {
        pipe.height = Math.max(50, Math.min(300, pipe.height));
        pipe.verticalVelocity *= -1;
      }
      if (!pipe.passed && pipe.x < bird.x) {
        pipe.passed = true;
        player.score += 1;
        if (player.score >= player.target) finishPlayer(true);
        player.pipes.push(makePlayerPipe(300));
      }
    });
    player.pipes = player.pipes.filter((pipe) => pipe.x + 104 >= 0);
    if (player.active && (bird.y < 0 || bird.y + 30 >= 500 || player.pipes.some(playerCollides))) {
      resetPlayerAttempt();
    }
    if (player.active) drawPlayer();
  }
  if (player.active && (performance.now() - player.startedAt) / 1000 >= player.timeLimit) {
    finishPlayer(false);
  }
  if (player.active) window.requestAnimationFrame(playerFrame);
}

function animateClock() {
  const elapsed = webTimer.running
    ? (performance.now() - webTimer.startedAt) / 1000
    : clockState.elapsed;
  fields.elapsed.textContent = formatTime(elapsed);
  window.requestAnimationFrame(animateClock);
}

async function startTraining(event) {
  event.preventDefault();
  const target = Math.max(1, Number(document.querySelector("#targetScore").value));
  document.querySelector("#targetDisplay").textContent = target;
  document.querySelector("#setupView").classList.add("hidden");
  document.querySelector("#trainingView").classList.remove("hidden");
  document.querySelector("#completeOverlay").classList.add("hidden");
  const outcomeTitle = document.querySelector("#outcomeTitle");
  outcomeTitle.textContent = "TARGET BEATEN";
  outcomeTitle.classList.remove("win", "loss");
  document.querySelector("#outcomeMessage").textContent = "pipes cleared";
  webTimer.startedAt = performance.now();
  webTimer.running = true;
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ action: "start", target }));
  }
}

document.querySelector("#startForm").addEventListener("submit", startTraining);
document.querySelector("#stopButton").addEventListener("click", () => {
  if (socket && socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ action: "stop" }));
});
function returnToTrainingSetup() {
  document.querySelector("#trainingView").classList.add("hidden");
  document.querySelector("#setupView").classList.remove("hidden");
}

function startBeatAI() {
  player.target = Number(document.querySelector("#targetDisplay").textContent);
  player.timeLimit = clockState.elapsed;
  resetPlayerAttempt();
  player.startedAt = performance.now();
  player.lastFrame = 0;
  player.active = true;
  document.querySelector("#completeOverlay").classList.add("hidden");
  gameStream.classList.remove("visible");
  playerCanvas.classList.add("visible");
  playerCanvas.focus();
  window.requestAnimationFrame(playerFrame);
}

document.querySelector("#againButton").addEventListener("click", returnToTrainingSetup);
document.querySelector("#beatButton").addEventListener("click", startBeatAI);
document.addEventListener("keydown", (event) => {
  if (event.code === "Space" || event.code === "ArrowUp") {
    event.preventDefault();
    playerJump();
  }
});
playerCanvas.addEventListener("pointerdown", playerJump);

animateClock();
connectSocket();
