import random
import sys
import itertools
from concurrent import futures
from threading import Timer

import grpc

import time
import datetime
import os

from protos import share_id_pb2, share_id_pb2_grpc, share_leader_id_pb2, share_leader_id_pb2_grpc, \
    gamemaster_pb2, gamemaster_pb2_grpc, player_pb2, player_pb2_grpc, \
    time_sync_pb2, time_sync_pb2_grpc, set_timeout_pb2, set_timeout_pb2_grpc
from election import IdSharingServicer, LeaderIdSharingServicer
from gamemaster import GameMasterServicer
from player import PlayerServicer
from set_timeout import TimeOutServicer

from tic_tac_toe import *

import time_sync


DEBUGGING = False


class Node:
    def __init__(self, id, ring_ids):
        self.id = id
        self.ring_ids = ring_ids
        self.alive_ids = ring_ids
        self.leader_id = None

        # For clock synchronization
        self.offset = 0

        # Leader/GameMaster (only defined for a leader)
        self.player_x_id = None
        self.player_o_id = None
        self.board = None
        self.moves_timestamps = {}  # board index - when the move was made

        # State for the timer
        self.waiting_for_move = False
        self.curr_move_timer = None
        self.leader_timeout = 30
        self.player_timeout = 120

        self.last_res_from_leader_timestamp = None
        self.leader_timeout_timer = None

        self.reset()

        self.cmds = {
            'Start-game': self.start_game,
            'Set-symbol': self.send_turn,
            'List-board': self.list_board,
            'Set-node-time': self.set_node_time,
            'Set-time-out': self.set_time_out
        }

        # Add all necessary services to a single server
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

        share_id_pb2_grpc.add_IdSharingServicer_to_server(IdSharingServicer(self), self.server)
        share_leader_id_pb2_grpc.add_LeaderIdSharingServicer_to_server(LeaderIdSharingServicer(self), self.server)
        gamemaster_pb2_grpc.add_GameMasterServicer_to_server(GameMasterServicer(self), self.server)
        player_pb2_grpc.add_PlayerServicer_to_server(PlayerServicer(self), self.server)
        time_sync_pb2_grpc.add_TimeSyncServicer_to_server(time_sync.TimeSyncServicer(self), self.server)
        set_timeout_pb2_grpc.add_TimeOutServicer_to_server(TimeOutServicer(self), self.server)

        self.server.add_insecure_port(Node._get_node_ip(self.id))

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

            self.waiting_for_move = False
            self.moves_timestamps = {}

            if self.leader_timeout_timer:
                self.leader_timeout_timer.cancel()
                self.leader_timeout_timer = None
            if self.curr_move_timer:
                self.curr_move_timer.cancel()
                self.curr_move_timer = None

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

    def exit_game(self, message):
        for node_id in self.ring_ids[:-1]:
            try:
                with grpc.insecure_channel(Node._get_node_ip(node_id)) as channel:
                    stub = player_pb2_grpc.PlayerStub(channel)
                    stub.ExitGame(player_pb2.SendMessageRequest(message=message))
            except grpc.RpcError:
                continue

    def start_game(self):
        n_retries = 1
        retries = -1
        while not retries == n_retries:
            status = self.start_election()
            if not status or len(self.alive_ids) < 3:
                print('Game start failed. There aren\'t enough nodes online to start a game.')
                retries += 1
                print(f'Sleeping for 10s, then maybe retrying election. {n_retries - retries} retries left.')

                time.sleep(10)
            else:
                break

        if not status or len(self.alive_ids) < 3:
            print('The game cannot be started. Exiting...')
            self.exit_game('not enough nodes online.')
            self.stop_server()
            os._exit(0)

        # trigger leader to sync clocks and start game
        status = self.notify_leader()
        if not status:
            print('Triggering leader failed.')
            return

    def setup_game_data_and_request_the_first_move(self):
        self._is_leader_check(self.id)

        player_ids = self._get_player_ids()
        self.player_x_id = random.choice(player_ids)
        self.player_o_id = player_ids[0] if self.player_x_id == player_ids[1] else player_ids[1]

        self.board = init_board()
        self.send_message_players('THE GAME HAS STARTED')
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
            with grpc.insecure_channel(Node._get_node_ip(client_id)) as channel:
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
            with grpc.insecure_channel(Node._get_node_ip(client_id)) as channel:
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
            _ = stub.SendMessage(player_pb2.SendMessageRequest(message="Turn has been requested by the Game Master"))
        # add basic timer to manage timeouts
        # state for this timer is changed in server code
        # in SetSymbol method
        self.waiting_for_move = True
        self.curr_move_timer = Timer(self.player_timeout, self._finish_if_still_waiting)
        self.curr_move_timer.start()

    def send_message_players(self, message):
        for node_id in self.ring_ids[:-1]:
            try:
                with grpc.insecure_channel(Node._get_node_ip(node_id)) as channel:
                    stub = player_pb2_grpc.PlayerStub(channel)
                    _ = stub.SendMessage(player_pb2.SendMessageRequest(message=message))
            except grpc.RpcError:
                continue

    def send_turn(self, pos):
        print('Send turn',  end='\n> ')
        pos = int(pos) - 1  # convert to 0-based index
        self._is_player_check(self.id)
        try:
            with grpc.insecure_channel(Node._get_node_ip(self.leader_id)) as channel:
                stub = gamemaster_pb2_grpc.GameMasterStub(channel)
                res = stub.SetSymbol(gamemaster_pb2.SetSymbolRequest(node_id=self.id, position=pos))
                if res.success:
                    self.last_res_from_leader_timestamp = time.time() + self.offset
                    self.reset_leader_timeout_timer()
                    print('Symbol set successfully', end='\n> ')
                else:
                    print(res.error)
        except grpc.RpcError as e:
            print("Leader isn't responding.")

    def list_board(self):
        print('List board')
        self._is_player_check(self.id)
        try:
            with grpc.insecure_channel(Node._get_node_ip(self.leader_id)) as channel:
                stub = gamemaster_pb2_grpc.GameMasterStub(channel)
                res = stub.ListBoard(gamemaster_pb2.ListBoardRequest())
                print(res.move_timestamps)
                print_board(res.board)
                self.last_res_from_leader_timestamp = time.time() + self.offset
                self.reset_leader_timeout_timer()
        except grpc.RpcError as e:
            print("Leader isn't responding.")


    def get_winner(self):
        self._is_leader_check(self.id)
        winner = get_winner(self.board)
        if winner is None:
            raise Exception('The game is not over yet')
        winner = get_symbol_char(winner)

        return winner

    def set_node_time(self, node_name, time_str):
        print('Setting time')
        try:
            node_id = int(node_name.split('-')[1])

            date = datetime.date.today().strftime('%m/%d/%Y')
            new_total_seconds = datetime.datetime.strptime(date + time_str, '%m/%d/%Y%H:%M:%S').timestamp()
        except ValueError:
            print('Incorrect format.')
            return

        if node_id not in self.ring_ids:
            print('Invalid node id.')
        elif node_id != self.id and self.id != self.leader_id:
            print('Only leader node can set up time of a different node.')

        elif self.id == node_id:
            # adjust the existing node time offset
            now = time.time() + self.offset
            offset = new_total_seconds - now
            self.offset = offset
            print(f'New offset for {node_name} is {offset}.')
        else:
            try:
                with grpc.insecure_channel(Node._get_node_ip(node_id)) as channel:
                    stub = time_sync_pb2_grpc.TimeSyncStub(channel)
                    res = stub.AdjustOffset(time_sync_pb2.OffsetRequest(offset=new_total_seconds))
                    print(f'New offset for {node_name} is {res.offset}.')
            except grpc.RpcError:
                print(f'Error setting {node_name} time.')

    def set_time_out(self, node_type, minutes):
        print('Setting timeout')
        if type == 'players':
            self.player_timeout = minutes * 60
        else:
            self.leader_timeout = minutes * 60

        for node_id in self.ring_ids[:-1]:
            with grpc.insecure_channel(Node._get_node_ip(node_id)) as channel:
                stub = set_timeout_pb2_grpc.TimeOutStub(channel)
                res = stub.SetTimeOut(set_timeout_pb2.SetTimeOutRequest(type=node_type, timeout=int(minutes * 60)))

        if res.success:
            print(f'New time out for {node_type} = {minutes} minutes')

    def set_symbol(self, player_id, pos_symbol):
        print('Set symbol')
        self._is_leader_check(self.id)
        # Check whose turn it is and only allow them to make a move
        # IMPORTANT NOTE: here we are just checking for node id, so it is
        # more than possible to cheat the game by sending requests from a fake id.
        # The correct solution would be to use tokens. However since this is not the
        # focus of this work, we deliberately skip this step.
        current_player = which_turn(self.board)
        if (current_player == X and player_id != self.player_x_id) or \
                (current_player == O and player_id != self.player_o_id):
            raise Exception(f'It is not your turn. Please wait for another player to make a move')

        set_symbol(self.board, pos_symbol, which_turn(self.board))
        self.moves_timestamps[pos_symbol] = datetime.datetime.fromtimestamp(time.time() + self.offset)
        if self.is_game_over():
            winner = self.get_winner()
            self.end_game(message=f'Player {winner} won the game!')
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

    def end_game(self, message):
        print('Resetting the game...')
        for node_id in self.ring_ids[:-1]:
            try:
                with grpc.insecure_channel(Node._get_node_ip(node_id)) as channel:
                    stub = player_pb2_grpc.PlayerStub(channel)
                    stub.EndGame(player_pb2.SendMessageRequest(message=message))
            except grpc.RpcError:
                continue
        self.reset()
        self.start_game()

    def reset_leader_timeout_timer(self):
        if self.leader_timeout_timer:
            self.leader_timeout_timer.cancel()
        self.leader_timeout_timer = Timer(self.leader_timeout, self._agree_if_leader_is_down)
        self.leader_timeout_timer.start()

    def _agree_if_leader_is_down(self):
        other_player_id = self.ring_ids[0] if self.ring_ids[0] != self.leader_id else self.ring_ids[1]
        try:
            with grpc.insecure_channel(Node._get_node_ip(other_player_id)) as channel:
                stub = player_pb2_grpc.PlayerStub(channel)
                res = stub.VerifyLeaderIsDown(player_pb2.VerifyLeaderIsDownRequest())
                if (time.time() + self.offset - res.last_req_from_leader_timestamp) > (self.leader_timeout - 15):
                    self.end_game(message='Both players agreed that the Game Master is down. Ending game...')
                else:
                    print("Players didn't agree that the leader is down. Game continues...")
                    self.reset_leader_timeout_timer()
        except grpc.RpcError:
            print("Other player isn't responding")

    def _get_player_ids(self):
        return [i for i in self.ring_ids + [self.id] if i != self.leader_id]

    def _game_started_check(self):
        if self.leader_id is None:
            raise Exception('Leader id is not set. The game has not started yet.')

    def _is_player_check(self, node_id):
        self._game_started_check()
        if node_id not in self._get_player_ids():
            raise Exception(f'{node_id} does not appear to be a valid player id.')

    def _is_leader_check(self, node_id):
        self._game_started_check()
        if node_id != self.leader_id:
            raise Exception(f'{node_id} does not appear to be the leader.')

    def _finish_if_still_waiting(self):
        if self.waiting_for_move:
            print('Waiting for move timed out. Ending game...')
            self.end_game('Waiting for move timed out')

    @staticmethod
    def print_help():
        print('''
Commands:

    Start-game
    List-board
    Set-symbol <position>
    Set-node time Node-<id> hh:mm:ss
    Set-time-out <players,leader> <minutes>
        ''')

    @staticmethod
    def _get_node_ip(node_id):
        return f'localhost:2002{node_id}'


if __name__ == '__main__':
    node_ids = [7, 8, 9]
    i = int(sys.argv[1])
    current_node_id = node_ids[i]

    n = Node(current_node_id, node_ids[i + 1:] + node_ids[:i + 1])
    n.start_server()

    print('WELCOME TO THE DISTRIBUTED TIC-TAC-TOE GAME!!!')
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
