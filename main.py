import asyncio
import cgi
import os
import pathlib
import shutil
import tempfile

from typing import Union
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse
from typing import Callable, cast
from image_merge import MergeImage
from starlette.responses import FileResponse, StreamingResponse

app = FastAPI()


# Main (Html)
@app.get("/")
async def main():
    content = """
<body>
<form action="/uploadfiles/" enctype="multipart/form-data" method="post">
<input name="files" type="file" multiple>
<input type="submit">
</form>
</body>
    """
    return HTMLResponse(content=content)


# Middleware
@app.middleware("http")
async def remove_merge_image_after_response(request: Request, call_next):
    response = await call_next(request)
    if type(StreamingResponse):
        response = cast(StreamingResponse, response)
        headers = response.headers
        if "content-disposition" in headers:
            content_disposition = headers['content-disposition']
            value, params = cgi.parse_header(content_disposition)
            if "filename" in params:
                file_name = params['filename']
                file_path = pathlib.Path().resolve() / file_name
                if os.path.exists(file_path):
                    await asyncio.sleep(0.25)
                    os.remove(file_path)

    return response

# Test
@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

# Test
@app.post("/uploadfiles/")
async def create_upload_files(files: list[UploadFile]):
    file_path, gif_file_name = await merge_upload_files(files)
    return FileResponse(path=file_path, filename=gif_file_name, media_type='application/octet-stream')


# API
@app.post("/api/v1/imageMerge")
async def make_merge_upload_files(files: list[UploadFile]):
    file_path, gif_file_name = await merge_upload_files(files)
    return FileResponse(path=file_path, filename=gif_file_name, media_type='application/octet-stream')


# Functions
async def merge_upload_files(files: list[UploadFile]):
    # temp save files
    temp_file_dicts = []
    for file in files:
        temp_file_dicts.append(await save_image_tmp(file))

    # make dict
    merge_dict = {}
    for temp_file_dict in temp_file_dicts:
        if "tmp_path" in temp_file_dict:
            tmp_path = temp_file_dict['tmp_path']
            if tmp_path:
                extension = pathlib.Path(tmp_path).suffix
                if extension != '.gif':
                    merge_dict['img'] = tmp_path
                else:
                    merge_dict['gif'] = tmp_path

    # merge background image and gif image
    # if 'img' in merge_dict and 'gif' in merge_dict:
    if "img" in merge_dict:
        background_img_file_path = merge_dict['img'].absolute()
        gif_file_name = await MergeImage.create_gif(background_img_file_path)

    # tmp clean
    for temp_file_dict in temp_file_dicts:
        if "tmp_path" in temp_file_dict:
            tmp_path = temp_file_dict['tmp_path']
            if tmp_path:
                tmp_path.unlink()

    # make gif file path
    file_path = pathlib.Path().resolve() / gif_file_name

    return [file_path, gif_file_name]


async def save_image_tmp(upload_file: UploadFile = File(...)):
    tmp_path = save_upload_file_tmp(upload_file)
    return {"tmp_path": tmp_path}


def save_upload_file_tmp(upload_file: UploadFile) -> Path:
    try:
        suffix = Path(upload_file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(upload_file.file, tmp)
            tmp_path = Path(tmp.name)
    finally:
        upload_file.file.close()

    return tmp_path


def save_upload_file(upload_file: UploadFile, destination: Path) -> None:
    try:
        with destination.open("wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
    finally:
        upload_file.file.close()


def handle_upload_file(upload_file: UploadFile, handler: Callable[[Path], None]) -> None:
    tmp_path = save_upload_file_tmp(upload_file)
    try:
        handler(tmp_path)  # Do something with the saved temp file
    finally:
        tmp_path.unlink()  # Delete the temp file
