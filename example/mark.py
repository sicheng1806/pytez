import matplotlib.pyplot as plt 
import sys 
import turtle
sys.path.append("scr")
from canvas import CanvasAxes


if __name__ == '__main__':
    fig,ax = plt.subplots(subplot_kw={"projection":"canvas"})
    cv = ax.canvas
    cv.circle((),radius=10,fill='red')
    plt.show()