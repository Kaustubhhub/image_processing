
import socket

import json

import base64

import io

import time

import argparse

from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageFilter





def load_config():

    with open("config.json", "r") as f:

        return json.load(f)["nodes"]





def process_image(data, operation):

    image = Image.open(io.BytesIO(data))



    if operation == "grayscale":

        image = image.convert("L")

    elif operation == "blur":

        image = image.filter(ImageFilter.GaussianBlur(radius=2))

    elif operation == "edge":

        image = image.filter(ImageFilter.FIND_EDGES)



    output = io.BytesIO()

    image.save(output, format="PNG")

    return output.getvalue()





def receive_all(conn):

    data = b""

    while True:

        chunk = conn.recv(65536)

        if not chunk:

            break

        data += chunk

    return data





def send_task(worker_name, image_data, operation):

    worker = load_config()[worker_name]



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



        return base64.b64decode(response["image"])



    finally:

        client.close()





def save_image(data, filename):

    with open(filename, "wb") as f:

        f.write(data)





def benchmark(filename, operation):

    image = Image.open(filename).convert("RGB")



    width, height = image.size

    middle = height // 2



    print("Image:", filename)

    print("Size:", width, "x", height)

    print("Operation:", operation)



    # Sequential processing on master

    buffer = io.BytesIO()

    image.save(buffer, format="PNG")



    start = time.time()

    sequential_result = process_image(buffer.getvalue(), operation)

    sequential_time = time.time() - start



    save_image(sequential_result, "sequential_output.png")



    # Divide image into two chunks

    first = image.crop((0, 0, width, middle))

    second = image.crop((0, middle, width, height))



    b1 = io.BytesIO()

    b2 = io.BytesIO()



    first.save(b1, format="PNG")

    second.save(b2, format="PNG")



    # Parallel processing on two workers

    start = time.time()



    with ThreadPoolExecutor(max_workers=2) as executor:

        f1 = executor.submit(

            send_task, "worker1", b1.getvalue(), operation

        )

        f2 = executor.submit(

            send_task, "worker2", b2.getvalue(), operation

        )



        result1 = Image.open(io.BytesIO(f1.result()))

        result2 = Image.open(io.BytesIO(f2.result()))



    final_image = Image.new(result1.mode, (width, height))

    final_image.paste(result1, (0, 0))

    final_image.paste(result2, (0, middle))



    parallel_time = time.time() - start



    final_image.save("parallel_output.png")



    print("\n===== PERFORMANCE COMPARISON =====")

    print("Sequential time:", round(sequential_time, 4), "seconds")

    print("Parallel time:  ", round(parallel_time, 4), "seconds")



    if parallel_time > 0:

        speedup = sequential_time / parallel_time

        print("Speedup:", round(speedup, 3), "x")



    if parallel_time < sequential_time:

        print("Result: Parallel processing was faster")

    else:

        print("Result: Sequential processing was faster")



    print("\nOutput files:")

    print("sequential_output.png")

    print("parallel_output.png")





parser = argparse.ArgumentParser()

parser.add_argument("image")

parser.add_argument("operation", choices=["grayscale", "blur", "edge"])



args = parser.parse_args()



benchmark(args.image, args.operation)

