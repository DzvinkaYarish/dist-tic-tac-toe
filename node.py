import sys
from concurrent import futures

import grpc

from protos import share_id_pb2, share_id_pb2_grpc, share_leader_id_pb2, share_leader_id_pb2_grpc, \
    gamemaster_pb2, gamemaster_pb2_grpc, player_pb2, player_pb2_grpc

from election import IdSharingServicer, LeaderIdSharingServicer
from gamemaster import GameMasterServicer
from player import PlayerServicer

from tic_tac_toe import *


class Node:
    def __init__(self, id, ring_ids):
        self.id = id
        self.ring_ids = ring_ids
        self.leader_id = 300

        self.cmds = {
            'Start-game': self.start_game,
            'Set-symbol': self.send_turn,
            'List-board': self.list_board,
            'Set-node-time': self.set_node_time,
            'Set-time-out': self.set_time_out
        }

        # Only defined for the game master (leader node), for the players it is None
        self.board = init_board()  # TODO this is for debugging, remove later
        # Only defined for the players (non-leader nodes), for the player it is None
        self.symbol = None

        # Add all necessary services to a single server
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))

        share_id_pb2_grpc.add_IdSharingServicer_to_server(IdSharingServicer(self), self.server)
        share_leader_id_pb2_grpc.add_LeaderIdSharingServicer_to_server(LeaderIdSharingServicer(self), self.server)
        gamemaster_pb2_grpc.add_GameMasterServicer_to_server(GameMasterServicer(self), self.server)
        player_pb2_grpc.add_PlayerServicer_to_server(PlayerServicer(self), self.server)

        self.server.add_insecure_port(f'localhost:2002{self.id}')

    def start_server(self):
        self.server.start()
        print(f'Started node with id {self.id}')
        print(f'Listening on port 2002{self.id}')

    def stop_server(self):
        self.server.stop(0)
        print(f'Stopped node with id {self.id}')

    def handle_input(self, inp):
        inp = inp.strip().split(' ')
        try:
            self.cmds[inp[0]](*inp[1:])
        except KeyError:
            print('Invalid command.')
        except TypeError:
            print('Invalid arguments to the command.')

    def start_election(self):
        print('Starting election')
        for next_node_id in self.ring_ids:
            try:
                with grpc.insecure_channel(Node._get_node_ip(next_node_id)) as channel:
                    print(f'Forwarding ELECTION message to node {next_node_id}')
                    stub = share_id_pb2_grpc.IdSharingStub(channel)
                    req = share_id_pb2.ShareIdRequest(sender_id=self.id, all_ids=','.join([str(self.id)]))
                    res = stub.ShareId(req)
                    break
            except grpc.RpcError as e:
                continue
        return res

    def start_game(self):
        status = self.start_election()
        if not status:
            print('Election failed. No leader was elected.')
            return

        print(f'Election completed successfully. Node at {self.leader_id} is the leader. Starting the game...')
        self.board = init_board()

        # ToDO: decide how leader knows that election has been completed and it needs to start acting as leader

    def sync_clocks(self):
        pass

    def get_turn(self, player_id):
        print('Get turn')
        self._is_player_check(player_id)
        with grpc.insecure_channel(Node._get_node_ip(player_id)) as channel:
            stub = player_pb2_grpc.PlayerStub(channel)
            _ = stub.RequestTurn(player_pb2.RequestTurnRequest())

    def send_turn(self, pos, symbol):
        print('Send turn')
        pos = int(pos)
        symbol = parse_symbol(symbol)
        self._is_player_check(self.id)
        with grpc.insecure_channel(Node._get_node_ip(self.leader_id)) as channel:
            stub = gamemaster_pb2_grpc.GameMasterStub(channel)
            res = stub.SetSymbol(gamemaster_pb2.SetSymbolRequest(position=pos, symbol=symbol))
            if res.success:
                print('Symbol set successfully')
            else:
                print(res.error)

    def list_board(self):
        print('List board')
        self._is_player_check(self.id)
        with grpc.insecure_channel(Node._get_node_ip(self.leader_id)) as channel:
            stub = gamemaster_pb2_grpc.GameMasterStub(channel)
            res = stub.ListBoard(gamemaster_pb2.ListBoardRequest())
            if res.success:
                print_board(res.board)
            else:
                print(res.error)

    def set_node_time(self, id, time_str):
        print('Setting time')

    def set_time_out(self, node_type, minutes):
        print('Setting timeout')

    def set_symbol(self, pos_symbol, symbol):
        print('Set symbol')
        set_symbol(self.board, pos_symbol, symbol)

    def get_board(self):
        print('Get board')
        return self.board

    def _get_player_ids(self):
        return [i for i in self.ring_ids if i != self.leader_id]

    def _game_started_check(self):
        if self.leader_id is None:
            raise Exception('Leader id is not set. The game has not started yet')

    def _is_player_check(self, node_id):
        self._game_started_check()
        if node_id not in self._get_player_ids():
            raise Exception(f'{node_id} does not appear to be a valid player id')

    def _is_leader_check(self, node_id):
        self._game_started_check()
        if node_id == self.leader_id:
            raise Exception(f'{node_id} does not appear to be the leader')

    @staticmethod
    def _get_node_ip(node_id):
        return f'localhost:2002{node_id}'


if __name__ == '__main__':
    node_ids = [100, 200, 300]
    current_node_id = node_ids[int(sys.argv[1])]

    # ids = list(range(3,8))
    # nodes = []
    # for i, j in enumerate(ids):
    #     nodes.append(Node(j, ids[i + 1:] + ids[:i + 1]))  # rotate the list of node ids to form a ring
    # for n in nodes:
    #     n.start_server()
    #
    # # for i, n in enumerate(nodes):
    # #     print(f'For node {i} rings ids are {n.ring_ids}')
    #
    # print(nodes[0].start_election())
    # for i, n in enumerate(nodes):
    #     print(f'For node {i} leader is {n.leader_id}')

    n = Node(current_node_id, node_ids)
    n.start_server()

    while True:
        try:
            print('Waiting for input...')
            inp = input()
            n.handle_input(inp)
        except KeyboardInterrupt:
            exit()
