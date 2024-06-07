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
        self.lastTimeAcc = 0
        self.passengers = 0
        self.depth = 5
        
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

        self.needToBeDock = []      # cube, node, is added bool
        self.passengerFields = []   # cube, node, has passenger
        
        self.cubeMap = []
        self.directionMap = []
        self.mustSpeedMap = []
        self.rotationCountMap = []

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
                passengerDirection = None
                speed = 0

                if field_type == FieldType.Passenger:
                    passengerDirection = segment.fields[col][row].passenger.direction
                    dockCube = cube.plus(passengerDirection.vector())
                    self.needToBeDock.append([dockCube, ';'.join(str(x) for x in dockCube.coordinates()), False])
                    self.passengerFields.append([cube, node, True])

                if field_type == FieldType.Goal:
                    speed = 1

                    if hasStream == True:
                        speed = 2

                # add nodes
                self.G.add_node(
                    node,
                    fieldType=field_type,
                    hasStream=hasStream,
                    segment=segmentIndex,
                    passengerDirection=passengerDirection,
                    dock=False,
                    speed=speed
                )
                
                # add docks
                for d in self.needToBeDock:
                    if d[2] == True:
                        continue

                    try:
                        if self.G.nodes[d[1]]['fieldType'] == FieldType.Water or self.G.nodes[d[1]]['fieldType'] == FieldType.Goal:
                            d[2] = True
                            self.G.nodes[d[1]]['dock'] = True
                            self.G.nodes[d[1]]['speed'] = 1
                            if self.G.nodes[d[1]]['hasStream'] == True:
                                self.G.nodes[d[1]]['speed'] = 2
                    except:
                        pass

            base = base.plus(segment.direction.vector())

    def setStarts(self):
        
        starts = {
            'next': {
                'startNodes': [],
                'startDirections': [],
                'rotationMulti': True,
                'startInt': 0,
                'mirroredDirections': False
            },
            'start': {
                'startNodes': [],
                'startDirections': [CubeDirection.Left],
                'rotationMulti': False,
                'startInt': 0,
                'mirroredDirections': False
            },
            'me': {
                'startNodes': [';'.join(str(x) for x in self.me.position.coordinates())],
                'startDirections': [self.me.direction.opposite()],
                'rotationMulti': True,
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
                if self.maxSegments < 8 or (row >= 1 and row <= 3): # if no goal on map or goal on map and field is goal else: goal on map field is no goal and dijkstra magic
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

                            rotationMulti = 1
                            if items['rotationMulti'] == True:
                                rotationMulti = (abs(flow.turn_count_to(self.G.nodes[smallestNode][directionTag])) + 1)

                            newWeight = (self.G.nodes[smallestNode][distanceTag] + 1) * rotationMulti

                            if newWeight < self.G.nodes[neighborNode][distanceTag]:
                                #print("relaxed to", self.G.nodes[smallestNode]['distance'] + 1)
                                self.G.nodes[neighborNode][distanceTag] = newWeight
                                self.G.nodes[neighborNode][directionTag] = flow


                            # neighbors unvisted machen wenn relax???

                    except:
                        #print("out of bounds")
                        continue
    
    def calcScores(self):

        '''
        for n in self.G.nodes:
            self.G.nodes[n]['distanceScore']    = self.G.nodes[n]['startDistance'] / (self.G.nodes[n]['meDistance'] + self.G.nodes[n]['nextDistance'])

            if self.G.nodes[n]['dock'] == False:
                self.G.nodes[n]['dockScore']    = self.G.nodes[n]['startDistance'] / (self.G.nodes[n]['meDistance'] + self.G.nodes[n]['nextDistance'])
            else:
                self.G.nodes[n]['dockScore']    = self.G.nodes[n]['startDistance'] / ((self.G.nodes[n]['meDistance'] / 10 ) + self.G.nodes[n]['nextDistance'])

        self.sortedGraph        = sorted(self.G.nodes.data(), key=lambda x: (-x[1]['distanceScore'], x[1]['meDistance']))[0:10]
        self.sortedGraphDock    = sorted(self.G.nodes.data(), key=lambda x: (-x[1]['dockScore'], x[1]['meDistance']))[0:10]'''

        for node in self.G.nodes:
            if self.G.nodes[node]['fieldType'] == FieldType.Island or self.G.nodes[node]['fieldType'] == FieldType.Passenger:
                self.G.nodes[node]['distanceScore'] = -self.infinite
                self.G.nodes[node]['dockScore'] = -self.infinite
                continue

            if node == ';'.join(str(x) for x in self.me.position.coordinates()):
                self.G.nodes[node]['distanceScore'] = -self.infinite
                self.G.nodes[node]['dockScore'] = -self.infinite
                continue

            s = self.G.nodes[node]['startDistance']
            m = self.G.nodes[node]['meDistance']
            n = self.G.nodes[node]['nextDistance']

            _s = (s / 9) ** 2
            _m = (m / 6) ** 2
            _n = (n / 3) ** 2

            
            self.G.nodes[node]['distanceScore'] = _s / (_m + _n)

            if self.passengers >= 2 and _n == 0:
                self.G.nodes[node]['dockScore'] = self.infinite
                continue

            if self.G.nodes[node]['dock'] == False:
                self.G.nodes[node]['dockScore'] = self.G.nodes[node]['distanceScore']
            else:
                self.G.nodes[node]['dockScore'] = (_s / (_m + _n)) * ((1 / _m) * 15)
            
            '''
            self.G.nodes[node]['distanceScore']  = _s - _m - _n

            if self.G.nodes[node]['dock'] == False or self.passengers >= 2:
                self.G.nodes[node]['dockScore'] = _s - _m - _n
            else:
                self.G.nodes[node]['dockScore'] = (_s - _m - _n) * (_m / 10)
            '''


        self.sortedGraph        = sorted(self.G.nodes.data(), key=lambda x: (-x[1]['distanceScore'], x[1]['meDistance']))[0:10]
        self.sortedGraphDock    = sorted(self.G.nodes.data(), key=lambda x: (-x[1]['dockScore'], x[1]['meDistance']))[0:10]
            

    def buildTree(self, index):

        destination = self.sortedGraphDock[index]
        node = destination[0]
        data = destination[1]

        nodeCoords = node.split(';')
        lastCube = CubeCoordinates(int(nodeCoords[0]), int(nodeCoords[1]))
        bestNode = node
        bestDistance = data['meDistance']

        self.cubeMap = []
        self.directionMap = []
        self.mustSpeedMap = []
        self.rotationCountMap = []

        while bestDistance > 0:
            self.cubeMap.insert(0, lastCube)

            lastNode = ';'.join(str(x) for x in lastCube.coordinates())
            nodeDirection = self.G.nodes[lastNode]['meDirection']
            self.directionMap.insert(0, nodeDirection.opposite())
            self.mustSpeedMap.insert(0, self.G.nodes[lastNode]['speed'])

            lastCube = lastCube.plus(nodeDirection.vector())

            bestNode = ';'.join(str(x) for x in lastCube.coordinates())
            bestDistance = self.G.nodes[bestNode]['meDistance']

        direction = self.me.direction
        for t in self.directionMap:
            self.rotationCountMap.append(abs(direction.turn_count_to(t)))
            direction = t

    def createMoveSlow(self):
        self.acceleration = 0

        if self.lastTimeAcc > 0:
            self.acceleration -= self.lastTimeAcc
            self.lastTimeAcc = 0

        if self.game_state.board.does_field_have_stream(self.me.position.plus(self.directionMap[0].vector())) == True:
            self.acceleration += 1
            self.lastTimeAcc += 1

        push = False
        my = ';'.join(str(x) for x in self.me.position.plus(self.directionMap[0].vector()).coordinates())
        other = ';'.join(str(x) for x in self.game_state.other_ship.position.coordinates())
        if my == other:
            self.acceleration += 1
            self.lastTimeAcc += 1
            push = True

        actions = []

        if self.acceleration != 0:
            actions.append(Accelerate(self.acceleration))
            
        if self.me.direction != self.directionMap[0]:
            actions.append(Turn(self.directionMap[0]))

        actions.append(Advance(1))

        # push to lowest dockScore lol
        if push:
            worstDistance = self.infinite # higest weight => push enemy to that field
            worstDirection = None
            for v in range(6):

                my = ';'.join(str(x) for x in self.me.position.coordinates())
                pushother = ';'.join(str(x) for x in self.game_state.other_ship.position.plus(self.directionVectorList[v]).coordinates())
                try:
                    if self.G.nodes[pushother]['fieldType'] == FieldType.Water and my != pushother:
                        if self.G.nodes[pushother]['dockScore'] < worstDistance:
                            worstDistance = self.G.nodes[pushother]['dockScore']
                            worstDirection = self.directionList[v]
                except:
                    pass

            actions.append(Push(worstDirection))

        return Move(actions=actions)
    
    def evalSpeed(self, distanceLeft, coal, speed, mustSpeed, depth, playerSegment, printStuff):

        turn = self.game_state.turn + (depth * 2)
        coalLoss = self.game_state.current_ship.coal - coal

        score = 0 # möglichst groß

        if printStuff:
            print(mustSpeed, speed)
        if mustSpeed == speed:
            score = self.infinite
        else:
            score += (self.depth - depth) * speed * 50

            if mustSpeed != 0:
                score = 0

            if self.passengers >= 2:
                score *= speed

        score *= 10 - distanceLeft

        score -= (self.depth - depth) * (coalLoss * 6) ** 3

        #score -= (depth ** 2) * 5

        #score -= max(0, 30 - turn) * (3 - depth) * (coalLoss ** 2) * 3

        #if playerSegment == self.maxSegments - 1 and distanceLeft - speed < 0:
            #score = 0

        score = math.ceil(score)

        return score

        # Tim hat eine Idee:
        # Spots, die man Speed (mit Kohle +-1 prunen) erreichen kann
        # Evaluaten lol -> Kohle und so wie vorher einbeziehen
    
    def createMoveFast(
            self,
            position: CubeCoordinates,
            direction: CubeDirection,
            speed: int,
            coal: int,
            depth: int,
            directionMap: List[CubeDirection],
            cubeMap: List[CubeCoordinates],
            rotationCountMap: List[int],
            mustSpeedMap: List[int],
            printStuff: bool
        ):

        if depth > self.depth or len(directionMap) == 0:
            node = ';'.join(str(x) for x in position.coordinates())
            mustSpeed = self.G.nodes[node]['speed']
            score = self.evalSpeed(len(directionMap), coal, speed, mustSpeed, depth, self.game_state.board.segment_index(position), printStuff)
            if printStuff:
                print('exit1', depth, len(directionMap), score)
            return score

        speedMap = []
        speedSumMap = []

        _position = position
        lastDirection = direction
        newStream = True
        for d in directionMap:
            speedMap.append(1)

            _position = _position.plus(d.vector())
            node = ';'.join(str(x) for x in _position.coordinates())

            try:
                test = self.G.nodes[node]['hasStream']
            except:
                continue

            # if this field is new Stream (set newStream for next field)
            # if now not on stream -> if next field stream it is 100% newStream
            if self.G.nodes[node]['hasStream'] == False:
                newStream = True
            
            # if on stream and direction change -> counts as new stream
            if self.G.nodes[node]['hasStream'] == True and lastDirection != d:
                newStream = True


            # if on newStream
            if self.G.nodes[node]['hasStream'] == True and newStream == True:
                newStream = False
                speedMap[-1] += 1

            # if push
            other = ';'.join(str(x) for x in self.game_state.other_ship.position.coordinates())
            if other == node:
                speedMap[-1] += 1
                newStream = True

            lastDirection = d

            if len(speedSumMap) == 0:
                lastOfTree = 0
            else:
                lastOfTree = speedSumMap[-1]

            speedSumMap.append(lastOfTree + speedMap[-1])

        
        minSpeed = 1
        maxSpeed = 4

        # select possible speeds
        possibleSpeeds: List[List] = []
        index = 0
        for s in range(minSpeed, maxSpeed + 1):

            if s in speedSumMap:
                possibleSpeeds.append([s, index])
                index += 1

        # calc coal
        newPossibleSpeeds = [] # speed, index in sumMap, coal, score
        for p in possibleSpeeds:
            accCoal = max(0, abs(speed - p[0]) - 1)
            rotationCoal = -1
            for i, r in enumerate(rotationCountMap):
                if i > p[1]:
                    break
                rotationCoal += r

            rotationCoal = max(0, rotationCoal)

            totalCoal = accCoal + rotationCoal
            p.append(totalCoal)

            # only select valid coal
            if coal - totalCoal >= 0:
                newPossibleSpeeds.append(p)

        if printStuff:
            print('pos', position)
            print('dir', direction)
            print('spd', speed)
            print('col', coal)
            print('dep', depth)
            print('diM', directionMap)
            print('cuM', cubeMap)
            print('rCM', rotationCountMap)
            print('mSM', mustSpeedMap)
            print('spM', speedMap)
            print('sSM', speedSumMap)
            print('poS', possibleSpeeds)
            print('nPS', newPossibleSpeeds)

        if len(newPossibleSpeeds) == 0:
            if depth > 0:
                node = ';'.join(str(x) for x in position.coordinates())
                mustSpeed = self.G.nodes[node]['speed']
                score = self.evalSpeed(len(directionMap), coal, speed, mustSpeed, depth, self.game_state.board.segment_index(position), printStuff)
                if printStuff:
                    print('exit2', depth, len(directionMap), score)
                return score
            else:
                return None

        node = ';'.join(str(x) for x in position.coordinates())
        mustSpeed = self.G.nodes[node]['speed']
        score = self.evalSpeed(len(directionMap), coal, speed, mustSpeed, depth, self.game_state.board.segment_index(position), printStuff)

        for n in newPossibleSpeeds:
            subStart = n[1]
            if printStuff:
                print('substart', subStart, 'at depth', depth)
            n.append(self.createMoveFast(
                position=cubeMap[subStart],
                direction=directionMap[subStart],
                speed=n[0],
                coal=coal - n[2],
                depth=depth+1,
                directionMap=directionMap[subStart + 1:].copy(),
                cubeMap=cubeMap[subStart + 1:].copy(),
                rotationCountMap=rotationCountMap[subStart + 1:].copy(),
                mustSpeedMap=mustSpeedMap[subStart + 1:].copy(),
                printStuff=printStuff
            ) + score)

        bestScore = -99999
        bestSpeed = None
        for n in newPossibleSpeeds:
            if n[3] >= bestScore:
                bestScore = n[3]
                bestSpeed = n.copy()

        if depth > 0:
            return bestScore
        else:
            if printStuff:
                print('bestspeed', bestSpeed)



        # make move from speed
        actions = []
        acc = bestSpeed[0] - speed
        if acc != 0:
            actions.append(Accelerate(acc))

        # advance one
        newPosition = position
        newDirection = direction
        for i in range(bestSpeed[1] + 1):
            newPosition = newPosition.plus(directionMap[i].vector())

            push = False
            my = ';'.join(str(x) for x in newPosition.coordinates())
            other = ';'.join(str(x) for x in self.game_state.other_ship.position.coordinates())
            if my == other:
                push = True

            if newDirection != directionMap[i]:
                actions.append(Turn(directionMap[i]))
                #self.totalTurns += 1

            actions.append(Advance(1))

            # push to highest weight field lol
            if push:
                positionsOnPath = [';'.join(str(x) for x in position.coordinates())]
                for p in cubeMap[:bestSpeed[1]]:
                    positionsOnPath.append(';'.join(str(x) for x in p.coordinates()))

                if printStuff:
                    print(position, speed)
                    print(cubeMap, bestSpeed[1], positionsOnPath)

                worstDistance = self.infinite # higest weight => push enemy to that field
                worstDirection = None
                notAllowed = []
                for v in range(6):
                    if printStuff:
                        print('notallowed', notAllowed)

                    if v in notAllowed:
                        continue
                    
                    pushother = ';'.join(str(x) for x in self.game_state.other_ship.position.plus(self.directionVectorList[v]).coordinates())

                    for p in positionsOnPath:
                        if pushother == p:
                            notAllowed.append(v)

                            if worstDirection == self.directionList[v]:
                                worstDistance = self.infinite
                                worstDirection = None

                            break

                        try:
                            if self.G.nodes[pushother]['fieldType'] == FieldType.Water or self.G.nodes[pushother]['fieldType'] == FieldType.Goal:
                                if self.G.nodes[pushother]['dockScore'] < worstDistance:
                                    worstDistance = self.G.nodes[pushother]['dockScore']
                                    worstDirection = self.directionList[v]
                        except:
                            pass

                if worstDirection == None:
                    return None

                actions.append(Push(worstDirection))

            newDirection = directionMap[i]
            
            # if passenger
            if self.G.nodes[my]['dock'] == True:
                if self.G.nodes[my]['speed'] == bestSpeed[0]:
                    self.passengers += 1

        return Move(actions=actions)
    
    def countPassengers(self):

        my = ';'.join(str(x) for x in self.me.position.plus(self.directionMap[0].vector()).coordinates())
        if self.G.nodes[my]['dock'] == True:
            #if self.me.speed + self.acceleration == self.G.nodes[my]['speed']: # commented because with one step at a time it doesnt matter
                self.passengers += 1

        print('passengers', self.passengers)

    def updatePassAndDocks(self):
            
            for p in self.passengerFields:
                if p[2] == False:
                    continue

                if self.game_state.board.get(p[0]).passenger.passenger == 0:
                    dock = p[0].plus(self.G.nodes[p[1]]['passengerDirection'].vector())
                    dockNode = ';'.join(str(x) for x in dock.coordinates())
                    self.G.nodes[dockNode]['dock'] = False
                    self.G.nodes[dockNode]['speed'] = 0 # should only be when not goal
                    self.G.nodes[p[1]]['passengerDirection'] = None
                    p[2] = False

    def randomMove(self):
        
        possible_moves: List[Move] = self.game_state.possible_moves()
        return possible_moves[random.randint(0, len(possible_moves) - 1)]

    def printGraph(self, console, useLogging, sendToServer):
        self.turnData = {
            "turn": self.game_state.turn,
            "player": self.game_state.current_ship.team,
            "time": self.startTimeString,
            "currentShip": {
                "coords": ';'.join(str(x) for x in self.game_state.current_ship.position.coordinates()),
                "passengers": self.passengers,
                "direction": self.game_state.current_ship.direction
            },
            "otherShip": {
                "coords": ';'.join(str(x) for x in self.game_state.other_ship.position.coordinates()),
                "passengers": self.game_state.other_ship.passengers,
                "direction": self.game_state.other_ship.direction
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
        print('t', self.game_state.turn)

        # set turn variables
        self.me = self.game_state.current_ship

        # add segments / fields to graph
        self.segmentsAdded = 0
        while self.maxSegments < len(self.game_state.board.segments):

            self.buildGraph(self.maxSegments)

            self.maxSegments += 1
            self.segmentsAdded += 1

        self.updatePassAndDocks()

        self.setDistances(self.setStarts())
        self.calcScores()

        for i, s in enumerate(self.sortedGraphDock):
            print(i)
            self.buildTree(i)
            #move1 = self.createMoveSlow()

            move3 = self.createMoveFast(
                self.me.position,
                self.me.direction,
                self.me.speed,
                self.me.coal,
                0,
                self.directionMap,
                self.cubeMap,
                self.rotationCountMap,
                self.mustSpeedMap,
                False
            )

            if move3 != None:
                break

        if move3 == None:
            move3 = self.randomMove()

        self.printGraph(console=False, useLogging=False, sendToServer=True)
        print('p', self.passengers)

        #self.countPassengers()

        # send move        
        #move = self.randomMove()
        move2 = Move([Advance(1)])
        return move3

    def on_update(self, state: GameState):
        self.game_state = state

if __name__ == "__main__":
    Starter(logic=Logic())
    # if u wanna have more insights, u can set the logging level to debug:
    # Starter(logic=Logic(), log_level=logging.DEBUG)