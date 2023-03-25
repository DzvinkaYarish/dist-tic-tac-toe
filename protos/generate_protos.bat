python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. share_id.proto
python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. share_leader.proto
python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. player.proto
python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. gamemaster.proto