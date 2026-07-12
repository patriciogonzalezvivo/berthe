from Surface import Surface, Path, convert
import cv2

margin = [10, 10]
marks = 5
image_file = 'contour.png'
scale = 0.55

vector_paths = convert.ImageDrawingToPath(image_file, translate=margin, scale=scale)
coorners = convert.ImageSurfaceCoorners(image_file, translate=margin, scale=scale)

path = Path(vector_paths)
axi = Surface(size='12in x 16in')

for coorner in coorners:
    axi.circle( coorner, marks*0.5)
    axi.line( [coorner[0]-marks, coorner[1]], [coorner[0]+marks, coorner[1]])
    axi.line( [coorner[0], coorner[1]-marks], [coorner[0], coorner[1]+marks])

axi.path( Path(vector_paths).getSimplify(2.0).getSorted())

axi.toSVG('contour.svg')
axi.toPNG('contour_svg.png', scale=4)