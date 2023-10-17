import io

from celery import Celery
from celery.result import AsyncResult
from flask import Flask, jsonify, request, send_file
from upscale import upscale

from config import BACKEND, BROKER

app = Flask("app")
celery_app = Celery(app.import_name, broker=BROKER, backend=BACKEND)
celery_app.conf.accept_content = ["msgpack"]
celery_app.conf.result_accept_content = ["msgpack"]
celery_app.conf.result_serializer = "msgpack"
celery_app.conf.task_serializer = "msgpack"


class ContextTask(celery_app.Task):
    def __call__(self, *args, **kwargs):
        with app.app_context():
            return self.run(*args, **kwargs)


celery_app.Task = ContextTask


@celery_app.task(serializer="msgpack")
def create_upscale_task(image_bytes: bytes):
    return upscale(image_bytes)


def upscale_image():
    img_file = request.files["image"]
    image_bytes = img_file.stream.read()

    task = create_upscale_task.delay(image_bytes)

    return jsonify({"task": task.id})


def check_task(task_id: str):
    result = AsyncResult(task_id, app=celery_app)
    response = {"status": result.status}
    if result.status == "SUCCESS":
        response["link"] = f"/processed/{task_id}/upscaled.jpg"
    return jsonify(response)


def download_file(task_id: str):
    result = AsyncResult(task_id, app=celery_app)
    if result.status != "SUCCESS":
        response = jsonify({"message": "not ready", "status": result.status})
        response.status_code = 423
        return response

    file = io.BytesIO(result.result)
    file.seek(0)
    return send_file(file, mimetype="image/jpeg", download_name="upscaled.jpg")


app.add_url_rule("/upload", view_func=upscale_image, methods=["POST"])
app.add_url_rule("/tasks/<string:task_id>", view_func=check_task, methods=["GET"])
app.add_url_rule(
    "/processed/<string:task_id>/upscaled.jpg", view_func=download_file, methods=["GET"]
)
