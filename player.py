import os
import time
from protos import player_pb2, player_pb2_grpc


class PlayerServicer(player_pb2_grpc.PlayerServicer):
    def __init__(self, node):
        self.node = node

    def SendMessage(self, request, context):
        print(request.message, end='\n> ')
        self.node.reset_leader_timeout_timer()
        self.node.last_res_from_leader_timestamp = time.time() + self.node.offset
        return player_pb2.SendMessageResponse()

    def EndGame(self, request, context):
        print(request.message)
        self.node.reset()
        print('Resetting the game...',  end='\n> ')
        return player_pb2.SendMessageResponse()

    def ExitGame(self, request, context):
        print(f'Exiting game because of {request.message}')
        self.node.stop_server()
        os._exit(0)

    def VerifyLeaderIsDown(self, request, context):
        return player_pb2.VerifyLeaderIsDownResponse(last_req_from_leader_timestamp=self.node.last_res_from_leader_timestamp)