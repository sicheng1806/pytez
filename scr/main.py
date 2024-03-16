from canvas import Canvas
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

def test_circle():
    cv = Canvas()
    cv.circle((0,0),anchor="west")
    cv.set_style(style_type="circle",fill='red',stroke=None)
    cv.circle((0,0),radius=0.3)
    cv.set_style("circle",fill=None)
    cv.translate((0,-2.4))
    cv.line((-2,1.2),(2,1.2))
    cv.circle((0,0))
    cv.circle((0,-2),radius=(0.75,0.5))
    plt.show()

def test_circle_through():
    cv = Canvas()
    a,b,c = (0,0),(2,-0.5),(1,1)
    cv.line(a,b,c,a,stroke="p:gray")
    cv.circle_through(a,b,c,name="c")
    cv.circle("c.center",radius=0.05,fill="red")
    plt.show()

def test_arc():
    cv = Canvas()
    cv.set_style("circle",stroke="p:r",alpha=0.5)
    cv.arc((0,0),start=0,delta="70deg",mode="open")
    cv.circle((0,0))

    cv.set_style("arc",mode="pie")
    cv.arc((2,0),start="90deg",delta="30deg",radius = 1.5)
    cv.circle((2,0),radius=1.5)

    cv.arc((4,0),0,"-180deg",mode="close",stroke="p:blue")
    cv.circle((4,0))
    
    cv.arc((6,0),0,"60deg",anchor="30deg")
    cv.circle((6,0))
    plt.show()

def test_arc_through():
    cv = Canvas()
    cv.arc_through((0,1),(1,1),(1,0))
    cv.set_style("circle",radius=0.1,fill='r')
    cv.circle((0,1))
    cv.circle((1,1))
    cv.circle((1,0))
    plt.show()

def test_mark():
    cv = Canvas()
    cv.set_style("mark",scale=3)
    ys = list(range(0,-10,-1))
    symbols = (">","|>","<>","[]","]","|","o","+","x","*")
    assert len(ys) == len(symbols)
    for y,symbol in zip(ys,symbols):
        cv.line((0,y),(1,y))
        cv.mark((0,y),(1,y),symbol=symbol)
    plt.show()
def test_marker():
    cv = Canvas()
    #cv.marker((0,0),(1,1))
    #cv.marker((-1,-1),(2,2),symbol=[("line",(0,0),(1,0),(1,1),(0,1),(0,0))])
    #
    cv.set_style("mark",scale=3)
    ys = list(range(0,-10,-1))
    symbols = (">","|>","<>","[]","]","|","o","+","x","*")
    assert len(ys) == len(symbols)
    for y,symbol in zip(ys,symbols):
        cv.marker((0,y),symbol=symbol)
    plt.show()

def test_line():
    cv = Canvas()
    cv.set_style("line",mark={"symbol":"o"})
    cv.line((-1.5,0),(1.5,0))
    cv.line((0,-1.5),(0,1.5))
    cv.line((-1, -1), (-0.5, 0.5), (0.5, 0.5), (1, -1),(-1,-1))
    plt.show()

def test_bezier():
    cv = Canvas()
    a,b,c = ((0, 0), (2, 0), (1, 1))
    cv.line(a, c, b, stroke="p:gray")
    cv.bezier(a, b, c)
    a,b,c,d = ((0, -1), (2, -1), (.5, -2), (1.5, 0))
    cv.line(a, c, d, b, stroke="p:gray")
    cv.bezier(a, b, c, d)
    plt.show()
def test_bezier_through():
    cv = Canvas()
    a,b,c = ((0, 0), (1, 1), (2, -1))
    cv.line(a, b, c, stroke="p:gray")
    cv.bezier_through(a, b, c, name="b")
    
    cv.line(a, "b.ctrl-0", "b.ctrl-1", c, stroke="p:gray")
    plt.show()

if __name__ == '__main__':
    test_bezier_through()