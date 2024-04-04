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

directionArrows: List[CubeDirection] = [                 # Right -> Clockwise
    CubeDirection.Right,
    CubeDirection.DownRight,
    CubeDirection.DownLeft,
    CubeDirection.Left,
    CubeDirection.UpLeft,
    CubeDirection.UpRight
]

G = nx.DiGraph()
G.add_nodes_from([('-1;-2;3', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.Right, 'distance': 7}), ('-1;-1;2', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.Right, 'distance': 7}), ('-1;0;1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 0, 'direction': CubeDirection.UpRight, 'distance': 14}), ('-2;1;1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.UpRight, 'distance': 15}), ('-3;2;1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.UpRight, 'distance': 16}), ('0;-2;2', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.Right, 'distance': 6}), ('0;-1;1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.Right, 'distance': 6}), ('0;0;0', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 0, 'direction': CubeDirection.UpRight, 'distance': 12}), ('-1;1;0', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.UpRight, 'distance': 13}), ('-2;2;0', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.UpRight, 'distance': 14}), ('1;-2;1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.Right, 'distance': 5}), ('1;-1;0', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.Right, 'distance': 5}), ('1;0;-1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 0, 'direction': CubeDirection.UpRight, 'distance': 10}), ('0;1;-1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.UpRight, 'distance': 11}), ('-1;2;-1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.UpRight, 'distance': 12}), ('2;-2;0', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.Right, 'distance': 4}), ('2;-1;-1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.Right, 'distance': 4}), ('2;0;-2', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 0, 'direction': CubeDirection.DownRight, 'distance': 7}), ('1;1;-2', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.Right, 'distance': 14}), ('0;2;-2', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 0, 'direction': CubeDirection.UpLeft, 'distance': 24}), ('3;-2;-1', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.Right, 'distance': 3}), ('3;-1;-2', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.Right, 'distance': 3}), ('3;0;-3', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 1, 'direction': CubeDirection.DownRight, 'distance': 5}), ('2;1;-3', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.DownRight, 'distance': 6}), ('1;2;-3', {'field_type': FieldType.Passenger, 'passengerDirection': CubeDirection.Right, 'stream': False, 'segment': 1, 'direction': None, 'distance': 9999999999}), ('4;-2;-2', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.Right, 'distance': 2}), ('4;-1;-3', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.Right, 'distance': 2}), ('4;0;-4', {'field_type': FieldType.Island, 'passengerDirection': None, 'stream': True, 'segment': 1, 'direction': None, 'distance': 9999999999}), ('3;1;-4', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.DownRight, 'distance': 4}), ('2;2;-4', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.Right, 'distance': 2}), ('5;-2;-3', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.Right, 'distance': 1}), ('5;-1;-4', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.Right, 'distance': 1}), ('5;0;-5', {'field_type': FieldType.Island, 'passengerDirection': None, 'stream': True, 'segment': 1, 'direction': None, 'distance': 9999999999}), ('4;1;-5', {'field_type': FieldType.Island, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': None, 'distance': 9999999999}), ('3;2;-5', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.Right, 'distance': 1}), ('6;-2;-4', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.Right, 'distance': 0}), ('6;-1;-5', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.Right, 'distance': 0}), ('6;0;-6', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': True, 'segment': 1, 'direction': CubeDirection.Right, 'distance': 0}), ('5;1;-6', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.Right, 'distance': 0}), ('4;2;-6', {'field_type': FieldType.Water, 'passengerDirection': None, 'stream': False, 'segment': 1, 'direction': CubeDirection.Right, 'distance': 0})])

colors = []
labels = []
distances = []
directions = []
hcoord = []
vcoord = []

for n in G.nodes:
    coords3 = n.split(';')
    cube = CubeCoordinates(int(coords3[0]), int(coords3[1]))

    if G.nodes[n]['field_type'] == FieldType.Water:
        passenger = False
        for v in directionList:
            v_n = ';'.join(str(x) for x in cube.plus(v.vector()).coordinates())
            try:
                if G.nodes[v_n]['field_type'] == FieldType.Passenger and G.nodes[v_n]['passengerDirection'] == v.opposite():
                    colors.append(["pink"])
                    passenger = True
                    break
            except:
                pass
        
        if not passenger:
            if not G.nodes[n]['stream']:
                colors.append(["blue"])
            else:
                colors.append(["turquoise"])
        
    elif G.nodes[n]['field_type'] == FieldType.Goal:
        colors.append(["gold"])
    elif G.nodes[n]['field_type'] == FieldType.Island:
        colors.append(["green"])
    elif G.nodes[n]['field_type'] == FieldType.Passenger:
        colors.append(["red"])

    labels.append(n)
    if G.nodes[n]['distance'] < 9999999999:
        distances.append(G.nodes[n]['distance'])
    else:
        distances.append('inf')
    directions.append(G.nodes[n]['direction'])

    q = int(coords3[0])
    r = int(coords3[1])
    s = int(coords3[2])

    #print(cube, cube.x(), cube.y())

    #hcoord.append(int(coords3[2]))
    #vcoord.append(2. * np.sin(np.radians(30)) * (int(coords3[1]) - int(coords3[0])) /3.)

    hcoord.append(2. * np.sin(np.radians(60)) * (q-s) /3.)
    vcoord.append(r)

fig, ax = plt.subplots(1)
ax.set_aspect('equal')

for x, y, c, l, d, d2 in zip(hcoord, vcoord, colors, labels, distances, directions):
    color = c[0]
    hex = RegularPolygon((x, y), numVertices=6, radius=2. / 3., 
                         orientation=np.radians(0), 
                         facecolor=color, alpha=0.2, edgecolor='k')
    ax.add_patch(hex)
    
    if d2 != None: # direction
        ax.text(x, y, '---->', ha='center', va='center', size=12, rotation = (6 - directionList.index(d2)) * 60, color='indigo')

    ax.text(x, y-0.3, l, ha='center', va='center', size=7) # coord
    ax.text(x, y+0.2, d, ha='center', va='center', size=8) # distance

# Also add scatter points in hexagon centres
ax.scatter(hcoord, vcoord, c=[c[0] for c in colors], alpha=0.5)

plt.gca().invert_yaxis()
plt.show()
