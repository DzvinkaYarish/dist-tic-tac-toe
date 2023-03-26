from protos import set_timeout_pb2, set_timeout_pb2_grpc


class TimeOutServicer(set_timeout_pb2_grpc.TimeOutServicer):
    def __init__(self, node):
        self.node = node

    def SetTimeOut(self, request, context):
        if request.type == 'players':
            self.node.player_timeout = request.timeout
        else:
            self.node.leader_timeout = request.timeout
        return set_timeout_pb2.SetTimeOutResponse(success=True)