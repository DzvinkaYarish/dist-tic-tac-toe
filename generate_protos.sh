python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. ./protos/share_id.proto
python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. ./protos/share_leader_id.proto
python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. ./protos/player.proto
python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. ./protos/gamemaster.proto
python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. ./protos/time_sync.proto