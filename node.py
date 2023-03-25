import random
import sys
import itertools
from concurrent import futures

import grpc

import time
import datetime

from protos import share_id_pb2, share_id_pb2_grpc, share_leader_id_pb2, share_leader_id_pb2_grpc, \
    gamemaster_pb2, gamemaster_pb2_grpc, player_pb2, player_pb2_grpc, \
    time_sync_pb2, time_sync_pb2_grpc
from election import IdSharingServicer, LeaderIdSharingServicer
from gamemaster import GameMasterServicer
from player import PlayerServicer

from tic_tac_toe import *

import time_sync


DEBUGGING = False


class Node:
    def __init__(self, id, ring_ids):
        self.id = id
        self.ring_ids = ring_ids
        self.leader_id = None

        # For clock synchronization
        self.offset = 0

        # Leader/GameMaster (only defined for a leader)
        self.player_x_id = None
        self.player_o_id = None
        self.board = None
        self.moves_timestamps = {}  # board index - when the move was made

        self.reset()

        self.cmds = {
            'Start-game': self.start_game,
            'Set-symbol': self.send_turn,
            'List-board': self.list_board,
            'Set-node-time': self.set_node_time,
            'Set-time-out': self.set_time_out
        }

        # Add all necessary services to a single server
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))

        share_id_pb2_grpc.add_IdSharingServicer_to_server(IdSharingServicer(self), self.server)
        share_leader_id_pb2_grpc.add_LeaderIdSharingServicer_to_server(LeaderIdSharingServicer(self), self.server)
        gamemaster_pb2_grpc.add_GameMasterServicer_to_server(GameMasterServicer(self), self.server)
        player_pb2_grpc.add_PlayerServicer_to_server(PlayerServicer(self), self.server)
        time_sync_pb2_grpc.add_TimeSyncServicer_to_server(time_sync.TimeSyncServicer(self), self.server)

        self.server.add_insecure_port(f'localhost:2002{self.id}')

    def reset(self):
        if DEBUGGING:  # for debugging
            self.leader_id = 300

            self.player_x_id = 100
            self.player_o_id = 200
            self.board = init_board()
        else:
            self.leader_id = None

            self.player_x_id = None
            self.player_o_id = None
            self.board = None

    def start_server(self):
        self.server.start()
        print(f'Started node with id {self.id}')
        print(f'Listening on port 2002{self.id}...')

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

    def notify_leader(self):
        with grpc.insecure_channel(Node._get_node_ip(self.leader_id)) as channel:
            stub = share_leader_id_pb2_grpc.LeaderIdSharingStub(channel)
            res = stub.NotifyLeader(share_leader_id_pb2.NotifyLeaderRequest())
            return res

    def start_game(self):
        status = self.start_election()
        if not status:
            print('Election failed. No leader was elected.')
            return

        # trigger leader to start clock sync
        status = self.notify_leader()
        if not status:
            print('Sync clock failed.')
            return

    def setup_game_data_and_request_the_first_move(self):
        self._is_leader_check(self.id)

        player_ids = self._get_player_ids()
        self.player_x_id = random.choice(player_ids)
        self.player_o_id = player_ids[0] if self.player_x_id == player_ids[1] else player_ids[1]

        self.board = init_board()

        self.get_turn(self.player_x_id)

    def sync_clocks(self):
        if self.leader_id is None:
            print('No leader has been elected yet.')
            return
        elif self.leader_id != self.id:
            print('This node is not the leader. No need to sync clocks.')
            return

        clients = self._get_player_ids()
        current_time = time.time()
        cls_times = itertools.product(clients, [current_time])
        print("Initialization of clock sync with time", current_time)

        # send time to all nodes and get current diffs
        def send_time(inpt):
            client_id, curr_time = inpt
            with grpc.insecure_channel(f'localhost:2002{client_id}') as channel:
                stub = time_sync_pb2_grpc.TimeSyncStub(channel)
                req = time_sync_pb2.TimeRequest(stime=curr_time)
                off_res = stub.GetOffset(req)
            return client_id, off_res.offset

        with futures.ThreadPoolExecutor(max_workers=len(clients)) as executor:
            offsets = executor.map(send_time, cls_times)

        # calculate actual offsets
        client_offsets, master_offset = time_sync.master_time_sync(dict(offsets))

        # send offsets to all nodes
        def send_offset(inpt):
            client_id, offset = inpt
            with grpc.insecure_channel(f'localhost:2002{client_id}') as channel:
                stub = time_sync_pb2_grpc.TimeSyncStub(channel)
                req = time_sync_pb2.OffsetRequest(offset=offset)
                stub.SetOffset(req)
            print(f"Sent offset {offset} to node {client_id}")

        with futures.ThreadPoolExecutor(max_workers=len(clients)) as executor:
            executor.map(send_offset, list(client_offsets.items()))

        # set offset of leader node
        self.offset = master_offset
        print("Clock sync completed successfully. Offset of leader node is", self.offset, "seconds")

    def get_turn(self, player_id):
        print('Get turn')
        self._is_player_check(player_id)
        with grpc.insecure_channel(Node._get_node_ip(player_id)) as channel:
            stub = player_pb2_grpc.PlayerStub(channel)
            _ = stub.RequestTurn(player_pb2.RequestTurnRequest())

    def send_turn(self, pos):
        print('Send turn')
        pos = int(pos) - 1  # convert to 0-based index
        self._is_player_check(self.id)
        with grpc.insecure_channel(Node._get_node_ip(self.leader_id)) as channel:
            stub = gamemaster_pb2_grpc.GameMasterStub(channel)
            res = stub.SetSymbol(gamemaster_pb2.SetSymbolRequest(position=pos))
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
            print(res.move_timestamps)
            print_board(res.board)

    def announce_winner(self):
        self._is_leader_check(self.id)
        winner = get_winner(self.board)
        if winner is None:
            raise Exception('The game is not over yet')
        winner = get_symbol_char(winner)

        print(f'Announcing winner {winner}')
        for player_id in [100]:  # self._get_player_ids():
            with grpc.insecure_channel(Node._get_node_ip(player_id)) as channel:
                stub = player_pb2_grpc.PlayerStub(channel)
                stub.EndGame(player_pb2.EndGameRequest(message=f'Player {winner} won the game!'))

        self.end_game()

    def set_node_time(self, id, time_str):
        print('Setting time')

    def set_time_out(self, node_type, minutes):
        print('Setting timeout')

    def set_symbol(self, pos_symbol):
        print('Set symbol')
        self._is_leader_check(self.id)
        set_symbol(self.board, pos_symbol, which_turn(self.board))
        self.moves_timestamps[pos_symbol] = datetime.datetime.now()
        if self.is_game_over():
            self.announce_winner()
        else:
            next_player = which_turn(self.board)
            self.get_turn(self.player_x_id if next_player == X else self.player_o_id)

    def get_board(self):
        print('Get board')
        self._is_leader_check(self.id)
        return self.board

    def get_move_timestamps(self):
        print('Get move timestamps')
        self._is_leader_check(self.id)
        return self.moves_timestamps

    def is_game_over(self):
        return get_winner(self.board) is not None

    def end_game(self):
        pass

    def _get_player_ids(self):
        return [i for i in self.ring_ids + [self.id] if i != self.leader_id]

    def _game_started_check(self):
        if self.leader_id is None:
            raise Exception('Leader id is not set. The game has not started yet')

    def _is_player_check(self, node_id):
        self._game_started_check()
        if node_id not in self._get_player_ids():
            raise Exception(f'{node_id} does not appear to be a valid player id')

    def _is_leader_check(self, node_id):
        self._game_started_check()
        if node_id != self.leader_id:
            raise Exception(f'{node_id} does not appear to be the leader')

    @staticmethod
    def print_help():
        print('''
Commands:

    Start-game
    List-board
    Set-symbol <position>
        ''')

    @staticmethod
    def _get_node_ip(node_id):
        return f'localhost:2002{node_id}'


if __name__ == '__main__':
    node_ids = [10, 20, 30]
    i = int(sys.argv[1])
    current_node_id = node_ids[i]

    # node_ids.remove(current_node_id)

    n = Node(current_node_id, node_ids[i + 1:] + node_ids[:i + 1])
    n.start_server()

    n.print_help()

    print("Positions:")
    print_board_indexes()

    while True:
        try:
            print("> ", end="")
            inp = input()
            if not inp.strip():
                continue
            n.handle_input(inp)
        except KeyboardInterrupt:
            exit()
