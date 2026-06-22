from reportlab.graphics.barcode import eanbc
from reportlab.graphics import renderPM
from reportlab.graphics.shapes import Drawing

isbn = "9789914357974"  

barcode = eanbc.Ean13BarcodeWidget(isbn)
bounds = barcode.getBounds()
w = bounds[2] - bounds[0]
h = bounds[3] - bounds[1]

d = Drawing(w, h + 20)
d.add(barcode)

out = "/mnt/data/isbn_barcode_9789914357974.png"
renderPM.drawToFile(d, out, fmt="PNG")

print(out)
