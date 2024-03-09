import matplotlib.pyplot as plt 
from canvas import CanvasAxes,Canvas

def _test_pos():
    '''测试直角坐标、极坐标和相对坐标的输入情况'''
    fig = plt.figure()
    ax = fig.add_subplot(projection="canvas")
    cv = ax.canvas
    cv.circle((10,10)) # (10,10)
    cv.circle({"x":10}) # (10,0)
    cv.circle({"y":10}) # (0,10)
    cv.circle({"angle":"30deg","radius":10}) # (5sqrt(3),5)
    cv.circle(("60deg",10)) # (5,5sqrt(3))
    cv.circle({"x":5,"y":5}) # (5,5)
    cv.circle({"rel":(-5,-5)}) # (0,0)
    cv.rect([0,0],[10,10])
    cv.autoscale()
    plt.show()

def _test_anchor():
    '''测试锚点的使用'''
    fig = plt.figure()
    ax = fig.add_subplot(projection="canvas")
    cv = ax.canvas
    # 测试pos的锚点调用
    cv.line((0,0),(1,0),(1,1),(0,1),name = "line")
    cv.line("line.start","line.end") # start,mid = (0,0) , (0.1)
    # 测试center是否准确
    cv.line((0,0),(4,0),(4,4),(0,4),(0,0),name = "line2")
    c = (2,2)
    print(f"{cv.pos("line2.center")} == {c}")
    # 测试锚点的各种调用
    for anchor in ("east","start","mid","end","center","north","south","west","30deg","30%",6):
        pos = cv.pos({"name":"line2","anchor":anchor})
        print(f"line2 anchor:{anchor} => {pos}")
    # 测试贝塞尔曲线的锚点
    cv.bezier((0,0),(10,3),(5,0),(5,3),name = "bezier")
    for anchor in ("start","mid","end","30%",6):
        print(f"bezier anchor:{anchor} => {cv.pos({"name":"bezier","anchor":anchor})}")
    plt.show()

def _test_node_style():
    fig = plt.figure()
    ax = fig.add_subplot(projection="canvas")
    cv = ax.canvas
    # 测试stroke字典输入
    cv.line((0,0),(1,0),(1,1),(0,1),stroke={"paint":"red","thickness":3,"cap":"round","dash":"dashed","join":"round"})
    # 测试其他样式输入
    cv.line((0,1),(0,0),stroke={"thickness":5})
    cv.line((0,0),(5,0),(5,5),(0,5),(0,0),fill = "blue",alpha=0.3)
    # 测试stroke字符输入
    cv.line((2,2),(4,4),stroke="p:red")
    cv.line((4,2),(2,4),stroke="p:yellow,t:10,c:round")
    cv.bezier((0,0),(6,4),(3,0),(3,4),stroke="p:red,t:10,c:round")
    plt.show()

def _main():
    fig = plt.figure()
    ax = fig.add_subplot(projection="canvas")
    cv = ax.canvas
    cv.bezier((0,0),(10,3),(5,0),(5,3))
    cv.bezier((10,10),(15,15),(12,10),(12,15))
    cv.line((0,0),(10,1),(5,3))
    plt.show()

if __name__ == '__main__':
    pass
    