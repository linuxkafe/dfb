#!/usr/bin/env python3
"""Graphical maze visualization for Fly Brain benchmarking."""
import pygame
import requests
import time
import sys
from typing import List, Tuple, Optional
import numpy as np

from tests.maze_sim import Maze, Fly, Action, solve_bfs


COLORS = {
    'bg': (30, 30, 30),
    'grid': (60, 60, 60),
    'empty': (50, 50, 50),
    'obstacle': (20, 20, 20),
    'fly': (0, 150, 255),
    'exit': (0, 255, 100),
    'path': (255, 200, 0),
    'visited': (100, 100, 255),
    'text': (255, 255, 255),
    'panel_bg': (40, 40, 40),
}


class MazeViz:
    def __init__(self, service_url: str = "http://steamdeck:8082", cell_size: int = 50):
        self.service_url = service_url
        self.cell_size = cell_size
        self.session = requests.Session()
        self.session.timeout = 5.0
        
        pygame.init()
        self.screen_width = 10 * cell_size + 300  # maze + side panel
        self.screen_height = 10 * cell_size + 100
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Fly Brain Maze Visualization")
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)
        self.clock = pygame.time.Clock()
        
        self.maze = None
        self.fly = None
        self.optimal_path = None
        self.episode = 0
        self.running = True
        self.paused = False
        self.step_mode = False
        self.step_requested = False
        self.show_optimal = True
        self.auto_run = True
        self.delay = 0.1
        
        self.stats = {
            'episodes': 0,
            'successes': 0,
            'total_steps': 0,
            'avg_latency': 0.0,
        }
    
    def new_episode(self, seed: Optional[int] = None):
        if seed is None:
            seed = self.episode
        self.maze = Maze.generate(size=10, obstacle_density=0.2, seed=seed)
        self.fly = Fly(self.maze)
        self.optimal_path = solve_bfs(self.maze)
        self.episode += 1
    
    def draw_maze(self):
        for x in range(self.maze.size):
            for y in range(self.maze.size):
                rect = pygame.Rect(
                    y * self.cell_size + 10,
                    x * self.cell_size + 10,
                    self.cell_size - 2,
                    self.cell_size - 2
                )
                
                if self.maze.grid[x][y] == 1:
                    color = COLORS['obstacle']
                else:
                    color = COLORS['empty']
                
                # Highlight optimal path
                if self.show_optimal and self.optimal_path:
                    fly_pos = self.maze.start
                    path_positions = [self.maze.start]
                    for action in self.optimal_path:
                        dx, dy = action.delta
                        fly_pos = (fly_pos[0] + dx, fly_pos[1] + dy)
                        path_positions.append(fly_pos)
                    if (x, y) in path_positions:
                        color = COLORS['path']
                
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, COLORS['grid'], rect, 1)
        
        # Draw fly
        fx, fy = self.fly.position
        fly_rect = pygame.Rect(
            fy * self.cell_size + 10 + 5,
            fx * self.cell_size + 10 + 5,
            self.cell_size - 10,
            self.cell_size - 10
        )
        pygame.draw.ellipse(self.screen, COLORS['fly'], fly_rect)
        
        # Draw exit
        ex, ey = self.maze.exit
        exit_rect = pygame.Rect(
            ey * self.cell_size + 10 + 5,
            ex * self.cell_size + 10 + 5,
            self.cell_size - 10,
            self.cell_size - 10
        )
        pygame.draw.rect(self.screen, COLORS['exit'], exit_rect)
        
        # Draw fly trail
        for pos in self.fly.path[:-1]:
            px, py = pos
            trail_rect = pygame.Rect(
                py * self.cell_size + 10 + self.cell_size // 2 - 3,
                px * self.cell_size + 10 + self.cell_size // 2 - 3,
                6, 6
            )
            pygame.draw.circle(self.screen, COLORS['visited'], trail_rect.center, 3)
    
    def draw_panel(self):
        panel_x = 10 * self.cell_size + 20
        panel_y = 10
        panel_w = 280
        
        # Background
        pygame.draw.rect(self.screen, COLORS['panel_bg'], 
                        (panel_x, panel_y, panel_w, self.screen_height - 20))
        
        lines = [
            f"Episode: {self.episode}",
            f"Position: {self.fly.position}",
            f"Exit: {self.maze.exit}",
            f"Steps: {len(self.fly.path) - 1}",
            f"Optimal: {len(self.optimal_path) if self.optimal_path else 'N/A'}",
            "",
            f"Total Episodes: {self.stats['episodes']}",
            f"Success Rate: {self.stats['successes']}/{self.stats['episodes']}" if self.stats['episodes'] > 0 else "Success Rate: N/A",
            f"Avg Steps: {self.stats['total_steps'] / self.stats['episodes']:.1f}" if self.stats['episodes'] > 0 else "Avg Steps: N/A",
            f"Avg Latency: {self.stats['avg_latency']:.1f}ms",
            "",
            "Controls:",
            "SPACE - Pause/Resume",
            "S - Step (when paused)",
            "N - New Episode",
            "O - Toggle Optimal Path",
            "A - Toggle Auto",
            "UP/DOWN - Speed",
            "ESC - Quit",
        ]
        
        for i, line in enumerate(lines):
            color = COLORS['text']
            if line.startswith("Controls:"):
                color = (255, 255, 100)
            text = self.small_font.render(line, True, color)
            self.screen.blit(text, (panel_x + 10, panel_y + 10 + i * 22))
    
    def step(self):
        if self.fly.at_exit():
            return False
        
        # Call decision endpoint
        start = time.perf_counter()
        try:
            resp = self.session.post(
                f"{self.service_url}/decide",
                json=self.fly.observe()
            )
            resp.raise_for_status()
            decision = resp.json()
            latency = (time.perf_counter() - start) * 1000
        except Exception as e:
            print(f"Decision error: {e}")
            latency = 0
            # Fallback to optimal
            if self.optimal_path:
                action = self.optimal_path[0]
            else:
                action = Action.RIGHT
        else:
            action_str = decision.get('action', 'RIGHT')
            action = Action[action_str]
        
        # Update stats
        self.stats['avg_latency'] = (self.stats['avg_latency'] * self.stats['episodes'] + latency) / (self.stats['episodes'] + 1)
        
        # Move fly
        self.fly.move(action)
        return True
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_s and self.paused:
                    self.step_requested = True
                elif event.key == pygame.K_n:
                    self.finish_episode()
                    self.new_episode()
                elif event.key == pygame.K_o:
                    self.show_optimal = not self.show_optimal
                elif event.key == pygame.K_a:
                    self.auto_run = not self.auto_run
                elif event.key == pygame.K_UP:
                    self.delay = max(0.01, self.delay - 0.02)
                elif event.key == pygame.K_DOWN:
                    self.delay = min(1.0, self.delay + 0.02)
    
    def finish_episode(self):
        self.stats['episodes'] += 1
        self.stats['total_steps'] += len(self.fly.path) - 1
        if self.fly.at_exit():
            self.stats['successes'] += 1
    
    def run(self):
        self.new_episode(seed=42)
        
        while self.running:
            self.handle_events()
            
            if not self.paused and self.auto_run:
                if not self.step():
                    self.finish_episode()
                    time.sleep(0.5)
                    self.new_episode()
                time.sleep(self.delay)
            elif self.paused and self.step_requested:
                if not self.step():
                    self.finish_episode()
                    time.sleep(0.5)
                    self.new_episode()
                self.step_requested = False
            
            self.screen.fill(COLORS['bg'])
            self.draw_maze()
            self.draw_panel()
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://steamdeck:8082')
    parser.add_argument('--cell-size', type=int, default=50)
    args = parser.parse_args()
    
    viz = MazeViz(args.url, args.cell_size)
    viz.run()


if __name__ == "__main__":
    main()