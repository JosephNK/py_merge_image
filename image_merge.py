import asyncio
import pathlib
import uuid

from PIL import Image, ImageSequence


class MergeImage:
    @staticmethod
    async def create_gif(background_file_path: pathlib.Path) -> str:
        # background = Image.open("sample/sample01.png")
        # animated_gif = Image.open("sample/leaves.gif")
        background = Image.open(background_file_path)
        animated_gif = Image.open("sample/leaves.gif")

        duration = animated_gif.info['duration']

        # background_width, background_height = background.size
        animated_gif_width, animated_gif_height = animated_gif.size
        background = background.resize((animated_gif_width, animated_gif_height))

        frames = []
        for frame in ImageSequence.Iterator(animated_gif):
            output = background.copy()
            transparent_foreground = frame.convert('RGBA')
            output.paste(transparent_foreground, (0, 0), mask=transparent_foreground)
            frames.append(output)

        unique_filename = str(uuid.uuid4().hex)

        gif_file_name = unique_filename + '.gif'

        frames[0].save(gif_file_name, save_all=True, append_images=frames[1:], optimize=False, duration=duration)

        return gif_file_name


async def test():
    await MergeImage.create_gif("sample/sample01.jpeg")

if __name__ == "__main__":
    asyncio.run(test())