import pygame
import pygame.gfxdraw
from collections import deque

_framerate = None
_screen = None
_clock = None

def mainloop(rasterize_fn):

    colors_queue = deque()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            
        rasterize_fn(colors_queue)
        
        try:
            color = colors_queue.pop()
        except IndexError:
            _clock.tick(_framerate)
            continue

        pygame.draw.circle(_screen, color, (400, 300), 100)

        pygame.display.flip()
        _clock.tick(_framerate)

def init(framerate):
    global _clock, _screen, _framerate
    
    _framerate = framerate

    pygame.init()
    _screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption('Audio Visualizer')

    _screen.fill((0, 0, 0))
    
    _clock = pygame.time.Clock()