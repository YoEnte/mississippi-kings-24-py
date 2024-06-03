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
import math
import json
import socket
from datetime import datetime

## fields   -> SoCha Fields
## nodes    -> graph key
## cubes    -> CubeCoordinates
##
## speed    -> ship speed needed
## step     -> single steps needed
## distance -> dtistance (can have evals etc)

class MyEncoder(json.JSONEncoder):
    def default(self, o):
        return str(o).replace('CubeDirection::', '').replace('FieldType.', '').replace('TeamEnum.', '')

class Logic(IClientHandler):
    game_state: GameState

    def __init__(self):

        self.G = nx.DiGraph()
        self.maxSegments = 0
        self.me: Ship
        self.infinite = 999999999999
        self.startTimeString = f"{datetime.now():%Y-%m-%dT%H:%M:%SM%f}"[:-3]
        
        self.directionList = [                 # Right -> Clockwise
            CubeDirection.Right,
            CubeDirection.DownRight,
            CubeDirection.DownLeft,
            CubeDirection.Left,
            CubeDirection.UpLeft,
            CubeDirection.UpRight
        ]
        self.directionVectorList = [
            CubeCoordinates(1, 0),  #-1     Right -> Clockwise
            CubeCoordinates(0, 1),  #-1
            CubeCoordinates(-1, 1), #0
            CubeCoordinates(-1, 0), #1
            CubeCoordinates(0, -1), #1
            CubeCoordinates(1, -1)  #0
        ]

        self.needToBeDock = []

    def buildGraph(self, segmentIndex):
        segment = self.game_state.board.segments[segmentIndex]
        base = segment.center.plus(segment.direction.opposite().vector())
        for col in range(4):
            cubes = []

            cubes += [[base.plus(segment.direction.rotated_by(-2).vector().times(2 - u)), u] for u in range(2)]
            cubes += [[base, 2]]
            cubes += [[base.plus(segment.direction.rotated_by(2).vector().times(d + 1)), d + 3] for d in range(2)]

            # add column of cubes to graph
            for cube, row in cubes:
                node = ';'.join(str(x) for x in cube.coordinates())
                hasStream = self.game_state.board.does_field_have_stream(cube)
                field_type = segment.fields[col][row].field_type

                if field_type == FieldType.Passenger:
                    passengerDirection = segment.fields[col][row].passenger.direction
                    dockCube = cube.plus(passengerDirection.vector())
                    self.needToBeDock.append([';'.join(str(x) for x in dockCube.coordinates()), False])

                # add nodes
                self.G.add_node(
                    node,
                    fieldType=field_type,
                    hasStream=hasStream,
                    segment=segmentIndex,
                    dock=False
                )
                
                # add docks
                for d in self.needToBeDock:
                    if d[1] == True:
                        continue

                    try:
                        if self.G.nodes[d[0]]['fieldType'] == FieldType.Water or self.G.nodes[d[0]]['fieldType'] == FieldType.Goal:
                            self.G.nodes[d[0]]['dock'] = True
                            d[1] = True
                    except:
                        pass

            base = base.plus(segment.direction.vector())

    def setStarts(self):
        
        starts = {
            'next': {
                'startNodes': [],
                'startDirections': [],
                'rotationMulti': 2,
                'startInt': 0,
                'mirroredDirections': False
            },
            'start': {
                'startNodes': [],
                'startDirections': [CubeDirection.Left],
                'rotationMulti': 2,
                'startInt': 0,
                'mirroredDirections': False
            },
            'me': {
                'startNodes': [';'.join(str(x) for x in self.me.position.coordinates())],
                'startDirections': [self.me.direction.opposite()],
                'rotationMulti': 2,
                'startInt': 0,
                'mirroredDirections': False
            }
        }

        ## next
        lastSegment = self.game_state.board.segments[-1]
        lastCenter = lastSegment.center.plus(self.game_state.board.next_direction.vector().times(2))
        cubes = []
        cubes += [[lastCenter.plus(self.game_state.board.next_direction.rotated_by(-2).vector().times(2 - u)), u] for u in range(2)]
        cubes += [[lastCenter, 2]]
        cubes += [[lastCenter.plus(self.game_state.board.next_direction.rotated_by(2).vector().times(d + 1)), d + 3] for d in range(2)]

        for cube, row in cubes:
            node = ';'.join(str(x) for x in cube.coordinates())
            if self.G.nodes[node]['fieldType'] == FieldType.Water or self.G.nodes[node]['fieldType'] == FieldType.Goal:
                if self.maxSegments < 8 or row >= 1 or row <= 3: # if no goal on map or goal on map and field is goal else: goal on map field is no goal and dijkstra magic
                    starts['next']['startNodes'].append(node)
                    starts['next']['startDirections'].append(self.game_state.board.next_direction)

        ## start
        if self.me.team == TeamEnum.One:
            starts['start']['startNodes'].append('-1;-1;2')
        else:
            starts['start']['startNodes'].append('2;-1;-1')

        return starts

    def setDistances(self, starts: dict[dict]):

        for key, items in starts.items():
            
            distanceTag = key + 'Distance'
            directionTag = key + 'Direction'

            # reset distances
            for n in self.G.nodes:
                self.G.nodes[n][distanceTag] = self.infinite
                self.G.nodes[n][directionTag] = None

                if n in items['startNodes']:
                    self.G.nodes[n][distanceTag] = items['startInt']
                    self.G.nodes[n][directionTag] = items['startDirections'][items['startNodes'].index(n)]

            
            unvisited = list(self.G.nodes).copy()
            # dijkstra relaxing stuff
            while len(unvisited) > 0:
                #print(unvisited)
                smallestIndex = None
                smallestNode = None
                smallestDistance = self.infinite + 1
                for u in range(len(unvisited)):
                    if self.G.nodes[unvisited[u]][distanceTag] < smallestDistance:
                        smallestIndex = u
                        smallestNode = unvisited[u]
                        smallestDistance = self.G.nodes[unvisited[u]][distanceTag]
                
                #print(smallestIndex, smallestNode, smallestDistance)

                unvisited.pop(smallestIndex)

                smallestNodeCoords = smallestNode.split(';')
                smallestNodeCube = CubeCoordinates(int(smallestNodeCoords[0]), int(smallestNodeCoords[1]))
                for v in self.directionList:
                    neighborCube = smallestNodeCube.plus(v.vector())
                    neighborNode = ';'.join(str(x) for x in neighborCube.coordinates())

                    #print(neighborCube)


                    try:
                        test = self.G.nodes[neighborNode] # for triggering try
                        #print(test)

                        if neighborNode in unvisited:
                            if self.G.nodes[neighborNode]['fieldType'] != FieldType.Water and self.G.nodes[neighborNode]['fieldType'] != FieldType.Goal:
                                unvisited.pop(unvisited.index(neighborNode))
                                #print('land')
                                continue
                            
                            if items['mirroredDirections'] == True:
                                flow = v
                            else:
                                flow = v.opposite()

                            newWeight = (self.G.nodes[smallestNode][distanceTag] + 1) * (abs(flow.turn_count_to(self.G.nodes[smallestNode][directionTag])) + 1)

                            if newWeight < self.G.nodes[neighborNode][distanceTag]:
                                #print("relaxed to", self.G.nodes[smallestNode]['distance'] + 1)
                                self.G.nodes[neighborNode][distanceTag] = newWeight
                                self.G.nodes[neighborNode][directionTag] = flow


                            # neighbors unvisted machen wenn relax???

                    except:
                        #print("out of bounds")
                        continue

    def calcScores(self):

        for n in self.G.nodes:
            self.G.nodes[n]['distanceScore']    = self.G.nodes[n]['startDistance'] / (self.G.nodes[n]['meDistance'] + self.G.nodes[n]['nextDistance'])
            if self.G.nodes[n]['dock'] == False:
                self.G.nodes[n]['dockScore']    = self.G.nodes[n]['startDistance'] / (self.G.nodes[n]['meDistance'] + self.G.nodes[n]['nextDistance'])
            else:
                self.G.nodes[n]['dockScore']    = self.G.nodes[n]['startDistance'] / ((self.G.nodes[n]['meDistance'] / 10 ) + self.G.nodes[n]['nextDistance'])

        self.sortedGraph        = sorted(self.G.nodes.data(), key=lambda x: (-x[1]['distanceScore'], x[1]['meDistance']))[0:10]
        self.sortedGraphDock    = sorted(self.G.nodes.data(), key=lambda x: (-x[1]['dockScore'], x[1]['meDistance']))[0:10]

    def randomMove(self):
        
        possible_moves: List[Move] = self.game_state.possible_moves()
        return possible_moves[random.randint(0, len(possible_moves) - 1)]

    def printGraph(self, console, useLogging, sendToServer):
        self.turnData = {
            "turn": self.game_state.turn,
            "player": self.game_state.current_ship.team,
            "time": self.startTimeString,
            "currentShip": {
                "coords": ';'.join(str(x) for x in self.game_state.current_ship.position.coordinates())
            },
            "otherShip": {
                "coords": ';'.join(str(x) for x in self.game_state.other_ship.position.coordinates())
            },
            "data": list(self.G.nodes.data()),
            "sortedGraph": self.sortedGraph,
            "sortedGraphDock": self.sortedGraphDock,
        }
        self.turnString = json.dumps(self.turnData, cls=MyEncoder)

        if console:
            if useLogging:
                logging.info(self.turnString)
                logging.info("\n\n")
            else:
                print(self.turnString)
                print("\n\n")

        if sendToServer:
            self.sendUDP('192.168.178.234', 30001)
        

    def sendUDP(self, host, port):

        turnBytes = str.encode(self.turnString)
        server = (host, port)
        UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        UDPClientSocket.sendto(turnBytes, server)

    def calculate_move(self) -> Move:
        # basic stuff
        logging.info("\n\n")
        logging.info("Calculate move...")

        # set turn variables
        self.me = self.game_state.current_ship

        # add segments / fields to graph
        self.segmentsAdded = 0
        while self.maxSegments < len(self.game_state.board.segments):

            self.buildGraph(self.maxSegments)

            self.maxSegments += 1
            self.segmentsAdded += 1

        self.setDistances(self.setStarts())
        self.calcScores()

        self.printGraph(console=False, useLogging=False, sendToServer=True)

        # send move        
        #move = self.randomMove()
        move = Move([Advance(1)])
        return move

    def on_update(self, state: GameState):
        self.game_state = state

if __name__ == "__main__":
    Starter(logic=Logic())
    # if u wanna have more insights, u can set the logging level to debug:
    # Starter(logic=Logic(), log_level=logging.DEBUG)