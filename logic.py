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
    graph: nx.DiGraph
    maxSegments: int
    
    def __init__(self):
        
        self.G = nx.DiGraph()
        self.maxSegments = 0
        self.directionVectors = [
            CubeCoordinates(1, 0),  #-1     Right -> Clockwise
            CubeCoordinates(0, 1),  #-1
            CubeCoordinates(-1, 1), #0
            CubeCoordinates(-1, 0), #1
            CubeCoordinates(0, -1), #1
            CubeCoordinates(1, -1)  #0
        ]

    def add_nodes(self, thisSegment: Segment): 
        base = thisSegment.center.plus(thisSegment.direction.opposite().vector())
        for i in range(4):
            up = thisSegment.direction.rotated_by(-2)
            for u in range(2):
                cube = base.plus(up.vector().times(2 - u))
                node = ';'.join(str(x) for x in cube.coordinates())
                self.G.add_node(node, field_type=thisSegment.fields[i][u].field_type, stream=False)
                #print(node)



            cube = base
            node = ';'.join(str(x) for x in cube.coordinates())
            self.G.add_node(node, field_type=thisSegment.fields[i][2].field_type, stream=True)
            #print(node)



            down = thisSegment.direction.rotated_by(2)
            for d in range(2):
                cube = base.plus(down.vector().times(d+1))
                node = ';'.join(str(x) for x in cube.coordinates())
                self.G.add_node(node, field_type=thisSegment.fields[i][3 + d].field_type, stream=False)
                #print(node)

            base = base.plus(thisSegment.direction.vector())
            #print()

        #print('--------\n\n')

    # this method is called every time the server is requesting a new move
    # this method should always be implemented otherwise the client will be disqualified
    def calculate_move(self) -> Move:
        logging.info("Calculate move...")
        #possible_moves: List[Move] = self.game_state.possible_moves()

        segments = self.game_state.board.segments
        newSegment = False
        while self.maxSegments < len(segments):
            self.maxSegments += 1
            newSegment = True

            thisSegment = segments[self.maxSegments - 1]

            self.add_nodes(thisSegment)


        if newSegment:
            # reset distances
            for n in self.G.nodes:
                self.G.nodes[n]['distance'] = 9999

            # set distances
            unvisited = list(self.G.nodes).copy()

            # set start            
            lastSegment = self.game_state.board.segments[-1]
            for n in range(5):
                lastCenter = lastSegment.center.plus(self.game_state.board.next_direction.vector().times(2))
                up = self.game_state.board.next_direction.rotated_by(-2)
                for u in range(2):
                    cube = lastCenter.plus(up.vector().times(2 - u))
                    node = ';'.join(str(x) for x in cube.coordinates())
                    self.G.nodes[node]['distance'] = 0

                cube = lastCenter
                node = ';'.join(str(x) for x in cube.coordinates())
                self.G.nodes[node]['distance'] = 0

                down = self.game_state.board.next_direction.rotated_by(2)
                for d in range(2):
                    cube = lastCenter.plus(down.vector().times(d+1))
                    node = ';'.join(str(x) for x in cube.coordinates())
                    self.G.nodes[node]['distance'] = 0

            # search
            while len(unvisited) > 0:
                #print(unvisited)
                smallestIndex = None
                smallestNode = None
                smallestDistance = 999999
                for u in range(len(unvisited)):
                    if self.G.nodes[unvisited[u]]['distance'] < smallestDistance:
                        smallestIndex = u
                        smallestNode = unvisited[u]
                        smallestDistance = self.G.nodes[unvisited[u]]['distance']
                
                #print(smallestIndex, smallestNode, smallestDistance)

                unvisited.pop(smallestIndex)



                smallestNodeCoords = smallestNode.split(';')
                smallestNodeCube = CubeCoordinates(int(smallestNodeCoords[0]), int(smallestNodeCoords[1]))
                for v in self.directionVectors:
                    neighborCube = smallestNodeCube.plus(v)
                    neighborNode = ';'.join(str(x) for x in neighborCube.coordinates())

                    #print(neighborCube)


                    try:
                        test = self.G.nodes[neighborNode] # for triggering try
                        #print(test)

                        if neighborNode in unvisited:
                            if self.G.nodes[neighborNode]['field_type'] != FieldType.Water and self.G.nodes[neighborNode]['field_type'] != FieldType.Goal:
                                unvisited.pop(unvisited.index(neighborNode))
                                #print('land')
                                continue

                            if self.G.nodes[neighborNode]['distance'] > self.G.nodes[smallestNode]['distance'] + 1:
                                #print("relaxed to", self.G.nodes[smallestNode]['distance'] + 1)
                                self.G.nodes[neighborNode]['distance'] = self.G.nodes[smallestNode]['distance'] + 1

                    except:
                        #print("out of bounds")
                        continue
        
                #print('----\n')


        print(self.G.nodes.data('distance'))
        print(len(list(self.G.nodes.data('distance'))))

        testmove = Move(actions=[Advance(1)])
        
        return testmove
        return possible_moves[random.randint(0, len(possible_moves) - 1)]

    # this method is called every time the server has sent a new game state update
    # this method should be implemented to keep the game state up to date
    def on_update(self, state: GameState):
        self.game_state = state


if __name__ == "__main__":
    Starter(logic=Logic())
    # if u wanna have more insights, u can set the logging level to debug:
    # Starter(logic=Logic(), log_level=logging.DEBUG)