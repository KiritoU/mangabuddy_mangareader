import os
import PIL
from PIL import Image
import numpy as np
from pathlib import Path

from settings import CONFIG


def resizeBrandImg(crwImgName: str, isLastImg: bool = False) -> Image:
    crwImg = PIL.Image.open(crwImgName)
    # imgExtension = crwImg.format.lower()
    crwImgWidth, crwImgHeight = crwImg.size

    brandImgName = CONFIG.BRAND_TOP_IMG_NAME
    if isLastImg:
        brandImgName = CONFIG.BRAND_BOTTOM_IMG_NAME

    brandImg = PIL.Image.open(brandImgName)
    brandWidth, brandHeight = brandImg.size

    newBrandWidth = crwImgWidth
    newBrandHeight = int(brandHeight * crwImgWidth / brandWidth)

    return brandImg.resize(
        (newBrandWidth, newBrandHeight)
    )  # , Image.Resampling.LANCZOS)


def combine_image(crwImgName: str, isLastImg: bool = False):
    if isLastImg:
        imgs = [PIL.Image.open(crwImgName), resizeBrandImg(crwImgName, isLastImg=True)]
    else:
        imgs = [resizeBrandImg(crwImgName), PIL.Image.open(crwImgName)]

    imgs_comb = np.vstack([np.asarray(i) for i in imgs])
    imgs_comb = PIL.Image.fromarray(imgs_comb)
    imgs_comb.save(crwImgName)


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
