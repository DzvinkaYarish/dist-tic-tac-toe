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
cd ./protos
python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. share_id.proto
python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. share_leader.proto
python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. tic_tac_toe_player.proto
python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. tic_tac_toe_gamemaster.proto
```

Alternatively, you can also execute `./generate_protos.sh` or `./generate_protos.bat` 
script in the protos directory.

### Run the processes 

On three separate terminals run:

```bash
python3 node.py
```
