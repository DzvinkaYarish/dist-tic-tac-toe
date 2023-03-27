import time

from protos import time_sync_pb2, time_sync_pb2_grpc


def master_time_sync(client_current_deltas: dict) -> tuple:
    print(f"Current deltas: {client_current_deltas}")
    # calculate average delta
    avg_delta = sum(client_current_deltas.values()) / (len(client_current_deltas) + 1)
    # update master time
    master_offset = avg_delta
    # update client times
    client_offsets = {}
    for client_id in client_current_deltas:
        client_offsets[client_id] = avg_delta - client_current_deltas[client_id]
    return client_offsets, master_offset


class TimeSyncServicer(time_sync_pb2_grpc.TimeSyncServicer):
    def __init__(self, node):
        self.node = node

    def GetOffset(self, request, context):
        ct = time.time()
        return time_sync_pb2.TimeReply(
            offset=ct - request.stime
        )

    def SetOffset(self, request, context):
        self.node.offset = request.offset
        return time_sync_pb2.Empty()

    def AdjustOffset(self, request, context):
        now = time.time() + self.node.offset
        self.node.offset = request.offset - now
        return time_sync_pb2.TimeReply(offset=self.node.offset)


if __name__ == '__main__':
    clt_times = {1: 10, 2: 40, 3: 10}
    print(master_time_sync(clt_times))
