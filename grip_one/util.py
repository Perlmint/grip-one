""" util functions """
from os.path import join, splitext
import mimetypes
from binascii import b2a_base64

def embed_image(root, img_src):
	""" embed image with base64 encoded """
	img_ext = splitext(img_src)[1]
	img_mime = mimetypes.types_map[img_ext]
	img = {}

	with open(join(root, img_src), "rb") as img_file:
		data = b2a_base64(img_file.read()).decode("utf-8")
		img["src"] = "data:{0};base64,{1}".format(img_mime, data)
		img["alt"] = img_src

	return img
