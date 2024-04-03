import logging
import random
from typing import List

# not all imports are currently used, but they might be in the future and it shows all available functionalities
from socha import (
    Accelerate,
    AccelerationProblem,
    Advance,
    AdvanceInfo,
    AdvanceProblem,
    Board,
    CartesianCoordinate,
    CubeCoordinates,
    CubeDirection,
    Field,
    FieldType,
    GameState,
    Move,
    Passenger,
    Push,
    PushProblem,
    Segment,
    Ship,
    TeamEnum,
    TeamPoints,
    Turn,
    TurnProblem,
)
from socha.api.networking.game_client import IClientHandler
from socha.starter import Starter

import networkx as nx

'''
Plan:
Letztes Feld aus dem Mittelstrom rausfinden mit Vektor

Graphen mit allen Nodes bauen ohne edges oder einfach übernehmen ohne edges von letztem zug + wenn neues segment auch die felder
Dijkstra von Schiff aus, die Edges on the go generieren 
Distanz zum "Ziel"
Kohle
Rotations
Speed

vllt wenn drei von den top 10 feldern discovered sind: abbrechen

Build Graph:
Alle neuen Nodes
Blanko Edges???
Dann bei jedem durchlauf die gewichte hinzufügen/ändern

und dann wieder die weights clearen?

ODER

keine edges
die edges immer neu hinzufügen mit weights -> cube coords, ob edges possible sind???
edges clearen




1. Gewichten von vorne nacht hinten in cols + gewichte für row
2. floodfill

'''

class Logic(IClientHandler):
    game_state: GameState

    # this method is called every time the server is requesting a new move
    # this method should always be implemented otherwise the client will be disqualified
    def calculate_move(self) -> Move:
        logging.info("Calculate move...")
        possible_moves: List[Move] = self.game_state.possible_moves()
        
        return possible_moves[random.randint(0, len(possible_moves) - 1)]

    # this method is called every time the server has sent a new game state update
    # this method should be implemented to keep the game state up to date
    def on_update(self, state: GameState):
        self.game_state = state


if __name__ == "__main__":
    Starter(logic=Logic())
    # if u wanna have more insights, u can set the logging level to debug:
    # Starter(logic=Logic(), log_level=logging.DEBUG)