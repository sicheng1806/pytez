from canvas import CanvasAxes
import matplotlib.pyplot as plt

def _test_style():
    _style_dct = dict(stroke="p:r,t:2",fill="red",alpha=0.5)
    fig,ax = plt.subplots(subplot_kw={"projection":"canvas"})
    cv = ax.canvas
    cv.line((0,0),(1,0),**_style_dct)
    cv.set_style(**_style_dct)
    cv.line((0,0),(0,1))
    cv.set_style(stroke="p:k,t:1",alpha=1,fill=None)
    cv.bezier((0,0),(10,3),(5,0),(5,3))
    cv.circle((),radius=1)
    plt.show()

def _test_anchor():
    fig,ax = plt.subplots(subplot_kw={"projection":"canvas"})
    cv = ax.canvas
    anchor_dct = ("start","mid","end","center","north","south","east","west","20%",15,"-30deg")
    cv.rect((0,0),(10,10),name="rect")
    cv.set_style(fill="red")
    for anchor in anchor_dct:
        cv.circle({"name":"rect","anchor":anchor},radius=1)
    plt.show()

def _test_custom():
    pass

if __name__ == '__main__':
    fig,ax = plt.subplots(subplot_kw={"projection":"canvas"})
    cv = ax.canvas
    cv.mark((0,0),(1,1))
    plt.show()