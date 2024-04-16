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
                colors.append(["lightseagreen"])
            
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
        alpha = 0.3
        if nodeData['segment'] % 2 == 1:
            alpha += 0.2
        hex = RegularPolygon((x, y), numVertices=6, radius=2. / 3., 
                            orientation=np.radians(0), 
                            facecolor=color, alpha=alpha, edgecolor='k')
        ax.add_patch(hex)
        
        if nodeData['direction'] != None: # direction
            ax.text(x, y, '--->', ha='center', va='center', size=12, rotation = (6 - directionList.index(nodeData['direction'])) * 60, color='indigo')

        ax.text(x, y-0.3, node, ha='center', va='center', size=7) # coord

        d = nodeData['distance']
        if d >= 9999999999:
            d = 'inf'
        
        ax.text(x, y+0.1, d, ha='center', va='center', size=9) # distance

        if nodeData['speed'] != None:
            ax.text(x, y+0.5, nodeData['speed'], ha='center', va='center', size=8) # speed

    # Also add scatter points in hexagon centres
    ax.scatter(hcoord, vcoord, c=[c[0] for c in colors], alpha=0.5)

    plt.gca().invert_yaxis()
    plt.gca().axes.get_xaxis().set_visible(False)
    plt.gca().axes.get_yaxis().set_visible(False)  
    plt.show()


G = nx.DiGraph()
G.add_nodes_from()

draw(G)