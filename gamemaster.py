import grpc

from protos import gamemaster_pb2, gamemaster_pb2_grpc


class GameMasterServicer(gamemaster_pb2_grpc.GameMasterServicer):
    def __init__(self, node):
        self.node = node

    def SetSymbol(self, request, context):
        try:
            self.node.set_symbol(request.position)
            return gamemaster_pb2.SetSymbolResponse(success=True)
        except Exception as exc:
            return gamemaster_pb2.SetSymbolResponse(success=False, error=exc.args[0])

    def ListBoard(self, request, context):
        board = self.node.get_board()
        move_timestamps = self.node.get_move_timestamps()
        return gamemaster_pb2.ListBoardResponse(
            board=board,
            move_timestamps=GameMasterServicer.move_timestamps_to_str(move_timestamps)
        )

    @staticmethod
    def move_timestamps_to_str(move_timestamps):
        move_timestamps_str = ""
        for i in range(9):
            if i in move_timestamps:
                move_timestamps_str += f"{i}: {move_timestamps[i].strftime('%H:%M:%S %m/%d/%Y')}\n"
            else:
                move_timestamps_str += f"{i}: None\n"
        return move_timestamps_str
