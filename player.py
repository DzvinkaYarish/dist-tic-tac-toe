import grpc

from protos import player_pb2_grpc


class PlayerServicer(player_pb2_grpc.PlayerServicer):
    def __init__(self, node):
        self.node = node

    def RequestTurn(self, request, context):
        print("Turn has been requested by the Game Master")

    def EndGame(self, request, context):
        print("The game has ended")
