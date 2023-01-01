import os
import PIL
from PIL import Image
import numpy as np
from pathlib import Path

from settings import CONFIG


def convert_image_to_jpg(imageName):
    img = Image.open(imageName)

    rgb_im = img.convert("RGB")

    newImageName = ".".join(imageName.split(".")[:-1]) + ".jpg"
    os.remove(imageName)
    rgb_im.save(newImageName)


if __name__ == "__main__":
    imageName = "/Users/devil/Dev/wordpress/madara_be/Fox_Tech_Solutions.png"
    convert_image_to_jpg(imageName)
    # combine_image(imageName)
    # combine_image("koomanga.jpeg", isLastImg=True)

    # convert_image_to_jpg("images/k.oomanga.jpeg")
