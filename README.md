# Tic-Tac-Toe project for Distributed Systems course

## Dzvenymyra-Marta Yarish, Nikita Fordui, Anton Zaliznyi

## How to run

### Setup virtual environment

Create a virtual environment

```bash
python -m venv tictactoe
```

Activate the virtual environment

For Windows:

```bash
"tictactoe/Scripts/activate.bat"
```

For Linux:

```bash
tictactoe/Scripts/activate
```

### Install the dependencies

```bash
python -m pip install -r requirements.txt
```

### Generate proto files

```bash
python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. ./protos/share_id.proto
python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. ./protos/share_leader_id.proto
python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. ./protos/player.proto
python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. ./protos/gamemaster.proto
python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. ./protos/set_timeout.proto
python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. ./protos/time_sync.proto
```

Alternatively, you can also execute `./generate_protos.sh` or `./generate_protos.bat` 
script in the root directory.

### Run the processes 

On three separate terminals run:

```bash
python3 node.py <node_id>
```
