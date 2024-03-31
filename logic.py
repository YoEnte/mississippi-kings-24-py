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

    # this method is called every time the server is requesting a new move
    # this method should always be implemented otherwise the client will be disqualified
    def calculate_move(self) -> Move:
        logging.info("Calculate move...")
        possible_moves: List[Move] = self.game_state.possible_moves()
        newPoss = []
        test = 0
        for m in possible_moves[0:round(len(possible_moves) / 1)]:
            test += 1
            print(m.actions, abs(m.actions[0].acc))
            count_acc = 0
            count_acc_distance = 0
            count_turn = 0
            count_turn_coal = 0
            count_adv = 0
            count_adv_distance = 0
            for a in m.actions:
                if type(a) == Accelerate:
                    count_acc += 1
                    count_acc_distance += a.acc

                elif type(a) == Turn:
                    count_turn += 1

                elif type(a) == Advance:
                    count_adv += 1
                    count_adv_distance += a.distance
            
            print(count_acc_distance, count_turn, count_adv, count_adv_distance)

            if count_acc_distance < 3 and count_turn < 2 and count_adv < 2 and count_adv_distance >= 2:
                newPoss.append(m)

        print(test)
        print(len(possible_moves))
        print(len(newPoss))

        if len(newPoss) > 0:
            return newPoss[random.randint(0, len(newPoss) - 1)]
        else:
            return possible_moves[random.randint(0, len(possible_moves) - 1)]

        

    # this method is called every time the server has sent a new game state update
    # this method should be implemented to keep the game state up to date
    def on_update(self, state: GameState):
        self.game_state = state


if __name__ == "__main__":
    Starter(logic=Logic())
    # if u wanna have more insights, u can set the logging level to debug:
    # Starter(logic=Logic(), log_level=logging.DEBUG)