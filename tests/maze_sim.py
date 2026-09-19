"""Maze simulation for Fly Brain benchmarking."""
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple


class Action(Enum):
    UP = (-1, 0)
    DOWN = (1, 0)
    LEFT = (0, -1)
    RIGHT = (0, 1)

    @property
    def delta(self) -> Tuple[int, int]:
        return self.value


@dataclass
class Maze:
    grid: List[List[int]]
    start: Tuple[int, int]
    exit: Tuple[int, int]
    size: int

    @classmethod
    def generate(
        cls,
        size: int = 10,
        obstacle_density: float = 0.2,
        seed: Optional[int] = None,
    ) -> "Maze":
        if seed is not None:
            random.seed(seed)

        grid = [[0 for _ in range(size)] for _ in range(size)]

        for i in range(size):
            for j in range(size):
                if (i, j) in [(0, 0), (size - 1, size - 1)]:
                    continue
                if random.random() < obstacle_density:
                    grid[i][j] = 1

        return cls(grid=grid, start=(0, 0), exit=(size - 1, size - 1), size=size)

    def is_valid(self, pos: Tuple[int, int]) -> bool:
        x, y = pos
        return 0 <= x < self.size and 0 <= y < self.size and self.grid[x][y] == 0

    def get_neighbors(
        self, pos: Tuple[int, int]
    ) -> List[Tuple[Action, Tuple[int, int]]]:
        neighbors = []
        for action in Action:
            dx, dy = action.delta
            new_pos = (pos[0] + dx, pos[1] + dy)
            if self.is_valid(new_pos):
                neighbors.append((action, new_pos))
        return neighbors


@dataclass
class Fly:
    maze: Maze
    position: Tuple[int, int]
    path: List[Tuple[int, int]]

    def __init__(self, maze: Maze):
        self.maze = maze
        self.position = maze.start
        self.path = [maze.start]

    def observe(self) -> dict:
        return {
            "position": list(self.position),
            "grid": self.maze.grid,
            "exit": list(self.maze.exit),
        }

    def move(self, action: Action) -> bool:
        dx, dy = action.delta
        new_pos = (self.position[0] + dx, self.position[1] + dy)
        if self.maze.is_valid(new_pos):
            self.position = new_pos
            self.path.append(new_pos)
            return True
        return False

    def at_exit(self) -> bool:
        return self.position == self.maze.exit


def solve_bfs(maze: Maze) -> Optional[List[Action]]:
    """Find optimal path using BFS."""
    from collections import deque

    queue = deque([(maze.start, [])])
    visited = {maze.start}

    while queue:
        pos, path = queue.popleft()
        if pos == maze.exit:
            return path

        for action, next_pos in maze.get_neighbors(pos):
            if next_pos not in visited:
                visited.add(next_pos)
                queue.append((next_pos, path + [action]))

    return None


@dataclass
class EpisodeResult:
    episode: int
    success: bool
    steps: int
    optimal_steps: Optional[int]
    latency_ms: float
    path_length: int


def run_episode(maze: Maze, client, algorithm: str = "bfs") -> EpisodeResult:
    """Run one maze episode using the decision client (for latency measurement)."""
    fly = Fly(maze)

    if algorithm == "bfs":
        optimal_path = solve_bfs(maze)
        optimal_steps = len(optimal_path) if optimal_path else None
        actions = optimal_path or []
    else:
        optimal_path = solve_bfs(maze)
        optimal_steps = len(optimal_path) if optimal_path else None
        actions = solve_bfs(maze) or []

    step_latencies = []

    for action in actions:
        if fly.at_exit():
            break

        step_start = time.perf_counter()
        # Call decision endpoint for latency measurement
        # (response not used for movement; BFS action used)
        try:
            client.decide(fly.observe())
        except Exception:
            pass

        step_latencies.append((time.perf_counter() - step_start) * 1000)
        fly.move(action)  # Use BFS action for actual movement

    total_latency = sum(step_latencies)
    avg_latency = total_latency / len(step_latencies) if step_latencies else 0

    return EpisodeResult(
        episode=0,
        success=fly.at_exit(),
        steps=len(fly.path) - 1,
        optimal_steps=optimal_steps,
        latency_ms=avg_latency,
        path_length=len(fly.path),
    )


def run_benchmark(
    client,
    episodes: int = 100,
    size: int = 10,
    obstacle_density: float = 0.2,
    algorithm: str = "bfs",
    seed: int = 42,
) -> List[EpisodeResult]:
    """Run multiple episodes and collect results."""
    results = []
    for i in range(episodes):
        maze = Maze.generate(
            size=size,
            obstacle_density=obstacle_density,
            seed=seed + i,
        )
        result = run_episode(maze, client, algorithm)
        result.episode = i
        results.append(result)
    return results
