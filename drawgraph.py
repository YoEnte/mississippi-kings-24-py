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
import matplotlib.pyplot as plt
from matplotlib.patches import RegularPolygon
import numpy as np

start: CubeDirection = CubeDirection.Right
directionList: List[CubeDirection] = [                 # Right -> Clockwise
    CubeDirection.Right,
    CubeDirection.DownRight,
    CubeDirection.DownLeft,
    CubeDirection.Left,
    CubeDirection.UpLeft,
    CubeDirection.UpRight
]

def draw(G: nx.DiGraph):

    colors = []
    hcoord = []
    vcoord = []

    for n in G.nodes:
        coords3 = n.split(';')
        cube = CubeCoordinates(int(coords3[0]), int(coords3[1]))

        if G.nodes[n]['field_type'] == FieldType.Water:
            if G.nodes[n]['dock']:
                colors.append(['pink'])
            elif not G.nodes[n]['stream']:
                colors.append(["blue"])
            else:
                colors.append(["turquoise"])
            
        elif G.nodes[n]['field_type'] == FieldType.Goal:
            colors.append(["gold"])
        elif G.nodes[n]['field_type'] == FieldType.Island:
            colors.append(["green"])
        elif G.nodes[n]['field_type'] == FieldType.Passenger:
            colors.append(["red"])

        q = int(coords3[0])
        r = int(coords3[1])
        s = int(coords3[2])
        hcoord.append(2. * np.sin(np.radians(60)) * (q-s) /3.)
        vcoord.append(r)

    fig, ax = plt.subplots(1)
    ax.set_aspect('equal')

    for x, y, c, n in zip(hcoord, vcoord, colors, G.nodes.data()):
        node = n[0]
        nodeData= n[1]
        
        color = c[0]
        alpha = 0.2
        if nodeData['segment'] % 2 == 1:
            alpha += 0.2
        hex = RegularPolygon((x, y), numVertices=6, radius=2. / 3., 
                            orientation=np.radians(0), 
                            facecolor=color, alpha=alpha, edgecolor='k')
        ax.add_patch(hex)
        
        if nodeData['direction'] != None: # direction
            ax.text(x, y, '---->', ha='center', va='center', size=12, rotation = (6 - directionList.index(nodeData['direction'])) * 60, color='indigo')

        ax.text(x, y-0.3, node, ha='center', va='center', size=7) # coord

        d = nodeData['distance']
        if d >= 9999999999:
            d = 'inf'
        
        ax.text(x, y+0.2, d, ha='center', va='center', size=8) # distance

    # Also add scatter points in hexagon centres
    ax.scatter(hcoord, vcoord, c=[c[0] for c in colors], alpha=0.5)

    plt.gca().invert_yaxis()
    plt.show()


G = nx.DiGraph()
G.add_nodes_from([('-1;-2;3', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 236}), ('-1;-1;2', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.Right, 'dock': False, 'distance': 117}), ('-1;0;1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 0, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 231}), ('-2;1;1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 232}), ('-3;2;1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.Right, 'dock': False, 'distance': 116}), ('0;-2;2', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 234}), ('0;-1;1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.Right, 'dock': False, 'distance': 116}), ('0;0;0', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 0, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 229}), ('-1;1;0', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 230}), ('-2;2;0', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.Right, 'dock': False, 'distance': 115}), ('1;-2;1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 232}), ('1;-1;0', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.Right, 'dock': False, 'distance': 115}), ('1;0;-1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 0, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 227}), ('0;1;-1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 228}), ('-1;2;-1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.Right, 'dock': False, 'distance': 114}), ('2;-2;0', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 230}), ('2;-1;-1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.Right, 'dock': False, 'distance': 114}), ('2;0;-2', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 0, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 225}), ('1;1;-2', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 226}), ('0;2;-2', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.Right, 'dock': False, 'distance': 113}), ('3;-2;-1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 228}), ('3;-1;-2', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.Right, 'dock': False, 'distance': 113}), ('3;0;-3', {'field_type': FieldType.Island, 'passengerDirection': None, 'stream': True, 'segment': 1, 'direction': None, 'dock': False, 'distance': 9999999999}), ('2;1;-3', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 224}), ('1;2;-3', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.Right, 'dock': False, 'distance': 112}), ('4;-2;-2', {'field_type': FieldType.Island, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': None, 'dock': False, 'distance': 9999999999}), ('4;-1;-3', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.Right, 'dock': False, 'distance': 112}), ('4;0;-4', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 1, 'direction': CubeDirection.Right, 'dock': False, 'distance': 110}), ('3;1;-4', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.UpRight, 'dock': False, 'distance': 222}), ('2;2;-4', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.Right, 'dock': False, 'distance': 111}), ('5;-2;-3', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 56}), ('5;-1;-4', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 55}), ('5;0;-5', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 1, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 54}), ('4;1;-5', {'field_type': FieldType.Island, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': None, 'dock': False, 'distance': 9999999999}), ('3;2;-5', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.Right, 'dock': False, 'distance': 110}), ('6;-2;-4', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 54}), ('6;-1;-5', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 53}), ('6;0;-6', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 1, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 52}), ('5;1;-6', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.Right, 'dock': False, 'distance': 26}), ('4;2;-6', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.UpRight, 'dock': False, 'distance': 54}), ('7;-2;-5', {'field_type': FieldType.Island, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': None, 'dock': False, 'distance': 9999999999}), ('7;-1;-6', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 51}), ('7;0;-7', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 2, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 50}), ('6;1;-7', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': CubeDirection.Right, 'dock': False, 'distance': 25}), ('5;2;-7', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': CubeDirection.UpRight, 'dock': False, 'distance': 52}), ('8;-2;-6', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': CubeDirection.Right, 'dock': False, 'distance': 32}), ('8;-1;-7', {'field_type': FieldType.Island, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': None, 'dock': False, 'distance': 9999999999}), ('8;0;-8', {'field_type': FieldType.Passenger, 'passengerDirection': CubeDirection.Right, 'stream': True, 'segment': 2, 'direction': None, 'dock': False, 'distance': 9999999999}), ('7;1;-8', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': CubeDirection.Right, 'dock': False, 'distance': 24}), ('6;2;-8', {'field_type': FieldType.Island, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': None, 'dock': False, 'distance': 9999999999}), ('9;-2;-7', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 15}), ('9;-1;-8', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 14}), ('9;0;-9', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': CubeDirection.DownRight, 'dock': True, 'distance': 13}), ('8;1;-9', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 2, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 11}), ('7;2;-9', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': CubeDirection.Right, 'dock': True, 'distance': 22}), ('10;-2;-8', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': CubeDirection.DownLeft, 'dock': False, 'distance': 30}), ('10;-1;-9', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': CubeDirection.DownLeft, 'dock': False, 'distance': 28}), ('10;0;-10', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': CubeDirection.DownLeft, 'dock': False, 'distance': 26}), ('9;1;-10', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 12}), ('8;2;-10', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 2, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 10}), ('10;1;-11', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 3, 'direction': CubeDirection.DownLeft, 'dock': False, 'distance': 24}), ('9;2;-11', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 3, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 11}), ('8;3;-11', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 3, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 9}), ('7;3;-10', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 3, 'direction': CubeDirection.DownLeft, 'dock': False, 'distance': 12}), ('6;3;-9', {'field_type': FieldType.Passenger, 'passengerDirection': CubeDirection.UpRight, 'stream': False, 'segment': 3, 'direction': None, 'dock': False, 'distance': 9999999999}), ('10;2;-12', {'field_type': FieldType.Island, 'passengerDirection': None, 'stream': False, 'segment': 3, 'direction': None, 'dock': False, 'distance': 9999999999}), ('9;3;-12', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 3, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 10}), ('8;4;-12', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 3, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 8}), ('7;4;-11', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 3, 'direction': CubeDirection.DownLeft, 'dock': False, 'distance': 10}), ('6;4;-10', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 3, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 5}), ('10;3;-13', {'field_type': FieldType.Island, 'passengerDirection': None, 'stream': False, 'segment': 3, 'direction': None, 'dock': False, 'distance': 9999999999}), ('9;4;-13', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 3, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 9}), ('8;5;-13', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 3, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 7}), ('7;5;-12', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 3, 'direction': CubeDirection.DownLeft, 'dock': False, 'distance': 8}), ('6;5;-11', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 3, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 4}), ('10;4;-14', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 3, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 10}), ('9;5;-14', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 3, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 8}), ('8;6;-14', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 3, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 6}), ('7;6;-13', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 3, 'direction': CubeDirection.DownLeft, 'dock': True, 'distance': 6}), ('6;6;-12', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 3, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 3}), ('10;5;-15', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 4, 'direction': CubeDirection.DownLeft, 'dock': False, 'distance': 4}), ('9;6;-15', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 4, 'direction': CubeDirection.DownLeft, 'dock': False, 'distance': 3}), ('8;7;-15', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 4, 'direction': CubeDirection.DownLeft, 'dock': False, 'distance': 2}), ('7;7;-14', {'field_type': FieldType.Passenger, 'passengerDirection': CubeDirection.UpLeft, 'stream': False, 'segment': 4, 'direction': None, 'dock': False, 'distance': 9999999999}), ('6;7;-13', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 4, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 2}), ('10;6;-16', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 4, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 7}), ('9;7;-16', {'field_type': FieldType.Island, 'passengerDirection': None, 'stream': False, 'segment': 4, 'direction': None, 'dock': False, 'distance': 9999999999}), ('8;8;-16', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 4, 'direction': CubeDirection.DownLeft, 'dock': False, 'distance': 2}), ('7;8;-15', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 4, 'direction': CubeDirection.DownLeft, 'dock': False, 'distance': 1}), ('6;8;-14', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 4, 'direction': CubeDirection.DownLeft, 'dock': False, 'distance': 0}), ('10;7;-17', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 4, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 6}), ('9;8;-17', {'field_type': FieldType.Island, 'passengerDirection': None, 'stream': False, 'segment': 4, 'direction': None, 'dock': False, 'distance': 9999999999}), ('8;9;-17', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 4, 'direction': CubeDirection.DownLeft, 'dock': False, 'distance': 1}), ('7;9;-16', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 4, 'direction': CubeDirection.DownLeft, 'dock': False, 'distance': 1}), ('6;9;-15', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 4, 'direction': CubeDirection.DownLeft, 'dock': False, 'distance': 0}), ('10;8;-18', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 4, 'direction': CubeDirection.DownLeft, 'dock': False, 'distance': 2}), ('9;9;-18', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 4, 'direction': CubeDirection.DownLeft, 'dock': False, 'distance': 1}), ('8;10;-18', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 4, 'direction': CubeDirection.DownLeft, 'dock': False, 'distance': 0}), ('7;10;-17', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 4, 'direction': CubeDirection.DownLeft, 'dock': False, 'distance': 0}), ('6;10;-16', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 4, 'direction': CubeDirection.DownLeft, 'dock': False, 'distance': 0})])

draw(G)