python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. share_id.proto
python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. share_leader.proto
python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. tic_tac_toe_player.proto
python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. tic_tac_toe_gamemaster.proto