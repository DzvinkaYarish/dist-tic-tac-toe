import grpc
import os

from protos import player_pb2, player_pb2_grpc


class PlayerServicer(player_pb2_grpc.PlayerServicer):
    def __init__(self, node):
        self.node = node

    def RequestTurn(self, request, context):
        print("Turn has been requested by the Game Master")
        return player_pb2.RequestTurnResponse()

    def EndGame(self, request, context):
        self.node.reset()
        print(request.message)
        print('Resetting the game...')
        return player_pb2.EndGameResponse()

    def ExitGame(self, request, context):
        print(f'Exiting game because of {request.message}')
        self.node.stop_server()
        os._exit(0)