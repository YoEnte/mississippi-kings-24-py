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
    mustSpeedMap: List[int]
    rotationMap: List[int]
    positionMap: List[CubeCoordinates]
    directionVectors: List[CubeCoordinates]
    directions: List[CubeDirection]
    passengerNodes: List[List] # str, CubeCoordinates, bool

    
    def __init__(self):
        
        self.G = nx.DiGraph()
        self.maxSegments = 0
        self.lastTimeAcc = 0
        self.totalTurns = 0
        self.totalAdv = 0
        self.tree: List[CubeDirection] = []
        self.mustSpeedMap: List[int] = []
        self.rotationMap: List[int] = []
        self.positionMap: List[CubeCoordinates] = []
        self.idle = False
        self.passengerNodes = []
        self.passengers = 0
        self.depth = 5
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
                self.G.add_node(node, field_type=field_type, passengerDirection=passengerDirection, speed=0, stream=stream, segment=self.maxSegments - 1, direction=None)
                #print(node)



            cube = base
            node = ';'.join(str(x) for x in cube.coordinates())
            stream = self.game_state.board.does_field_have_stream(cube)
            field_type = thisSegment.fields[i][2].field_type
            passengerDirection = None
            if field_type == FieldType.Passenger:
                passengerDirection = thisSegment.fields[i][2].passenger.direction
                self.passengerNodes.append([node, cube, True])
            self.G.add_node(node, field_type=field_type, passengerDirection=passengerDirection, speed=0, stream=stream, segment=self.maxSegments - 1, direction=None)
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
                self.G.add_node(node, field_type=field_type, passengerDirection=passengerDirection, speed=0, stream=stream, segment=self.maxSegments - 1, direction=None)
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
            
    def setDistances(self, tries):

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
                        if self.passengers < 2 and tries == 0: # if need for passengers
                            if self.G.nodes[neighborNode]['dock'] == True:
                                dockMulti = 0

                        newWeight = math.floor((self.G.nodes[smallestNode]['distance'] + 1) * (abs(flow.turn_count_to(self.G.nodes[smallestNode]['direction'])) + 1) * dockMulti)

                        #if newWeight == 0:
                            #newWeight = 0.1

                        if self.G.nodes[neighborNode]['distance'] > newWeight:
                            #print("relaxed to", self.G.nodes[smallestNode]['distance'] + 1)
                            self.G.nodes[neighborNode]['distance'] = newWeight
                            self.G.nodes[neighborNode]['direction'] = flow


                        # neighbors unvisted machen wenn

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
                self.G.nodes[dockNode]['speed'] = 0
                self.G.nodes[p[0]]['passengerDirection'] = None
                p[2] = False

    def buildTree(self):
        
        self.tree = []
        self.mustSpeedMap = []
        self.rotationMap = []
        self.positionMap = []

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
                self.mustSpeedMap.append(self.G.nodes[globalbestNode]['speed'])
                self.positionMap.append(lastCube)
            except:
                break
        
        direction = self.direction
        for t in self.tree:
            self.rotationMap.append(abs(direction.turn_count_to(t)))
            direction = t

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
    
    def evalSpeed(self, distanceLeft, coal, speed, mustSpeed, depth, playerSegment):

        turn = self.game_state.turn + (depth * 2)
        coalLoss = self.game_state.current_ship.coal - coal

        score = 0 # möglichst groß


        print(mustSpeed, speed)
        if mustSpeed == speed:
            score = (self.depth - depth) * 200
        else:
            score += (self.depth - depth) * speed * 4

            if mustSpeed != 0:
                score = 0

        score -= (self.depth - depth) * (coalLoss ** 3) * 10

        score *= ((self.depth + 1) - depth) / 2
        #score -= max(0, 30 - turn) * (3 - depth) * (coalLoss ** 2) * 3

        #if playerSegment == self.maxSegments - 1 and distanceLeft - speed < 0:
            #score = 0

        score = math.ceil(score)

        return score
    
    def treeToMoveSpeed(
            self,
            position: CubeCoordinates,
            direction: CubeDirection,
            speed: int,
            coal: int,
            depth: int,
            tree: List[CubeDirection],
            mustSpeedMap: List[int],
            rotationMap: List[int],
            positionMap: List[CubeCoordinates]
        ):
        
        minSpeed = 1
        maxSpeed = 4

        if depth > self.depth or len(tree) == 0:
            node = ';'.join(str(x) for x in position.coordinates())
            mustSpeed = self.G.nodes[node]['speed']
            score = self.evalSpeed(len(tree), coal, speed, mustSpeed, depth, self.game_state.board.segment_index(position))
            print('exit1', depth, len(tree), score)
            return score

        print('\n\n new depth')
        print('parms', position, direction, speed, coal, depth)

        print('tree', tree)
        print('mustSpeedMap', mustSpeedMap)
        print('rotationMap', rotationMap)
        print('positionMap', positionMap)

        speedMap = []
        speedMapSum = []

        # generate speed maps
        pos = position
        lastDirection = direction
        newStream = True
        for t in tree:
            speedMap.append(1)

            pos = pos.plus(t.vector())
            node = ';'.join(str(x) for x in pos.coordinates())

            try:
                test = self.G.nodes[node]['stream']
            except:
                continue

            # if this field is new Stream (set newStream for next field)
            # if now not on stream -> if next field stream it is 100% newStream
            if self.G.nodes[node]['stream'] == False:
                newStream = True
            
            # if on stream and direction change -> counts as new stream
            if self.G.nodes[node]['stream'] == True and lastDirection != t:
                newStream = True


            # if on newStream
            if self.G.nodes[node]['stream'] == True and newStream == True:
                newStream = False
                speedMap[-1] += 1

            other = ';'.join(str(x) for x in self.game_state.other_ship.position.coordinates())
            if other == node:
                speedMap[-1] += 1

            lastDirection = t

            if len(speedMapSum) == 0:
                lastOfTree = 0
            else:
                lastOfTree = speedMapSum[-1]

            speedMapSum.append(lastOfTree + speedMap[-1])
        
        print('speedMap', speedMap)
        print('speedMapSum', speedMapSum)

        # select possible speeds
        possibleSpeeds: List[List] = []
        index = 0
        for s in range(minSpeed, maxSpeed + 1):

            if s in speedMapSum:
                possibleSpeeds.append([s, index])
                index += 1

        # calc coal
        newPossibleSpeeds = [] # speed, index in sumMap, coal, score
        for p in possibleSpeeds:
            accCoal = max(0, abs(speed - p[0]) - 1)
            rotationCoal = -1
            for i, r in enumerate(rotationMap):
                if i > p[1]:
                    break
                rotationCoal += r

            rotationCoal = max(0, rotationCoal)

            totalCoal = accCoal + rotationCoal
            p.append(totalCoal)

            # only select valid coal
            if coal - totalCoal >= 0:
                newPossibleSpeeds.append(p)
        
        print('possSpeeds', possibleSpeeds)
        print('newPossSpeeds', newPossibleSpeeds)

        if len(newPossibleSpeeds) == 0:
            if depth > 0:
                node = ';'.join(str(x) for x in position.coordinates())
                mustSpeed = self.G.nodes[node]['speed']
                score = self.evalSpeed(len(tree), coal, speed, mustSpeed, depth, self.game_state.board.segment_index(position))
                print('exit2', depth, len(tree), score)
                return score
            else:
                return None
        
        
        
        node = ';'.join(str(x) for x in position.coordinates())
        mustSpeed = self.G.nodes[node]['speed']
        score = self.evalSpeed(len(tree), coal, speed, mustSpeed, depth, self.game_state.board.segment_index(position))

        for n in newPossibleSpeeds:
            subStart = n[1]
            print('substart', subStart, 'at depth', depth)
            n.append(self.treeToMoveSpeed(
                positionMap[subStart],
                tree[subStart],
                n[0],
                coal - n[2],
                depth+1,
                tree[subStart + 1:].copy(),
                mustSpeedMap[subStart + 1:].copy(),
                rotationMap[subStart + 1:].copy(),
                positionMap[subStart + 1:].copy(),
            ) + score)

        print('newPossSpeeds', newPossibleSpeeds, 'at depth', depth)

        bestScore = -99999
        bestSpeed = None
        for n in newPossibleSpeeds:
            if n[3] >= bestScore:
                bestScore = n[3]
                bestSpeed = n.copy()

        if depth > 0:
            return bestScore
        else:
            print('bestspeed', bestSpeed)



        actions = []
        acc = bestSpeed[0] - speed
        if acc != 0:
            actions.append(Accelerate(acc))

        # advance one
        newPosition = position
        newDirection = direction
        for i in range(bestSpeed[1] + 1):
            newPosition = newPosition.plus(tree[i].vector())

            push = False
            my = ';'.join(str(x) for x in newPosition.coordinates())
            other = ';'.join(str(x) for x in self.game_state.other_ship.position.coordinates())
            if my == other:
                push = True

            if newDirection != tree[i]:
                actions.append(Turn(tree[i]))
                self.totalTurns += 1

            actions.append(Advance(1))

            # push to highest weight field lol
            if push:
                positionsOnPath = [';'.join(str(x) for x in position.coordinates())]
                for p in positionMap[:bestSpeed[1]]:
                    positionsOnPath.append(';'.join(str(x) for x in p.coordinates()))

                print(position, speed)
                print(positionMap, bestSpeed[1], positionsOnPath)

                worstDistance = -999 # highest weight => push enemy to that field
                worstDirection = None
                notAllowed = []
                for v in range(6):
                    print('notallowed', notAllowed)

                    if v in notAllowed:
                        break
                    
                    pushother = ';'.join(str(x) for x in self.game_state.other_ship.position.plus(self.directionVectors[v]).coordinates())

                    for p in positionsOnPath:
                        if pushother == p:
                            notAllowed.append(v)

                            if worstDirection == self.directions[v]:
                                worstDistance = -999
                                worstDirection = None
                            break

                        try:
                            if self.G.nodes[pushother]['field_type'] == FieldType.Water:
                                if self.G.nodes[pushother]['distance'] > worstDistance:
                                    worstDistance = self.G.nodes[pushother]['distance']
                                    worstDirection = self.directions[v]
                        except:
                            pass

                actions.append(Push(worstDirection))

            newDirection = tree[i]
            
            # if passenger
            if self.G.nodes[my]['dock'] == True:
                if self.G.nodes[my]['speed'] == bestSpeed[0]:
                    self.passengers += 1

        return Move(actions=actions)

    def hashCube(self, position: CubeCoordinates) -> str:
        pass

    def unhashCube(self, position: str) -> CubeCoordinates:
        pass

    def randomMove(self) -> Move:

        possible_moves: List[Move] = self.game_state.possible_moves()
        return possible_moves[random.randint(0, len(possible_moves) - 1)]


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

        
        if self.playerSegmentIndex >= 6 and self.passengers < 2 and self.idle == False:
            self.idle = True

        #if self.maxSegments == 8 and len(self.tree) <= 4 and self.idle == False:
        #    self.idle = True

        if self.idle == False:
            print('goal')
        else:
            print('idle')


        self.updatePassAndDocks()

        move2 = None
        tries = 0
        if (self.idle == False or True):
            while move2 == None:
                self.setDistances(tries)

                #logging.info(self.G.nodes.data('distance'))
                #logging.info(self.G.nodes.data('direction'))
                graphstr = str(self.G.nodes.data()).replace('::', '.')
                logging.info(graphstr)
                logging.info("")

                self.buildTree()
                logging.info(self.tree)
                logging.info("")

                move1 = self.treeToMove()

                move2 = self.treeToMoveSpeed(
                    self.position,
                    self.direction,
                    self.game_state.current_ship.speed,
                    self.game_state.current_ship.coal,
                    0,
                    self.tree.copy(),
                    self.mustSpeedMap.copy(),
                    self.rotationMap.copy(),
                    self.positionMap.copy()
                )

                if tries >= 3:
                    return self.randomMove()

                tries += 1
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

            moves = []
            depth = 2
            while len(moves) == 0:
                moves = self.game_state.possible_action_comb(self.game_state, [], 0, depth)
                
                depth += 1
            
            print(moves)
            move2 = Move(moves[0])


        #self.treeToMoveSpeed(self.position, self.direction, self.game_state.current_ship.speed, self.game_state.current_ship.coal, 0)

        print(self.game_state.current_ship.passengers, 'passengers')
        print(self.passengers, 'passengers')

        return move2
        return possible_moves[random.randint(0, len(possible_moves) - 1)]

    # this method is called every time the server has sent a new game state update
    # this method should be implemented to keep the game state up to date
    def on_update(self, state: GameState):
        self.game_state = state


if __name__ == "__main__":
    Starter(logic=Logic())
    # if u wanna have more insights, u can set the logging level to debug:
    # Starter(logic=Logic(), log_level=logging.DEBUG)