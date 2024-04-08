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

#############
## TO DO
## Choose between goal and idle mode (at end)
## Idle => drive in circle
## Speedy Moves
## First Speedy then passengers?

class Logic(IClientHandler):
    game_state: GameState
    graph: nx.DiGraph
    maxSegments: int
    tree: List[CubeDirection]
    directionVectors: List[CubeCoordinates]
    directions: List[CubeDirection]
    passengerNodes = List[List] # str, CubeCoordinates, bool
    
    def __init__(self):
        
        self.G = nx.DiGraph()
        self.maxSegments = 0
        self.lastTimeAcc = 0
        self.totalTurns = 0
        self.totalAdv = 0
        self.tree: List[CubeDirection] = []
        self.idle = False
        self.passengerNodes = []
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
                field_type = thisSegment.fields[i][u].field_type
                passengerDirection = None
                if field_type == FieldType.Passenger:
                    passengerDirection = thisSegment.fields[i][u].passenger.direction
                    self.passengerNodes.append([node, cube, True])
                self.G.add_node(node, field_type=field_type, passengerDirection=passengerDirection, speed=None, stream=stream, segment=self.maxSegments - 1, direction=None)
                #print(node)



            cube = base
            node = ';'.join(str(x) for x in cube.coordinates())
            stream = self.game_state.board.does_field_have_stream(cube)
            field_type = thisSegment.fields[i][2].field_type
            passengerDirection = None
            if field_type == FieldType.Passenger:
                passengerDirection = thisSegment.fields[i][2].passenger.direction
                self.passengerNodes.append([node, cube, True])
            self.G.add_node(node, field_type=field_type, passengerDirection=passengerDirection, speed=None, stream=stream, segment=self.maxSegments - 1, direction=None)
            #print(node)



            down = thisSegment.direction.rotated_by(2)
            for d in range(2):
                cube = base.plus(down.vector().times(d+1))
                node = ';'.join(str(x) for x in cube.coordinates())
                stream = self.game_state.board.does_field_have_stream(cube)
                field_type = thisSegment.fields[i][3 + d].field_type
                passengerDirection = None
                if field_type == FieldType.Passenger:
                    passengerDirection = thisSegment.fields[i][3 + d].passenger.direction
                    self.passengerNodes.append([node, cube, True])
                self.G.add_node(node, field_type=field_type, passengerDirection=passengerDirection, speed=None, stream=stream, segment=self.maxSegments - 1, direction=None)
                #print(node)

            base = base.plus(thisSegment.direction.vector())
            #print()

            for n in self.G.nodes:
                cube = CubeCoordinates(int(n.split(';')[0]), int(n.split(';')[1]))
                self.G.nodes[n]['dock'] = False
                for v in self.directions:
                    v_n = ';'.join(str(x) for x in cube.plus(v.vector()).coordinates())
                    try:
                        if self.G.nodes[v_n]['field_type'] == FieldType.Passenger and self.G.nodes[v_n]['passengerDirection'] == v.opposite():
                            self.G.nodes[n]['dock'] = True

                            break
                    except:
                        pass

                if self.G.nodes[n]['dock'] == True or self.G.nodes[n]['field_type'] == FieldType.Goal:
                    speed = 1
                    if self.G.nodes[n]['stream'] == True:
                        speed += 1
                    self.G.nodes[n]['speed'] = speed

        #print('--------\n\n')
            
    def setDistances(self):

        # reset distances
        for n in self.G.nodes:
            self.G.nodes[n]['distance'] = 9999999999
            self.G.nodes[n]['direction'] = None

        # set distances
        unvisited = list(self.G.nodes).copy()

        # set start
        lastSegment = self.game_state.board.segments[-1]
        lastCenter = lastSegment.center.plus(self.game_state.board.next_direction.vector().times(2))
        up = self.game_state.board.next_direction.rotated_by(-2)
        for u in range(2):
            cube = lastCenter.plus(up.vector().times(2 - u))
            node = ';'.join(str(x) for x in cube.coordinates())
            if self.G.nodes[node]['field_type'] == FieldType.Water or self.G.nodes[node]['field_type'] == FieldType.Goal:
                if self.maxSegments < 8 or u == 1: # if no goal on map or goal on map and field is goal else: goal on map field is no goal and dijkstra magic
                    self.G.nodes[node]['distance'] = 0
                    self.G.nodes[node]['direction'] = self.game_state.board.next_direction
                else:
                    pass
            else:
                pass

        cube = lastCenter
        node = ';'.join(str(x) for x in cube.coordinates())
        if self.G.nodes[node]['field_type'] == FieldType.Water or self.G.nodes[node]['field_type'] == FieldType.Goal:
            self.G.nodes[node]['distance'] = 0
            self.G.nodes[node]['direction'] = self.game_state.board.next_direction
        else:
            pass

        down = self.game_state.board.next_direction.rotated_by(2)
        for d in range(2):
            cube = lastCenter.plus(down.vector().times(d+1))
            node = ';'.join(str(x) for x in cube.coordinates())
            if self.G.nodes[node]['field_type'] == FieldType.Water or self.G.nodes[node]['field_type'] == FieldType.Goal:
                if self.maxSegments < 8 or d == 0:
                    self.G.nodes[node]['distance'] = 0
                    self.G.nodes[node]['direction'] = self.game_state.board.next_direction
                else:
                    pass
            else:
                pass

        # dijkstra relaxing stuff
        while len(unvisited) > 0:
            #print(unvisited)
            smallestIndex = None
            smallestNode = None
            smallestDistance = 999999999999
            for u in range(len(unvisited)):
                if self.G.nodes[unvisited[u]]['distance'] < smallestDistance:
                    smallestIndex = u
                    smallestNode = unvisited[u]
                    smallestDistance = self.G.nodes[unvisited[u]]['distance']
            
            #print(smallestIndex, smallestNode, smallestDistance)

            unvisited.pop(smallestIndex)

            smallestNodeCoords = smallestNode.split(';')
            smallestNodeCube = CubeCoordinates(int(smallestNodeCoords[0]), int(smallestNodeCoords[1]))
            for v in self.directions:
                neighborCube = smallestNodeCube.plus(v.vector())
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

                        flow = v.opposite()

                        dockMulti = 1
                        if self.game_state.current_ship.passengers < 2: # if need for passengers
                            if self.G.nodes[neighborNode]['dock'] == True:
                                dockMulti = 0.5

                        newWeight = round((self.G.nodes[smallestNode]['distance'] + 1) * (abs(flow.turn_count_to(self.G.nodes[smallestNode]['direction'])) + 1) * dockMulti)

                        if self.G.nodes[neighborNode]['distance'] > newWeight:
                            #print("relaxed to", self.G.nodes[smallestNode]['distance'] + 1)
                            self.G.nodes[neighborNode]['distance'] = newWeight
                            self.G.nodes[neighborNode]['direction'] = flow


                except:
                    #print("out of bounds")
                    continue
    
            #print('----\n')

    def updatePassAndDocks(self):
        
        for p in self.passengerNodes:
            if p[2] == False:
                continue

            if self.game_state.board.get(p[1]).passenger.passenger == 0:
                dock = p[1].plus(self.G.nodes[p[0]]['passengerDirection'].vector())
                dockNode = ';'.join(str(x) for x in dock.coordinates())
                self.G.nodes[dockNode]['dock'] = False
                self.G.nodes[p[0]]['passengerDirection'] = None
                p[2] = False


    def buildTree(self):
        
        self.tree = []
        lastCube = self.position
        globalbestNode = ';'.join(str(x) for x in self.position.coordinates())
        globalbestDistance = 999999999999
        maxloop = 300
        loop = 0
        while globalbestDistance > 0 and loop < maxloop:
            loop+=1
            nodeDirection = self.G.nodes[';'.join(str(x) for x in lastCube.coordinates())]['direction']
            lastCube = lastCube.plus(nodeDirection.vector())
            try:
                globalbestNode = ';'.join(str(x) for x in lastCube.coordinates())
                globalbestDistance = self.G.nodes[globalbestNode]['distance']
                self.tree.append(nodeDirection)
            except:
                break

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
####HELPHELPHELP BUGGYY???
        if self.direction != self.tree[0]:
            actions.append(Turn(self.tree[0]))
            self.totalTurns += 1

        actions.append(Advance(advancement))
        self.totalAdv += 1

# push to highest weight field lol
        if push:
            worstDistance = -1 # higest weight => push enemy to that field
            worstDirection = None
            for v in range(6):

                my = ';'.join(str(x) for x in self.position.coordinates())
                pushother = ';'.join(str(x) for x in self.game_state.other_ship.position.plus(self.directionVectors[v]).coordinates())
                try:
                    if self.G.nodes[pushother]['field_type'] == FieldType.Water and my != pushother:
                        if self.G.nodes[pushother]['distance'] > worstDistance:
                            worstDistance = self.G.nodes[pushother]['distance']
                            worstDirection = self.directions[v]
                except:
                    pass

            actions.append(Push(worstDirection))

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
        logging.info("\n\n\n\n")
        logging.info("Calculate move...")
        logging.info(self.game_state.turn)
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

        
        if self.playerSegmentIndex == 7 and self.game_state.current_ship.passengers < 2 and self.idle == False:
            self.idle = True
        
        if self.idle == False:
            print('goal')
        else:
            print('idle')
        print(self.game_state.current_ship.passengers)

        self.updatePassAndDocks()

        if (self.idle == False):
            self.setDistances()

            #logging.info(self.G.nodes.data('distance'))
            #logging.info(self.G.nodes.data('direction'))
            graphstr = str(self.G.nodes.data()).replace('::', '.')
            logging.info(graphstr)
            logging.info("")

            self.buildTree()
            logging.info(self.tree)
            logging.info("")

            move = self.treeToMove()
        else:

            ## ToDo
            ## Das funktioniert hier an sich, ist aber nicht wirklich reliable
            ## fährt in die falsche richtung und so
            ## plan:
            ## possible turns (turn distance < 2)
            ## perform action
            ## advance(1)
            ## perform action
            ## recursively
            ## depth == 10 or so
            ## stay on segment 8
            ## generate tree (as known) -> movetotree()

            moves = self.game_state.possible_action_comb(self.game_state, [], 0, 2)
            print(moves)
            move = Move(moves[0])


        #self.treeToMoveSpeed(self.position, self.direction, self.game_state.current_ship.speed, self.game_state.current_ship.coal, 0)

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