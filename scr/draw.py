'''
这个模块定义了许多用于绘画的函数
'''

import matplotlib.patches as mpatch
from matplotlib.typing import CapStyleType, ColorType, JoinStyleType, LineStyleType 
from .anchor import Anchor

__all__ = ["BaseShape","Circle","Arc","Mark",
           "Line","Grid","Text","Rect","Bezier",
           "Catmull","Hobby","MergePath",
           ]

class BaseShape(mpatch.Patch,Anchor):
    '''
    形状基类，用于支持锚点，样式

    方法
    ------
    
    '''
    def __init__(self,pos,style,**kw_mpl) -> None:
        mpl_kw = self.init_shape(pos,style,kw_mpl)
        super().__init__(**kw_mpl)
        super(Anchor,self).__init__()
        self.init_anchor()
    def init_anchor(self):
        '''初始化轴'''
        pass
    def init_shape(self,pos,style,kw_mpl):
        ''''''


class Circle():
    '''
    圆心和半径确定或三点确定的圆或椭圆
    '''
    def __init__(self) -> None:
        pass

class Rect():
    '''
    对角点确定的矩形
    '''
