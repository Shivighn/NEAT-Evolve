import neat.config
import pygame
import random
import os
import time
import neat
import pickle
import json
import io
import threading
import asyncio
import websockets
from PIL import Image
from http.server import ThreadingHTTPServer
from routes import create_web_handler
pygame.font.init()  # init font

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(PROJECT_DIR, "frontend")
ASSETS_DIR = os.path.join(FRONTEND_DIR, "imgs")

WIN_WIDTH = 400
WIN_HEIGHT = 600

pipe_img = pygame.transform.scale2x(pygame.image.load(os.path.join(ASSETS_DIR,"pipe.png")))
bg_img = pygame.transform.scale(pygame.image.load(os.path.join(ASSETS_DIR,"bg.png")), (600, 900))
bird_images = [pygame.transform.scale(pygame.image.load(os.path.join(ASSETS_DIR,"bird" + str(x) + ".png")),(40,30)) for x in range(1,4)]
base_img = pygame.transform.scale2x(pygame.image.load(os.path.join(ASSETS_DIR,"base.png")))
STAT_FONT = pygame.font.SysFont("comicsans", 50)

training_state = {"running": False, "status": "READY TO TRAIN", "target": 10,
                  "generation": 0, "score": 0, "best": 0, "elapsed": 0,
                  "population": 0, "alive": 0, "average_fitness": 0,
                  "best_fitness": 0}
state_lock = threading.Lock()
stop_requested = threading.Event()
target_reached = threading.Event()
training_started_at = None
latest_frame = None
frame_version = 0
frame_condition = threading.Condition()
websocket_loop = None


def start_training(target):
    global training_started_at
    with state_lock:
        training_state.update({"running": True, "status": "TRAINING IN PROGRESS",
                               "target": target, "generation": 0,
                               "score": 0, "best": 0, "elapsed": 0,
                               "population": 0, "alive": 0,
                               "average_fitness": 0, "best_fitness": 0})
    stop_requested.clear()
    target_reached.clear()
    training_started_at = time.monotonic()
    threading.Thread(target=run, args=(os.path.join(os.path.dirname(__file__),
                              "config_feedforward.txt"),), daemon=True).start()


async def websocket_handler(websocket):
    async def send_updates():
        last_frame = None
        last_status_at = 0
        while True:
            now = time.monotonic()
            if now - last_status_at >= 0.2:
                with state_lock:
                    payload = dict(training_state)
                if payload["running"] and training_started_at:
                    payload["elapsed"] = now - training_started_at
                await websocket.send(json.dumps(payload))
                last_status_at = now
            with frame_condition:
                frame = latest_frame
                version = frame_version
            if frame is not None and version != last_frame:
                await websocket.send(frame)
                last_frame = version
            await asyncio.sleep(1 / 30)

    sender = asyncio.create_task(send_updates())
    try:
        async for message in websocket:
            request = json.loads(message)
            if request.get("action") == "start":
                start_training(max(1, int(request.get("target", 10))))
            elif request.get("action") == "stop":
                stop_requested.set()
    finally:
        sender.cancel()


def start_websocket_server():
    async def serve():
        async with websockets.serve(websocket_handler, "0.0.0.0", 8765):
            await asyncio.Future()
    try:
        asyncio.run(serve())
    except OSError as error:
        if error.errno not in (98, 10048) and getattr(error, "winerror", None) != 10048:
            raise
        print("WebSocket server already running on port 8765")

# game sprites
class Bird:
    # General variables
    MAX_ROTATION = 25
    IMGS = bird_images
    ROT_VEL = 20
    ANIMATION_TIME = 5

    def __init__(self, x, y):
        #Bird initialisation
        self.x = x
        self.y = y
        self.tilt = 0  # degrees to tilt
        self.tick_count = 0
        self.vel = 0
        self.height = self.y
        self.img_count = 0
        self.img = self.IMGS[0]

    def jump(self):

        # bird jump
        self.vel = -10
        self.tick_count = 0
        self.height = self.y

    def move(self):
        #bird move whne pressing key
        self.tick_count += 1

        # for downward acceleration
        displacement = self.vel*(self.tick_count) + 0.5*(3)*(self.tick_count)**2  # calculate displacement

        # terminal velocity
        if displacement >= 16:
            displacement = (displacement/abs(displacement)) * 16

        if displacement < 0:
            displacement -= 2

        self.y = self.y + displacement

        if displacement < 0 or self.y < self.height + 50:  # tilt up
            if self.tilt < self.MAX_ROTATION:
                self.tilt = self.MAX_ROTATION
        else:  # tilt down
            if self.tilt > -90:
                self.tilt -= self.ROT_VEL

    def draw(self, win):
        # Draw the bird using pygame
        self.img_count += 1

        # For animation of bird, loop through three images
        if self.img_count <= self.ANIMATION_TIME:
            self.img = self.IMGS[0]
        elif self.img_count <= self.ANIMATION_TIME*2:
            self.img = self.IMGS[1]
        elif self.img_count <= self.ANIMATION_TIME*3:
            self.img = self.IMGS[2]
        elif self.img_count <= self.ANIMATION_TIME*4:
            self.img = self.IMGS[1]
        elif self.img_count == self.ANIMATION_TIME*4 + 1:
            self.img = self.IMGS[0]
            self.img_count = 0

        # so when bird is nose diving it isn't flapping
        if self.tilt <= -80:
            self.img = self.IMGS[1]
            self.img_count = self.ANIMATION_TIME*2


        # tilt the bird
        blitRotateCenter(win, self.img, (self.x, self.y), self.tilt)

    def get_mask(self):
        #returning mask for gameobject
        return pygame.mask.from_surface(self.img)

class Pipe:
    GAP = 150
    VEL = 5
    VEL_UP = 2

    def __init__(self, x):
        # Initialising pipes
        self.x = x
        self.height = 0

        # where the top and bottom of the pipe is
        self.top = 0
        self.bottom = 0

        self.PIPE_TOP = pygame.transform.flip(pipe_img, False, True)
        self.PIPE_BOTTOM = pipe_img

        self.passed = False
        self.vertical_vel = self.VEL_UP

        self.set_height()

    def set_height(self):
        # distance of gap from the top of screen
        self.height = random.randrange(50, 300)
        self.top = self.height - self.PIPE_TOP.get_height()
        self.bottom = self.height + self.GAP

    def move(self):
        # moving pipe
        self.x -= self.VEL
        self.height += self.vertical_vel
        if self.height <= 50 or self.height >= 300:
            self.height = max(50, min(300, self.height))
            self.vertical_vel *= -1
        self.top = self.height - self.PIPE_TOP.get_height()
        self.bottom = self.height + self.GAP

    def draw(self, win):
        # drawing pipes (Bottom and top)
        # draw top
        win.blit(self.PIPE_TOP, (self.x, self.top))
        # draw bottom
        win.blit(self.PIPE_BOTTOM, (self.x, self.bottom))

    def collide(self, bird):
        # checking for collision using masks
        bird_mask = bird.get_mask()
        top_mask = pygame.mask.from_surface(self.PIPE_TOP)
        bottom_mask = pygame.mask.from_surface(self.PIPE_BOTTOM)

        top_offset = (self.x - bird.x, self.top - round(bird.y))
        bottom_offset = (self.x - bird.x, self.bottom - round(bird.y))

        b_point = bird_mask.overlap(bottom_mask, bottom_offset)
        t_point = bird_mask.overlap(top_mask,top_offset)

        if b_point or t_point:
            return True

        return False

class Base:
    VEL = 5
    WIDTH = base_img.get_width()
    IMG = base_img

    def __init__(self, y):
        self.y = y
        self.x1 = 0
        self.x2 = self.WIDTH

    def move(self):
        self.x1 -= self.VEL
        self.x2 -= self.VEL
        if self.x1 + self.WIDTH < 0:
            self.x1 = self.x2 + self.WIDTH

        if self.x2 + self.WIDTH < 0:
            self.x2 = self.x1 + self.WIDTH

    def draw(self, win):
        win.blit(self.IMG, (self.x1, self.y))
        win.blit(self.IMG, (self.x2, self.y))

# game orientations
def blitRotateCenter(surf, image, topleft, angle):
    rotated_image = pygame.transform.rotate(image, angle)
    new_rect = rotated_image.get_rect(center = image.get_rect(topleft = topleft).center)

    surf.blit(rotated_image, new_rect.topleft)

def draw_window(win, birds, pipes, base, score):
    global latest_frame, frame_version
    win.blit(bg_img, (0,0))

    for pipe in pipes:
        pipe.draw(win)

    # score
    score_label = STAT_FONT.render("Score: " + str(score),1,(255,255,255))
    win.blit(score_label, (WIN_WIDTH - score_label.get_width() - 15, 10))

    base.draw(win)
    for bird in birds:    
        bird.draw(win)
    pygame.display.update()
    pixels = pygame.image.tostring(win, "RGB")
    image = Image.frombytes("RGB", (WIN_WIDTH, WIN_HEIGHT), pixels)
    frame = io.BytesIO()
    image.save(frame, "JPEG", quality=70, optimize=False)
    with frame_condition:
        latest_frame = frame.getvalue()
        frame_version += 1
        frame_condition.notify_all()

# learning mechnaism
def main(genomes,config):
    global training_started_at
    nets = []
    ge =[]
    birds = []

    for _,g in genomes:
        net = neat.nn.FeedForwardNetwork.create(g,config)
        nets.append(net)
        birds.append(Bird(50,150))
        g.fitness = 0
        ge.append(g)

    base = Base(500)
    pipes = [Pipe(300)]
    win = pygame.display.set_mode((WIN_WIDTH,WIN_HEIGHT))
    clock = pygame.time.Clock()

    score = 0
    run = True
    with state_lock:
        training_state["generation"] += 1
        training_state["score"] = 0
        training_state["population"] = len(birds)
        training_state["alive"] = len(birds)
    while run:

        clock.tick(30)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                pygame.quit()
                stop_requested.set()

        pipe_ind = 0
        if len(birds)>0:
            if len(pipes)>1 and birds[0].x > pipes[0].x+pipes[0].PIPE_TOP.get_width():
                pipe_ind=1
        else:
            run = False
            break

        for x,bird in enumerate(birds):
            bird.move()
            ge[x].fitness += 0.1

            output = nets[x].activate((bird.y,abs(bird.y-pipes[pipe_ind].height),abs(bird.y-pipes[pipe_ind].bottom)))
            # we get list of outputs as we have 1 output neuron we put ouput[0]
            if output[0] > 0.5:
                bird.jump()


        add_pipe = False
        rem = []
        for pipe in pipes:
            for x,bird in enumerate(birds):

                if pipe.collide(bird):
                    ge[x].fitness-=1
                    birds.pop(x)
                    nets.pop(x)
                    ge.pop(x)
                    

                if not pipe.passed and pipe.x < bird.x:
                    pipe.passed = True
                    add_pipe = True


            if pipe.x + pipe.PIPE_TOP.get_width() < 0:
                rem.append(pipe)
        
            pipe.move()

        if add_pipe:
            score += 1
            for g in ge:
                g.fitness += 5
            pipes.append(Pipe(300))
            with state_lock:
                training_state["score"] = score
                training_state["best"] = max(training_state["best"], score)
            if score >= training_state["target"]:
                target_reached.set()
                run = False

        for r in rem:
            pipes.remove(r)

        for x,bird in enumerate(birds):
            if bird.y + bird.img.get_height() >= 500 or bird.y < 0:
                birds.pop(x)
                nets.pop(x)
                ge.pop(x)

        base.move()
        draw_window(win, birds, pipes, base,score)

        with state_lock:
            fitness_values = [genome.fitness for genome in ge]
            training_state["elapsed"] = time.monotonic() - training_started_at
            training_state["alive"] = len(birds)
            training_state["average_fitness"] = (sum(fitness_values) / len(fitness_values)
                                                  if fitness_values else 0)
            training_state["best_fitness"] = max(fitness_values, default=0)
        if stop_requested.is_set() or target_reached.is_set():
            run = False



def run(config_path):
    global training_started_at
    #loading configuration file
    config = neat.config.Config(neat.DefaultGenome, neat.DefaultReproduction,
                            neat.DefaultSpeciesSet, neat.DefaultStagnation,
                            config_path)
    
    #population data
    p = neat.Population(config)

    #printing Statistics
    p.add_reporter(neat.StdOutReporter(True))
    stats = neat.StatisticsReporter()
    p.add_reporter(stats)

    for _ in range(30):
        if stop_requested.is_set() or target_reached.is_set():
            break
        p.run(main, 1)
    with state_lock:
        training_state["running"] = False
        training_state["status"] = ("TARGET BEATEN" if target_reached.is_set()
                                     else "RUN STOPPED")


if __name__ == "__main__":
    web_handler = create_web_handler(
        FRONTEND_DIR, training_state, state_lock, stop_requested,
        lambda: training_started_at, start_training,
        lambda: latest_frame, frame_condition)
    server = ThreadingHTTPServer(("localhost", 8000), web_handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    threading.Thread(target=start_websocket_server, daemon=True).start()
    print("Website: http://localhost:8000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Server stopped")
        server.server_close()