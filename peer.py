
import socket

import json

import argparse

import base64

import tempfile

import subprocess

import sys

import os





def load_config():

    with open("config.json", "r") as f:

        return json.load(f)["nodes"]





def receive_all(conn):

    data = b""

    while True:

        chunk = conn.recv(65536)

        if not chunk:

            break

        data += chunk

    return data





def start_peer(peer_name):

    nodes = load_config()

    port = nodes[peer_name]["port"]



    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server.bind(("0.0.0.0", port))

    server.listen(5)



    print(f"{peer_name} listening on port {port}")



    while True:

        conn, address = server.accept()



        with conn:

            try:

                request = json.loads(receive_all(conn).decode())



                print("Request received from:", address)



                if request.get("action") == "process_image":



                    operation = request["operation"]

                    image_data = base64.b64decode(request["image"])



                    with tempfile.TemporaryDirectory() as temp:

                        input_file = os.path.join(temp, "input.png")

                        output_file = os.path.join(temp, "output.png")



                        with open(input_file, "wb") as f:

                            f.write(image_data)



                        result = subprocess.run(

                            [

                                sys.executable,

                                "cluster.py",

                                "master",

                                input_file,

                                operation,

                                output_file

                            ],

                            capture_output=True,

                            text=True,

                            timeout=120

                        )



                        if result.returncode != 0:

                            raise Exception(result.stderr[-2000:])



                        with open(output_file, "rb") as f:

                            output_data = f.read()



                    response = {

                        "status": "success",

                        "peer": peer_name,

                        "message": "Image processed by cluster",

                        "image": base64.b64encode(output_data).decode()

                    }



                    print("Cluster processing completed")



                else:

                    response = {

                        "peer": peer_name,

                        "status": "success",

                        "resource": "Image processing available"

                    }



                conn.sendall(json.dumps(response).encode())



            except Exception as e:

                response = {

                    "status": "error",

                    "message": str(e)

                }

                conn.sendall(json.dumps(response).encode())





def send_request(source_peer, target_peer):

    nodes = load_config()

    target = nodes[target_peer]



    request = {

        "from": source_peer,

        "message": "Requesting shared resources"

    }



    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    client.settimeout(120)



    try:

        client.connect((target["host"], target["port"]))

        client.sendall(json.dumps(request).encode())

        client.shutdown(socket.SHUT_WR)



        response = json.loads(receive_all(client).decode())

        print(json.dumps(response, indent=4))



    except Exception as e:

        print("Communication failed:", e)



    finally:

        client.close()





def process_request(source_peer, target_peer, image_file, operation):

    nodes = load_config()

    target = nodes[target_peer]



    with open(image_file, "rb") as f:

        image_data = base64.b64encode(f.read()).decode()



    request = {

        "action": "process_image",

        "from": source_peer,

        "operation": operation,

        "image": image_data

    }



    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    client.settimeout(180)



    try:

        print("Sending image-processing request to", target_peer)



        client.connect((target["host"], target["port"]))

        client.sendall(json.dumps(request).encode())

        client.shutdown(socket.SHUT_WR)



        response = json.loads(receive_all(client).decode())



        if response["status"] != "success":

            print("Processing failed:", response["message"])

            return



        output_data = base64.b64decode(response["image"])



        output_file = "peer_result.png"



        with open(output_file, "wb") as f:

            f.write(output_data)



        print("\nRequest completed successfully")

        print("Requesting peer:", source_peer)

        print("Receiving peer:", response["peer"])

        print("Processing:", operation)

        print("Output file:", output_file)

        print(response["message"])



    except Exception as e:

        print("Communication failed:", e)



    finally:

        client.close()





parser = argparse.ArgumentParser()



parser.add_argument(

    "action",

    choices=["listen", "send", "process"]

)



parser.add_argument("peer")

parser.add_argument("target", nargs="?")

parser.add_argument("image", nargs="?")

parser.add_argument("operation", nargs="?")



args = parser.parse_args()



if args.action == "listen":

    start_peer(args.peer)



elif args.action == "send":

    if not args.target:

        print("Specify target peer")

    else:

        send_request(args.peer, args.target)



elif args.action == "process":

    if not args.target or not args.image or not args.operation:

        print("Usage: python3 peer.py process SOURCE TARGET IMAGE OPERATION")

    elif args.operation not in ["grayscale", "blur", "edge"]:

        print("Invalid operation")

    else:

        process_request(

            args.peer,

            args.target,

            args.image,

            args.operation

        )

