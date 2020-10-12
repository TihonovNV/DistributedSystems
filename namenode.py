import os, sys
import shutil
from flask import Flask, request, jsonify, send_from_directory
from flask import Response
import requests
from treelib import Node, Tree
from time import sleep
import io
import json

File_system = Tree()

File_system.create_node("", "")

DATA_NODES = [("localhost", "8000"), ("localhost", "8001")]

down_servers = []

api = Flask(__name__)

def broadcast_command(command, data=""):
    ping_servers()
    for (ip, port) in DATA_NODES:
        if (ip, port) not in down_servers:
            url = f"http://{ip}:{port}" + command
            if (data == ""):
                response = requests.get(url)
            else:
                response = requests.post(url, data=data)
            #api.logger.info(response.content)

def send_file(command, file):
    ping_servers()
    for (ip, port) in DATA_NODES:
        if (ip, port) not in down_servers:
            url = f"http://{ip}:{port}" + command
            files = {'file': file}
            response = requests.post(url, files=files)
            #api.logger.info(response.content)


def get_data(command):
    ping_servers()
    for (ip, port) in DATA_NODES:
        if (ip, port) not in down_servers:
            url = f"http://{ip}:{port}" + command
            return requests.get(url).content
    

def copy_directory(source_ip, source_port, dest_ip, dest_port, path, directory):
    if path and directory:
        new_path = path.strip("/") + "/" +  directory.strip("/")
        new_path = new_path.replace("//", "/").strip('/')

    url = f"http://{source_ip}:{source_port}/dir/list_dir/{new_path}"
    response = requests.get(url)
    #api.logger.info(response.json())
    for directory in response.json()['directories']:
        copy_directory(source_ip, source_port, dest_ip, dest_port, new_path, directory)
        url = f"http://{dest_ip}:{dest_port}/dir/make_dir/" + directory.strip('/')
        requests.get(url)
    for file in response.json()['files']:
        path_for_file = new_path.strip('/') + "/" + file.strip('/')
        path_for_file = path_for_file.replace("//", "/").strip("/")
        url = f"http://{source_ip}:{source_port}/file/read_file/{path_for_file}"
        file = io.BytesIO(requests.get(url).content)
        files = {'file': file}

        url = f"http://{dest_ip}:{dest_port}/file/upload_file/{path_for_file}"
        requests.post(url, files=files)
    

def copy_info(source_ip, source_port, dest_ip, dest_port):
    url = f"http://{dest_ip}:{dest_port}/dir/clear_node/"
    requests.get(url)
    copy_directory(source_ip, source_port, dest_ip, dest_port, "", "")
  
def restore_server(down_ip, down_port):
    for (ip, port) in DATA_NODES:
        if (ip, port) not in down_servers:
            copy_info(ip, port, down_ip, down_port)
            down_servers.remove((down_ip, down_port))
            
        
def ping_servers():
    for (ip, port) in DATA_NODES:
        try:
            requests.get("http://" + ip + ":" + port)
            if (ip, port) in down_servers:
                restore_server(ip, port)
        except Exception:
            down_servers.append((ip, port))

@api.route("/make_dir/", methods=["POST"])
def make_directory():
    """Make a directory"""
    directory_name = request.args.get("directory_name")
    tokens = directory_name.split("/")
    directory = "/".join(tokens[:-1])
    if not File_system.contains(directory):
        return Response("{'Status':'Directory can not be created'}", status=400, mimetype='application/json')
    if not File_system.contains(directory_name):
        broadcast_command("/dir/make_dir/" + directory_name)
        File_system.create_node(f"/{tokens[len(tokens)-1]}", directory_name, parent=directory)
        return Response("{'Status':'Success'}", status=200, mimetype='application/json')
    return Response("{'Status':'Directory already existed'}", status=400, mimetype='application/json')

@api.route("/delete_dir/", methods=["POST"])
def delete_directory():
    directory_name = request.args.get("directory_name")
    print(File_system,file=sys.stderr)
    if not File_system.contains(directory_name):
        return Response("{'Status':'Directory does not exist'}", status=401, mimetype='application/json')
    if File_system.get_node(directory_name).tag[0] != "/":
        return Response("{'Status':'Directory does not exist'}", status=400, mimetype='application/json')
    broadcast_command("/dir/delete_dir/" + directory_name)
    File_system.remove_node(directory_name)
    return Response("{'Status':'Success'}", status=200, mimetype='application/json')

@api.route("/read_dir/")
def list_files():
    "Просто вернуть дерево из неймноды"
    directory_name = request.args.get("directory_name")
    if (File_system.contains(directory_name)):
        return jsonify({"content":[child.tag for child in File_system.children(directory_name)]})
    return Response("{'Status':'Directory does not exist'}", status=400, mimetype='application/json')
    
@api.route("/create/", methods=["POST"])
def make_file():
    filename = request.args.get("filename")
    tokens = filename.split("/")
    directory = "/".join(tokens[:-1])
    if not File_system.contains(directory):
        return Response("{'Status':'File can not be created'}", status=401, mimetype='application/json')
    if not File_system.contains(filename):
        broadcast_command("/file/make_file/" + filename)
        File_system.create_node(f"{tokens[len(tokens)-1]}", filename, parent=directory)
        return Response("{'Status':'Success'}", status=200, mimetype='application/json')
    return Response("{'Status':'File already existed'}", status=400, mimetype='application/json')

@api.route("/delete/", methods=["POST"])
def delete_file():
    filename = request.args.get("filename")
    if not File_system.contains(filename):
        return Response("{'Status':'File does not exist'}", status=400, mimetype='application/json')
    if File_system.get_node(filename).tag[0] == "/":
        return Response("{'Status':'File does not exist'}", status=400, mimetype='application/json')    
    broadcast_command("/file/delete_file/" + filename)
    File_system.remove_node(filename)
    return Response("{'Status':'Success'}", status=200, mimetype='application/json')

@api.route("/write/", methods=["POST"])
def write_file():
    filename = request.form.get("filename")
    target_dir = request.form.get("target_dir")

    if not File_system.contains(target_dir):
        return Response("{'Status':'File can not be created'}", status=401, mimetype='application/json')
    if not File_system.contains(filename):
        if target_dir == "":
            send_file("/file/upload_file/" + filename, file=request.files['file'])
            File_system.create_node(filename, filename, parent=target_dir)
        else:
            send_file("/file/upload_file/" + target_dir + "/" + filename, file=request.files['file'])
            File_system.create_node(filename, target_dir + "/" + filename, parent=target_dir)
        return Response("{'Status':'Success'}", status=200, mimetype='application/json')
    return Response("{'Status':'File already existed'}", status=400, mimetype='application/json')

@api.route("/copy/", methods=["POST"])
def copy_file():
    filename = request.args.get('filename')
    target_dir = request.args.get('target_dir')
    name = filename.split("/")[len(filename.split("/")) - 1]

    if File_system.contains(target_dir + name):
        return Response("{'Status':'File already existed'}", status=400, mimetype='application/json')
    if not File_system.contains(filename):
        return Response("{'Status':'Source file does not exist'}", status=400, mimetype='application/json')
    if not File_system.contains(target_dir):
        return Response("{'Status':'Destination directoty does not exist'}", status=400, mimetype='application/json') 
    if File_system.get_node(filename).tag[0] == '/':
        return Response("{'Status':'Source file does not exist'}", status=400, mimetype='application/json')
    if File_system.get_node(target_dir).tag[0] != '/':
        return Response("{'Status':'Destination directory does not exist'}", status=400, mimetype='application/json')

    data = {
        "from": filename,
        "to": f"{target_dir}/{name}"
    }
    broadcast_command("/file/copy_file/", data=data)
    File_system.create_node(name, target_dir + "/" + name, parent=target_dir)
    return Response("{'Status':'Success'}", status=200, mimetype='application/json')

@api.route("/move/", methods=["POST"])
def move_file():
    filename = request.args.get('filename')
    target_dir = request.args.get('target_dir')
    name = filename.split("/")[len(filename.split("/")) - 1]

    if File_system.contains(target_dir + "/" + name):
        return Response("{'Status':'File already existed'}", status=400, mimetype='application/json')
    if not File_system.contains(filename):
        return Response("{'Status':'Source file does not exist'}", status=400, mimetype='application/json')
    if not File_system.contains(target_dir):
        return Response("{'Status':'Destination directory does not exist'}", status=400, mimetype='application/json')     

    data = {
        "from": filename,
        "to": f"{target_dir}/{name}"
    }

    broadcast_command("/file/move_file/", data=data)

    File_system.remove_node(filename)
    File_system.create_node(name, target_dir + "/" + name, parent=target_dir)
    return Response("{'Status':'Success'}", status=200, mimetype='application/json')

@api.route("/info/")
def info_file():
    filename = request.args.get('filename')

    if not File_system.contains(filename):
        return Response("{'Status':'File does not exits'}", status=401, mimetype='application/json')
    if File_system.get_node(filename).tag[0] == '/':
        return Response("{'Status':'Source file does not exist'}", status=400, mimetype='application/json')

    return get_data("/file/info_file/" + filename)

@api.route("/read/")
def read_file():
    filename = request.args.get('filename')

    if not File_system.contains(filename):
        return Response("{'Status':'File does not exits'}", status=401, mimetype='application/json')
    if File_system.get_node(filename).tag[0] == '/':
        return Response("{'Status':'Source file does not exist'}", status=401, mimetype='application/json')
  
    return get_data("/file/read_file/" + filename)

if __name__ == "__main__":
    api.run(debug=True, port=1337)
    while (True):
        ping_servers()
        sleep(60)