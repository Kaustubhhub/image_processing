
import socket

import json

import argparse

import base64

import io

import time

from PIL import Image, ImageFilter

from concurrent.futures import ThreadPoolExecutor





CONFIG_FILE = "config.json"





def load_config():

    with open(CONFIG_FILE, "r") as f:

        return json.load(f)["nodes"]





def receive_all(conn):

    data = b""

    while True:

        chunk = conn.recv(65536)

        if not chunk:

            break

        data += chunk

    return data





def process_image(image_data, operation):

    image = Image.open(io.BytesIO(image_data))



    if operation == "grayscale":

        image = image.convert("L")

    elif operation == "blur":

        image = image.filter(ImageFilter.GaussianBlur(radius=2))

    elif operation == "edge":

        image = image.filter(ImageFilter.FIND_EDGES)



    output = io.BytesIO()

    image.save(output, format="PNG")

    return output.getvalue()





def start_worker(worker_name):

    nodes = load_config()

    port = nodes[worker_name]["port"]



    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server.bind(("0.0.0.0", port))

    server.listen(5)



    print(f"{worker_name} listening on port {port}")



    while True:

        conn, address = server.accept()



        with conn:

            try:

                request = json.loads(receive_all(conn).decode())



                image_data = base64.b64decode(request["image"])

                operation = request["operation"]



                result = process_image(image_data, operation)



                response = {

                    "status": "success",

                    "worker": worker_name,

                    "image": base64.b64encode(result).decode()

                }



                print(f"Processed {operation} request from {address}")



            except Exception as e:

                response = {

                    "status": "error",

                    "message": str(e)

                }



            conn.sendall(json.dumps(response).encode())





def send_task(worker_name, image_data, operation):

    nodes = load_config()

    worker = nodes[worker_name]



    request = {

        "operation": operation,

        "image": base64.b64encode(image_data).decode()

    }



    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    client.settimeout(60)



    try:

        client.connect((worker["host"], worker["port"]))

        client.sendall(json.dumps(request).encode())

        client.shutdown(socket.SHUT_WR)



        response = json.loads(receive_all(client).decode())



        if response["status"] != "success":

            raise Exception(response["message"])



        print(f"{worker_name} completed its task")



        return base64.b64decode(response["image"])



    finally:

        client.close()





def start_master(input_file, operation, output_file):

    image = Image.open(input_file).convert("RGB")



    width, height = image.size

    middle = height // 2



    first_half = image.crop((0, 0, width, middle))

    second_half = image.crop((0, middle, width, height))



    buffer1 = io.BytesIO()

    buffer2 = io.BytesIO()



    first_half.save(buffer1, format="PNG")

    second_half.save(buffer2, format="PNG")



    print("Distributing image chunks to workers...")



    start_time = time.time()



    with ThreadPoolExecutor(max_workers=2) as executor:

        future1 = executor.submit(

            send_task, "worker1", buffer1.getvalue(), operation

        )



        future2 = executor.submit(

            send_task, "worker2", buffer2.getvalue(), operation

        )



        result1 = Image.open(io.BytesIO(future1.result()))

        result2 = Image.open(io.BytesIO(future2.result()))



    final_image = Image.new(result1.mode, (width, height))



    final_image.paste(result1, (0, 0))

    final_image.paste(result2, (0, middle))



    final_image.save(output_file)



    end_time = time.time()



    print("\nProcessing completed successfully")

    print("Operation:", operation)

    print("Output:", output_file)

    print("Image size:", width, "x", height)

    print("Processing time:", round(end_time - start_time, 3), "seconds")





parser = argparse.ArgumentParser()

parser.add_argument("role", choices=["master", "worker"])

parser.add_argument("name")

parser.add_argument("operation", nargs="?")

parser.add_argument("output", nargs="?")



args = parser.parse_args()



if args.role == "worker":

    start_worker(args.name)



elif args.role == "master":

    if not args.operation or not args.output:

        print("Usage: python3 cluster.py master input.png operation output.png")

    else:

        if args.operation not in ["grayscale", "blur", "edge"]:

            print("Invalid operation")

        else:

            start_master(args.name, args.operation, args.output)

