'''
这个模块实现了pytez的主要接口——Canvas类

此模块和其他模块的关系：

绘图流程决定的关系
========================

图形绘制流程
---------------
1. 用户调用canvas的绘图函数，传入坐标、图形样式、其他mpl参数
2. 由Position类解析传入的坐标，得到绝对数据坐标
3. 由StyleManager类解析传入的样式，得到可直接使用的样式参数
4. 由绝对数据坐标、解析后样式和mpl参数得到相应的图形类
5. 将图形类注册到Canvas.ax的子类中，交由mpl控制绘图
6. 补充: Canvas类的状态由上下文管理器CanvasCTX管理，位置解析和样式解析都需要结合Canvas的状态处理。

图形绘制流程关系
------------------
1. Canvas类需要调用Position类和StyleManager类用于处理数据，Position类和StyleManager类需要调用Canvas类相应的状态属性来处理数据
2. Canvas类使用CanvasCTX类管理状态
3. CanvasCTX类具有PosCTX类用来储存坐标，StyleCTX类储存样式，BasicCTX类储存Canvas的debug和background属性等基本属性。

作图流程
------------

1. 新建Canvas类
2. 绘图
   * 使用绘图方法
   * 设置样式、变换、当前位置等等状态
'''


from matplotlib.axes import Axes
from matplotlib.projections import register_projection
import matplotlib.pyplot as plt 
from .context import CanvasCtx
from .position import parse_pos
from .anchor import Anchor

class CanvasAxes(Axes):
    '''
    一个Canvas类调用的Axes子类，直角坐标系投影，基本与之相同，目前建立这个类，是方便预留投影和预设一些参数
    '''
    name = "canvas"
    def clear(self):
        super().clear()
        self.axis(False)
    def get_canvas(self):
        pass

class _BaseCanvas():
    '''
    Canvas的基类
    '''

class Canvas():
    '''
    用于绘图的主要类，api类processing和ctez。

    Canvas的接口设计
    ====================
    
    属性
    -----
    (为保证安全性,不支持对属性直接修改，须使用对应的方法)

    **数据坐标系统** 

    1. ``_context`` CanvasCTX类型 
       存储变换矩阵、当前坐标、当前样式和debug属性、backgourd属性的上下文管理器
    2. ``_prematrixes`` 列表类型  
       使用过的变换矩阵
    3. ``_maxprematrixes`` int
       变换矩阵序列存储的最大长度，默认15
    4. ``bounds`` (float,float) 
       坐标系的边界值,由_context属性返回
    5. ``curpos`` (float,float)
       当前位置,由_context属性返回
    6. ``transform`` (3,3)数组
       2维坐标系的变换矩阵，由_context属性返回
    7. ``maxprematrixes`` int
       变换矩阵序列存储的最大长度，由_maxprematrixes返回
    8. ``prematrixes`` list
       使用过的变换矩阵，由_prematrixes返回
    
    **样式**

    1. ``curstyle`` dict 
       以字典类型返回当前样式,由_context属性返回
    
    **命名系统和锚点** 

    1. ``_anchors`` dict    
       储存所有锚点的字典
    2. ``anchors`` dict 
       储存所有锚点的字典,由_anchors返回
    3. ``_children`` list 
       储存所有的绘图元素以及锚点类
    4. ``children`` list 
       储存所有的绘图元素以及锚点类，由_children属性返回
    
    **图层和其他属性** 

    1. ``_zorder`` int 
       返回当前所处的图层序号
    2. ``zorder`` int 
       返回当前所处的图层序号,由_zorder类返回
    3. ``_fig`` 
    4. ``fig`` 
    5. ``_ax`` Axes
       返回用于绘图对应的Axes类型
    6. ``ax`` Axes
       返回用于绘图对应的Axes类型，由_ax返回
    8. ``_tmpchildren`` 支持with语句临时储存子类，支持with语句的对象一般是含组的。

    方法
    -------
    **数据坐标系统**

    1. ``get_curpos()`` 返回当前坐标
    2. ``get_origin()`` 返回当前原点在绝对坐标系统的坐标
    3. ``get_ctx`` 返回上下文管理器
    4. ``moveto(pos)`` 设置当前坐标
    5. ``rotate(angle,origin=(0,0))`` 过点绕轴旋转
    6. ``translate(vetc)`` 向向量vetc方向位移
    7. ``scale(x,y)`` 放缩变换
    8. ``set_viewport(from,to,bounds)`` 设置子坐标系
    9. ``set_origin(pos)`` 设置坐标原点
    10. ``set_ctx(mat,style,debug,zorder,background)`` 设置部分上下文

    **样式** 

    1. ``set_style(fill,strick,**style_special)`` 设置当前默认样式
    
    **命名系统与锚点** 

    1. ``get_anchors()`` 返回锚点命名列表
    2. ``anchor(name,pos)`` 设置一个新的指定位置的锚点，类型为Anchor。
    3. ``copy_anchors(element_from,filter=None)`` 从Canvas类复制锚点
    4. ``get_child(name=None,index=None)`` 获取一个注册后的绘图元素，默认返回最后一个元素。
    
    **图层和其他**

    1. ``get_ax()`` 获取Axes
    2. ``set_zorder()`` 设置当前图层序号
    3. ``add_shape()`` 添加图形元素

    **绘图方法**

    1. ``circle``
    2. ``circle_through``
    3. ``arc``
    4. ``arc_through``
    5. ``mark``
    6. ``line`` 
    7. ``grid``
    8. ``text``
    9. ``rect``
    10. ``bezier`` 
    11. ``bezier_through``
    12. ``catmull``
    13. ``hobby``
    15. ``merge_path``
    16. ``intersections``
    17. ``group`` 
    '''
    def __init__(self,
                 fig=None,
                 debug=False,
                 backgroud="w",
                 maxprematrixes = 15,
                 **axes_kw
                 ):
        '''
        参数
        ------
        fig : ``Matplotlib.figure.Figure`` ; 默认为当前figure，如果没有将会自动创建。 
            设置Canvas的figure。

        debug : ``bool`` ; 默认为False 
            是否启用调试模式，若启用将会将图形的画框以红色线条绘制出来。

        backgroud : ``str`` 或者 ``Color`` 
            设置画板的背景色，优先级高于axes的参数
        
        axes_kw : axes的参数设置，具体参见matplotlib.axes.Axes。
        '''
        # 建立与mpl接口
        self._fig = fig if fig else plt.figure()
        axes_kw["projection"] = "canvas" if "canvas" not in axes_kw else axes_kw["projection"]
        self._ax = self.fig.add_subplot(**axes_kw)
        self._contenxt = CanvasCtx(debug=debug,background=backgroud,zorder=0)
        self._prematrixes = [] 
        self._maxprematrixes = maxprematrixes
        self._anchors = {}
        self._children = []
        self._zorder = 0
        self._tmpchildren = []


    # CTX
    @property
    def pos_ctx(self):
        return self._contenxt.get_pos_ctx()
    @property
    def style_ctx(self):
        return self._contenxt.get_style_ctx()
    @property
    def basic_ctx(self):
        return self._contenxt.get_basic_ctx()
    # 坐标系统
    @property
    def bounds(self):
        return self._contenxt.get_bounds()
    @property
    def curpos(self):
        return self._contenxt.get_curpos()
    @property
    def transform(self):
        return self.get_tmat()
    @property
    def maxprematrixes(self):
        return self._maxprematrixes
    @property
    def prematrixes(self):
        return self._prematrixes
    # 样式
    @property
    def curstyle(self):
        return self._contenxt.get_curstyle()
    # 命名系统和锚点
    @property
    def anchors(self):
        return self._anchors
    @property
    def children(self):
        return self._children
    # 图层和其他属性
    @property
    def zorder(self):
        return self._zorder
    @property
    def fig(self):
        return self._fig
    @property
    def ax(self):
        return self._ax 
    
    
    def _parse_anchor(self,anchor:str):
        '''解析锚点'''
        obj,name = anchor.split('.',1)
        if obj not in self.anchors:
            raise AttributeError(f"{anchor} 未注册")
        obj = self.anchors[obj]
        return self.obj.get_anchor(name)

    def parse_position(self,*pos_dct_ls):
        '''将各种表示法的坐标转化为绝对数据坐标系统坐标'''
        for pos_dct in pos_dct_ls:
            if "anchor" in pos_dct:
                yield self._parse_anchor(pos_dct["anchor"])
            else: 
                yield parse_pos(pos_dct=pos_dct,transform=self.transform,curpos=self.curpos)    
    def parse_style(self,style_dct):
        '''将pytez类型的样式和mpl类型的样式转化为无冲突的mpl类型的样式字典,pytez优先'''
        pass
    
    def anchor(self,name,anchor_or_pos):
        '''注册一个新的锚点'''
        if not isinstance(anchor_or_pos,Anchor):
            pos = self.parse_position(anchor_or_pos)
            anchor = Anchor()
            anchor.new_anchor(name,pos)
        else:
            anchor = anchor_or_pos
        self.anchors[name] = anchor
    def _register_shape(self,shape):
        self.ax.add_artist(shape)
        self._children.append(shape)
    def circle(self,position,radius:float|tuple[float,float]=1,name=None,anchor="center",**style_or_kwmpl):
        '''
        绘制一个圆或者椭圆

        参数
        -----
        position : ``位置坐标`` 或者其的列表，具体参见表示位置的方法。
            图案的位置，和anchor共同决定中心的位置。
        
        name : ``str`` ; 默认为None
            图形的命名
        
        radius :  ``float`` or ``(float,float)`` 或者其的列表 ; 默认为1
            圆的半径或者椭圆的长短轴，a表示x轴方向的轴，b表示y轴方向的轴。
        
        anchor: ``锚点字符串`` 或其列表  ， 具体请参考表示锚点的方法 ; 默认为 "center"
            图像的要绘制的锚点位置
        
        **style: style的参数，具体请参考style的参数设置
        '''
        pos = self.parse_position(*position) # 位置点获取，
        kw_mpl = self.parse_style(style_or_kwmpl) # 获取kw_mpl
        _content = Circle(pos,radius=radius,anchor=anchor,**kw_mpl) # 构建
        if name is not None:
            self.anchor(name,_content)
        self._register_shape(_content)

    def set_style(self,
                  fill:str|None,
                  stroke:dict|str,
                  *style_special
                  ):
        '''
        设置画板的样式
        
        参数
        -------
        fill : ``颜色`` ，具体参考表示颜色的方式 ; 默认为None
            图案的默认填充色
        
        stroke : ``stroke参数`` ， 具体参考stroke的参数设置 ; 默认为None
            图案的边界线
        
        style_special : ``dict`` ; 默认为None
            对特定的图案的样式进行设置
        '''
        pass
    

register_projection(CanvasAxes)

if __name__ == '__main__':
    import matplotlib.pyplot as plt
    c = Canvas()
    c.circle((0,0),name="Circle")
    #c.set_style(fill="red",stroke=None)
    #c.circle("circle.east",radius= 0.3)
    plt.show()
