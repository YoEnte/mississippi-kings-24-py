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

class Logic(IClientHandler):
    game_state: GameState
    graph: nx.DiGraph
    maxSegments: int
    tree: List[CubeDirection]
    
    def __init__(self):
        
        self.G = nx.DiGraph()
        self.maxSegments = 0
        self.lastTimeAcc = 0
        self.totalTurns = 0
        self.totalAdv = 0
        self.tree = []
        self.directionVectors = [
            CubeCoordinates(1, 0),  #-1     Right -> Clockwise
            CubeCoordinates(0, 1),  #-1
            CubeCoordinates(-1, 1), #0
            CubeCoordinates(-1, 0), #1
            CubeCoordinates(0, -1), #1
            CubeCoordinates(1, -1)  #0
        ]

        self.directions = [                 # Right -> Clockwise
            CubeDirection.Right,
            CubeDirection.DownRight,
            CubeDirection.DownLeft,
            CubeDirection.Left,
            CubeDirection.UpLeft,
            CubeDirection.UpRight
        ]

    def add_nodes(self, thisSegment: Segment): 
        base = thisSegment.center.plus(thisSegment.direction.opposite().vector())
        for i in range(4):
            up = thisSegment.direction.rotated_by(-2)
            for u in range(2):
                cube = base.plus(up.vector().times(2 - u))
                node = ';'.join(str(x) for x in cube.coordinates())
                stream = self.game_state.board.does_field_have_stream(cube)
                self.G.add_node(node, field_type=thisSegment.fields[i][u].field_type, stream=stream, segment=self.maxSegments - 1)
                #print(node)



            cube = base
            node = ';'.join(str(x) for x in cube.coordinates())
            stream = self.game_state.board.does_field_have_stream(cube)
            self.G.add_node(node, field_type=thisSegment.fields[i][2].field_type, stream=stream, segment=self.maxSegments - 1)
            #print(node)



            down = thisSegment.direction.rotated_by(2)
            for d in range(2):
                cube = base.plus(down.vector().times(d+1))
                node = ';'.join(str(x) for x in cube.coordinates())
                stream = self.game_state.board.does_field_have_stream(cube)
                self.G.add_node(node, field_type=thisSegment.fields[i][3 + d].field_type, stream=stream, segment=self.maxSegments - 1)
                #print(node)

            base = base.plus(thisSegment.direction.vector())
            #print()

        #print('--------\n\n')
            
    def setDistances(self):

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
                if self.G.nodes[node]['field_type'] == FieldType.Water or self.G.nodes[node]['field_type'] == FieldType.Goal:
                    self.G.nodes[node]['distance'] = 1-u
                else:
                    pass

            cube = lastCenter
            node = ';'.join(str(x) for x in cube.coordinates())
            if self.G.nodes[node]['field_type'] == FieldType.Water or self.G.nodes[node]['field_type'] == FieldType.Goal:
                self.G.nodes[node]['distance'] = 0
            else:
                pass

            down = self.game_state.board.next_direction.rotated_by(2)
            for d in range(2):
                cube = lastCenter.plus(down.vector().times(d+1))
                node = ';'.join(str(x) for x in cube.coordinates())
                if self.G.nodes[node]['field_type'] == FieldType.Water or self.G.nodes[node]['field_type'] == FieldType.Goal:
                    self.G.nodes[node]['distance'] = d
                else:
                    pass

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

                        weight = 0
                        if self.G.nodes[neighborNode]['stream'] == False:
                            weight += 1
                        else:
                            weight += 4

                        if self.G.nodes[neighborNode]['distance'] > self.G.nodes[smallestNode]['distance'] + weight:
                            #print("relaxed to", self.G.nodes[smallestNode]['distance'] + 1)
                            self.G.nodes[neighborNode]['distance'] = self.G.nodes[smallestNode]['distance'] + weight

                except:
                    #print("out of bounds")
                    continue
    
            #print('----\n')
                
    def buildTree(self):
        # shortest path        
        self.tree = []
        lastCube = self.position
        globalbestNode = 999999

        while globalbestNode > 0:
            localBestNode = 999999
            d = self.directions.index(self.segmentDirection)

            for i in range(6):
                if d > 5:
                    d = 0

                searchCubeVector = self.directionVectors[d]
                searchDirection = self.directions[d]
                nextCube = lastCube.plus(searchCubeVector)

                try:
                    test = self.G.nodes[';'.join(str(x) for x in nextCube.coordinates())] # filter key error
                except:
                    d += 1
                    continue

                if self.G.nodes[';'.join(str(x) for x in nextCube.coordinates())]['distance'] < localBestNode:
                    localBestCube = nextCube
                    localBestDirection = searchDirection
                    localBestNode = self.G.nodes[';'.join(str(x) for x in nextCube.coordinates())]['distance']
            
                #print(d, localBestNode, globalbestNode, searchDirection)
                d += 1


            if localBestNode < globalbestNode:
                globalbestNode = localBestNode
                lastCube = localBestCube

            self.tree.append(localBestDirection)

    def treeToMove(self) -> Move:
        acceleration = 0
        advancement = 1

        if self.lastTimeAcc > 0:
            acceleration -= self.lastTimeAcc
            self.lastTimeAcc = 0

        if self.game_state.board.does_field_have_stream(self.position.plus(self.tree[0].vector())) == True:
            acceleration += 1
            self.lastTimeAcc += 1

        push = False
        my = ';'.join(str(x) for x in self.position.plus(self.tree[0].vector()).coordinates())
        other = ';'.join(str(x) for x in self.game_state.other_ship.position.coordinates())
        if my == other:
            acceleration += 1
            self.lastTimeAcc += 1
            push = True

        actions = []

        if acceleration != 0:
            actions.append(Accelerate(acceleration))

        if self.direction != self.tree[0]:
            actions.append(Turn(self.tree[0]))
            self.totalTurns += 1

        actions.append(Advance(advancement))
        self.totalAdv += 1

        if push:
            v = self.directions.index(self.segmentDirection.opposite().rotated_by(-1))
            for i in range(6):
                if v > 5:
                    v = 0

                my = ';'.join(str(x) for x in self.position.coordinates())
                pushother = ';'.join(str(x) for x in self.game_state.other_ship.position.plus(self.directionVectors[v]).coordinates())
                try:
                    test = self.G.nodes[pushother] # filter out of bounds
                except:
                    v += 1
                    continue

                if self.G.nodes[pushother]['field_type'] == FieldType.Water and my != pushother:
                    actions.append(Push(self.directions[v]))
                    break

                v += 1

        #print(self.totalAdv, self.totalTurns)

        return Move(actions=actions)
    
    def treeToMoveSpeed(self, position: CubeCoordinates, direction: CubeDirection, speed: int, coal: int, steps: int):

        maxSpeedCoal = min(1, coal)
        maxTurnCoal = min(1, coal)
        
        maxSpeed = 4
        minSpeed = 1

        possibleSpeeds = []
        for m in range(maxSpeedCoal + 1):
            if speed - (m + 1) >= minSpeed:
                possibleSpeeds.append(speed - (m + 1))

        possibleSpeeds.append(speed)

        for p in range(maxSpeedCoal + 1):
            if speed + (p + 1) <= maxSpeed:
                possibleSpeeds.append(speed + (p + 1))

        print(speed, possibleSpeeds)

        for s in possibleSpeeds:
            accelation = Accelerate(s - speed)
            localCoal = coal - (abs(s - speed) - 1)
            for i in range(s):
                
                # if stream or push:
                    # x-2
                # else
                    # x-1
                
                # step+1
                # position += direction
                # direction = tree[step]

                # if x > 0:
                    # go on
                # elif x == 0:
                    # recursion
                # else:
                    # aua
                
                
                pass

    def hashCube(self, position: CubeCoordinates) -> str:
        pass

    def unhashCube(self, position: str) -> CubeCoordinates:
        pass

    # this method is called every time the server is requesting a new move
    # this method should always be implemented otherwise the client will be disqualified
    def calculate_move(self) -> Move:
        logging.info("Calculate move...")
        #possible_moves: List[Move] = self.game_state.possible_moves()
        
        self.position = self.game_state.current_ship.position
        self.direction = self.game_state.current_ship.direction
        self.playerSegmentIndex = self.game_state.board.segment_with_index_at(self.position)[0]
        self.playerSegment = self.game_state.board.segment_with_index_at(self.position)[1]
        self.segmentDirection = self.playerSegment.direction
        self.nextDirection = self.game_state.board.next_direction

        segments = self.game_state.board.segments
        newSegment = False
        while self.maxSegments < len(segments):
            self.maxSegments += 1
            newSegment = True

            thisSegment = segments[self.maxSegments - 1]

            self.add_nodes(thisSegment)


        if newSegment:
            self.setDistances()

        #print(self.G.nodes.data('distance'))
        #print(len(list(self.G.nodes.data('distance'))))

        self.buildTree()
        print(self.tree)

        move = self.treeToMove()

        self.treeToMoveSpeed(self.position, self.direction, self.game_state.current_ship.speed, self.game_state.current_ship.coal, 0)

        return move
        return possible_moves[random.randint(0, len(possible_moves) - 1)]

    # this method is called every time the server has sent a new game state update
    # this method should be implemented to keep the game state up to date
    def on_update(self, state: GameState):
        self.game_state = state


if __name__ == "__main__":
    Starter(logic=Logic())
    # if u wanna have more insights, u can set the logging level to debug:
    # Starter(logic=Logic(), log_level=logging.DEBUG)