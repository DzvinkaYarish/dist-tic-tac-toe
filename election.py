import grpc

from protos import share_id_pb2, share_id_pb2_grpc, share_leader_id_pb2, share_leader_id_pb2_grpc


def get_node_ip(node_id):
    return f'localhost:2002{node_id}'


class IdSharingServicer(share_id_pb2_grpc.IdSharingServicer):
    def __init__(self, node):
        self.node = node

    def ShareId(self, request, context):
        all_ids = list(map(int, request.all_ids.split(',')))
        # ELECTION message made a full circle
        if self.node.id in all_ids:
            print(f'Election message made a full circle and returned to {self.node.id}')
            leader_id = max(all_ids)
            self.node.leader_id = leader_id

            # try sending LEADER message to next alive node
            for next_node_id in self.node.ring_ids:
                try:
                    with grpc.insecure_channel(get_node_ip(next_node_id)) as channel:
                        print(f'Forwarding LEADER message to node {next_node_id}')

                        stub = share_leader_id_pb2_grpc.LeaderIdSharingStub(channel)
                        req = share_leader_id_pb2.ShareLeaderIdRequest(sender_id=self.node.id, leader_id=leader_id,
                                                                       all_ids=','.join([str(self.node.id)]))
                        res = stub.ShareLeaderId(req)
                        break
                except grpc.RpcError as e:
                    continue
        # try sending ELECTION message to next alive node
        else:
            for next_node_id in self.node.ring_ids:
                try:
                    with grpc.insecure_channel(get_node_ip(next_node_id)) as channel:
                        print(f'Forwarding ELECTION message to node {next_node_id}')

                        stub = share_id_pb2_grpc.IdSharingStub(channel)
                        req = share_id_pb2.ShareIdRequest(sender_id=self.node.id,
                                                          all_ids=','.join(list(map(str, all_ids + [self.node.id]))))
                        res = stub.ShareId(req)

                        break
                except grpc.RpcError as e:
                    continue
        return share_id_pb2.ShareIdResponse(success=True)


class LeaderIdSharingServicer(share_leader_id_pb2_grpc.LeaderIdSharingServicer):
    def __init__(self, node):
        self.node = node

    def ShareLeaderId(self, request, context):
        all_ids = list(map(int, request.all_ids.split(',')))
        print(f'Node {self.node.id}  received LEADER message from {request.sender_id}')

        if self.node.id in all_ids:
            self.node.alive_ids = all_ids
            if request.leader_id in all_ids:
                print(f'ELECTION SUCCESSFUL! NEW LEADER ID IS {request.leader_id}',  end='\n> ')
                self.node.leader_id = request.leader_id
            # Start election all over again
            else:
                print('starting election again')
                self.node.start_election()

        else:
            print(f'Node {self.node.id} sets it leader as {request.leader_id}')
            self.node.leader_id = request.leader_id

            for next_node_id in self.node.ring_ids:
                try:
                    with grpc.insecure_channel(get_node_ip(next_node_id)) as channel:
                        print(f'Forwarding LEADER message to node {next_node_id}')
                        stub = share_leader_id_pb2_grpc.LeaderIdSharingStub(channel)
                        req = share_leader_id_pb2.ShareLeaderIdRequest(sender_id=self.node.id, leader_id=request.leader_id,
                                                                       all_ids=','.join(list(map(str, all_ids + [self.node.id]))))

                        res = stub.ShareLeaderId(req)
                        break

                except grpc.RpcError as e:
                    continue
        return share_leader_id_pb2.ShareLeaderIdResponse(success=True)

    def NotifyLeader(self, request, context):
        print('I am the leader node.',  end='\n> ')
        self.node.sync_clocks()
        self.node.setup_game_data_and_request_the_first_move()
        return share_leader_id_pb2.NotifyLeaderResponse(success=True)



