import grpc

from protos import gamemaster_pb2, gamemaster_pb2_grpc


class GameMasterServicer(gamemaster_pb2_grpc.GameMasterServicer):
    def __init__(self, node):
        self.node = node

    def SetSymbol(self, request, context):
        try:
            self.node.set_symbol(request.position, request.symbol)
            return gamemaster_pb2.SetSymbolResponse(success=True)
        except Exception as exc:
            return gamemaster_pb2.SetSymbolResponse(success=False, error=exc.args[0])

    def ListBoard(self, request, context):
        board = self.node.get_board()
        return gamemaster_pb2.ListBoardResponse(success=True, error=None, board=board)
