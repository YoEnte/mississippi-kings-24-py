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
G.add_nodes_from([('-1;-2;3', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 64}), ('-1;-1;2', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 63}), ('-1;0;1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 0, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 62}), ('-2;1;1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.Right, 'dock': False, 'distance': 31}), ('-3;2;1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.Right, 'dock': False, 'distance': 33}), ('0;-2;2', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 62}), ('0;-1;1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 61}), ('0;0;0', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 0, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 60}), ('-1;1;0', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.Right, 'dock': False, 'distance': 30}), ('-2;2;0', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.Right, 'dock': False, 'distance': 32}), ('1;-2;1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 60}), ('1;-1;0', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 59}), ('1;0;-1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 0, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 58}), ('0;1;-1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.Right, 'dock': False, 'distance': 29}), ('-1;2;-1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.Right, 'dock': False, 'distance': 31}), ('2;-2;0', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 58}), ('2;-1;-1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 57}), ('2;0;-2', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 0, 'direction': CubeDirection.DownRight, 'dock': True, 'distance': 56}), ('1;1;-2', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.Right, 'dock': False, 'distance': 28}), ('0;2;-2', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.Right, 'dock': False, 'distance': 30}), ('3;-2;-1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.DownLeft, 'dock': False, 'distance': 116}), ('3;-1;-2', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.DownLeft, 'dock': False, 'distance': 114}), ('3;0;-3', {'field_type': FieldType.Passenger, 'passengerDirection': CubeDirection.Left, 'stream': True, 'segment': 1, 'direction': None, 'dock': False, 'distance': 9999999999}), ('2;1;-3', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.Right, 'dock': False, 'distance': 27}), ('1;2;-3', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.Right, 'dock': False, 'distance': 29}), ('4;-2;-2', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.DownLeft, 'dock': False, 'distance': 115}), ('4;-1;-3', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.Left, 'dock': False, 'distance': 230}), ('4;0;-4', {'field_type': FieldType.Island, 'passengerDirection': None, 'stream': True, 'segment': 1, 'direction': None, 'dock': False, 'distance': 9999999999}), ('3;1;-4', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.Right, 'dock': False, 'distance': 26}), ('2;2;-4', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.Right, 'dock': False, 'distance': 28}), ('5;-2;-3', {'field_type': FieldType.Island, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': None, 'dock': False, 'distance': 9999999999}), ('5;-1;-4', {'field_type': FieldType.Island, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': None, 'dock': False, 'distance': 9999999999}), ('5;0;-5', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 1, 'direction': CubeDirection.Right, 'dock': False, 'distance': 5}), ('4;1;-5', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.UpRight, 'dock': False, 'distance': 12}), ('3;2;-5', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.UpRight, 'dock': False, 'distance': 13}), ('6;-2;-4', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 11}), ('6;-1;-5', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 10}), ('6;0;-6', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 1, 'direction': CubeDirection.Right, 'dock': False, 'distance': 4}), ('5;1;-6', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.UpRight, 'dock': False, 'distance': 10}), ('4;2;-6', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.UpRight, 'dock': False, 'distance': 11}), ('7;-2;-5', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 9}), ('7;-1;-6', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 8}), ('7;0;-7', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 2, 'direction': CubeDirection.Right, 'dock': False, 'distance': 3}), ('6;1;-7', {'field_type': FieldType.Island, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': None, 'dock': False, 'distance': 9999999999}), ('5;2;-7', {'field_type': FieldType.Passenger, 'passengerDirection': CubeDirection.Right, 'stream': False, 'segment': 2, 'direction': None, 'dock': False, 'distance': 9999999999}), ('8;-2;-6', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 7}), ('8;-1;-7', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': CubeDirection.DownRight, 'dock': False, 'distance': 6}), ('8;0;-8', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 2, 'direction': CubeDirection.Right, 'dock': False, 'distance': 2}), ('7;1;-8', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': CubeDirection.Right, 'dock': False, 'distance': 2}), ('6;2;-8', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': CubeDirection.Right, 'dock': True, 'distance': 2}), ('9;-2;-7', {'field_type': FieldType.Island, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': None, 'dock': False, 'distance': 9999999999}), ('9;-1;-8', {'field_type': FieldType.Island, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': None, 'dock': False, 'distance': 9999999999}), ('9;0;-9', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 2, 'direction': CubeDirection.Right, 'dock': False, 'distance': 1}), ('8;1;-9', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': CubeDirection.Right, 'dock': False, 'distance': 1}), ('7;2;-9', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': CubeDirection.Right, 'dock': False, 'distance': 1}), ('10;-2;-8', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': CubeDirection.Right, 'dock': False, 'distance': 0}), ('10;-1;-9', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': CubeDirection.Right, 'dock': False, 'distance': 0}), ('10;0;-10', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 2, 'direction': CubeDirection.Right, 'dock': False, 'distance': 0}), ('9;1;-10', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': CubeDirection.Right, 'dock': False, 'distance': 0}), ('8;2;-10', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 2, 'direction': CubeDirection.Right, 'dock': False, 'distance': 0})])

draw(G)