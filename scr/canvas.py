from matplotlib.axes import Axes
from matplotlib.projections import register_projection
from argparse import Namespace
import numpy as np 
import re 
import json

from argument import standardize_style_dct,standardize_xy,standardiz_angle,get_drawable
from matrix import get_transformed_xy
from node import Node

from argument import DefaultStyleValue,RE_find_anchor

class CanvasAxes(Axes):
    '''在Axes的基础上增加了canvas属性用于作为cetz风格的绘图接口
    '''
    name = "canvas"
    def __init__(self, fig,
                 *args,
                 facecolor=None,  # defaults to rc axes.facecolor
                 frameon=True,
                 sharex=None,  # use Axes instance's xaxis info
                 sharey=None,  # use Axes instance's yaxis info
                 label='',
                 xscale=None,
                 yscale=None,
                 box_aspect=None,
                 **kwargs
                 ):
        super().__init__(fig, *args, facecolor=facecolor, frameon=frameon, sharex=sharex, sharey=sharey, label=label, xscale=xscale, yscale=yscale, box_aspect=box_aspect, **kwargs)
        self.set_aspect("equal")
        self.grid(False)
        self.xaxis.set_visible(False)
        self.yaxis.set_visible(False)
        self.canvas = Canvas(self)
    
class Canvas():
    '''绘图的主要接口'''

    def __init__(self,ax) -> None:
        self.ax = ax
        self._ctx = Namespace(
            prev=(0,0),
            style = self._get_style_by_json(".pytez_style.json"),
            datalim = [[0,1],[0,1]],
            padding={"top":1,"bottom":1,"left":1,"right":1},
            transform= np.eye(3,dtype=float),
            nodes={},
            _unnamed_nodes=[])
        self._autoscale()

    # ctx不可更改
    @property 
    def ctx(self):
        return self._ctx
    # style 管理
    def _get_style_by_json(self,fname):
        with open(fname,'r') as f:
            style = json.loads(f.read())
        return standardize_style_dct(style_dct=style)

    def _load_default_style(self,style_dct,support_keys,name=None):
        '''用默认字典填充样式字典'''
        for k in support_keys:
            if k in style_dct: continue
            if name is not None and name in self.ctx.style and k in self.ctx.style[name] and self.ctx.style[name][k] is not None:
                style_dct[k] = self.ctx.style[name][k]
            elif k in self.ctx.style:
                style_dct[k] = self.ctx.style[k]
        return style_dct
    
    def set_style(self,**style):
        '''更新默认字典的内容'''
        style = self.ctx | style
        return standardize_style_dct(style)
    
    # 位置管理
    def pos(self,pos,_update=True):
        '''根据状态返回坐标值,并更新prev状态,
        1. update,to 用于指定是否更新当前位置，坐标参照位置
        2. x,y | angle,radius | name,anchor | 分别代表直角坐标，极坐标，锚点表示法
        3. rel:pos 相对坐标
        '''
        update = _update
        _has_transform = True
        to = self.ctx.prev
        if isinstance(pos,str): #锚点字符串
            if not re.fullmatch(RE_find_anchor,pos): raise ValueError(f"{pos}不是支持的锚点值，锚点格式错误")
            if "." in pos :
                name,anchor = pos.split(".")
            else:
                name = pos
                anchor = None
            return self.pos({
                "name":name,
                "anchor":anchor
            })
        if np.array(pos).shape == (0,):
            return self.ctx.prev
        if not isinstance(pos,dict) and np.array(pos).shape == (2,):
            if isinstance(pos[0],str):
                angle = standardiz_angle(pos[0])
                try:
                    radius = float(pos[1])
                except : 
                    raise ValueError(f"{pos[1]}不是合法的radius值")
                return self.pos({
                    "angle":angle,
                    "radius":radius
                }) # (angle,radius)
            xy =  standardize_xy(pos) # (x,y)
        if isinstance(pos,dict):
            # 保证键参数正确
            conflict_dct = {"x":1,"y":1,"rel":2,"angle":3,"radius":3,"update":0,"to":0,"name":4,"anchor":4} #通过数字映射完成冲突管理
            conflict_num = 0
            for k in pos.keys():
                if conflict_num != conflict_dct[k]:
                    if  conflict_num * conflict_dct[k] != 0 :
                        raise ValueError(f"{pos}含有互斥的键")
                    else : conflict_num = conflict_num + conflict_dct[k]          
            if "update" in pos:
                if not isinstance(pos["update"],bool):
                    raise ValueError(f"{pos}不是支持的update键，必须为bool类型")
                update = pos["update"] and _update
            if "to" in pos:
                if "to" in pos["to"] : raise ValueError(f"{pos}to键嵌套,不允许嵌套")
                to = self.pos(pos["to"],_update=False)
            match conflict_num :
                case 1 : 
                    x = 0 if "x" not in pos else pos["x"]
                    y = 0 if "y" not in pos else pos["y"]
                    xy =  standardize_xy((x,y)) # xy
                case 2 : 
                    if isinstance(pos,dict) and "rel" in pos["rel"]: raise ValueError(f"{pos}rel键嵌套,不允许嵌套")
                    xy =  to + self.pos(pos["rel"]) # rel
                case 3 : 
                    angle = 0 if "angle" not in pos else pos["angle"]
                    radius = 0 if "radius" not in pos else pos["radius"]
                    angle = standardiz_angle(angle)
                    xy = standardize_xy((radius * np.cos(angle),radius * np.sin(angle))) # angle_radius
                case 4 :
                    if "name" not in pos.keys() : raise ValueError("在使用anchor表示法时，必需指定命名")
                    name = pos["name"]
                    if name not in self.ctx.nodes.keys() : raise ValueError(f"Anchor:{name}未找到：尚未注册")
                    anchor = None if "anchor" not in pos.keys() else pos["anchor"]
                    xy =  self.ctx.nodes[name].calculate_anchors(anchor)
                    _has_transform = False
        if _has_transform:
            xy = get_transformed_xy(self.ctx.transform,xy)
        if update :
            self._update_prev(xy)
        self._update_datalim(*xy) # 更新数据集，每一个pos操作都会更新
        return xy 
    ## prev
    def _update_prev(self,xy):
        self.ctx.prev = standardize_xy(xy)
    def moveto(self,pos):
        xy = self.pos(pos)
        return self._update_prev(xy)
    def moveto_xy(self,xy):
        return self._update_prev(xy)
    # ax交互管理
    def _register_node(self,name,node):
        '''注册node，在创建node时使用一次'''
        for a in node.iter_artists():
            self.ax.add_artist(a)
            self._autoscale()
        if name is not None: self.ctx.nodes[name] = node
        else: self.ctx._unnamed_nodes.append(node)
        return node
    ## datalim
    def _update_datalim(self,x=None,y=None):
        '''根据坐标更新ctx.datalim值'''
        if x is not None:
            if x < self.ctx.datalim[0][0] : self.ctx.datalim[0][0] = x 
            if x > self.ctx.datalim[0][1] : self.ctx.datalim[0][1] = x 
        if y is not None: 
            if y < self.ctx.datalim[1][0] : self.ctx.datalim[1][0] = y 
            if y > self.ctx.datalim[1][1] : self.ctx.datalim[1][1] = y

    def _set_datalim(self,xmin=None,xmax=None,ymin=None,ymax=None):
        '''直接设置ctx.datalim的值'''
        try:
            if xmin is not None: self.ctx.datalim[0][0] = float(xmin)
            if xmax is not None: self.ctx.datalim[0][1] = float(xmax) 
            if ymin is not None: self.ctx.datalim[1][0] = float(ymin)
            if ymax is not None: self.ctx.datalim[1][1] = float(ymax)
        except :
            raise ValueError(f"datalim参数错误")
    
    ## autoscale
    def _autoscale(self,scalex=True,scaley=True):
        '''使用ctx中的xlim和ylim自动放缩'''
        if scalex:
            self.ax.set_xlim([self.ctx.datalim[0][0] - self.ctx.padding["left"],self.ctx.datalim[0][1] + self.ctx.padding["right"]])
        if scaley:
            self.ax.set_ylim([self.ctx.datalim[1][0] - self.ctx.padding["bottom"],self.ctx.datalim[1][1] + self.ctx.padding["top"]])
    def autoscale(self,scalex=True,scaley=True):
        '''自动放缩，以适应画面'''
        self.ctx.datalim[0] = [0,1]
        self.ctx.datalim[1] = [0,1]
        nodes = self.ctx.nodes.values().extend(self.ctx._unnamed_nodes)
        for n in nodes:
            _lim = n.get_lim() 
            self._update_datalim(*_lim[0])
            self._update_datalim(*_lim[1])
        self._autoscale(scalex=scalex,scaley=scaley)
    
    # 绘图api
    def path(self,*segments,name=None,**style):
        support_keys = DefaultStyleValue.keys()
        style = self._load_default_style(style,support_keys=support_keys,name="line")
        _segments = [[] for i in range(len(segments))]
        for i,seg in enumerate(segments):
            for cmd in seg:
                _cmd = [cmd[0]]
                _cmd.extend(map(self.pos,cmd[1:]))
                _segments[i].append(_cmd)
        node = Node(drawables=[get_drawable(drawtype="path",segments=seg,**style) for seg in _segments],name=name,)
        return self._register_node(name,node)

    def path_by_xy(self,*segments,name=None,**style):
        support_keys = DefaultStyleValue.keys()
        style = self._load_default_style(style,support_keys=support_keys,name="line")
        node = Node(drawables=[get_drawable(drawtype="path",segments=seg,**style) for seg in segments],name=name,)
        return self._register_node(name,node)

    def line(self,*pos,name=None,**style):
        return self.path([("line",*pos)],name=name,**style)

    def bezier(self,start,end,ctr1,ctr2,name = None,**style):
        return self.path([("cubic",start,end,ctr1,ctr2)],name=name,**style)
    
    def rect(self,a,b,name=None,**style):
        a,b = map(self.pos,(a,b))
        return self.path_by_xy([
            ("line",a,(b[0],a[1]),b,(a[0],b[1]),a),
        ],name=name,**style)

    def circle(self,center,radius = 1,name=None,**style):
        MAGIC = 0.2652031
        SQRTHALF = np.sqrt(0.5)
        MAGIC45 = SQRTHALF * MAGIC

        vertices = np.array([[0.0, -1.0],
                             [MAGIC, -1.0],
                             [SQRTHALF-MAGIC45, -SQRTHALF-MAGIC45],
                             [SQRTHALF, -SQRTHALF],

                             [SQRTHALF+MAGIC45, -SQRTHALF+MAGIC45],
                             [1.0, -MAGIC],
                             [1.0, 0.0],

                             [1.0, MAGIC],
                             [SQRTHALF+MAGIC45, SQRTHALF-MAGIC45],
                             [SQRTHALF, SQRTHALF],

                             [SQRTHALF-MAGIC45, SQRTHALF+MAGIC45],
                             [MAGIC, 1.0],
                             [0.0, 1.0],

                             [-MAGIC, 1.0],
                             [-SQRTHALF+MAGIC45, SQRTHALF+MAGIC45],
                             [-SQRTHALF, SQRTHALF],

                             [-SQRTHALF-MAGIC45, SQRTHALF-MAGIC45],
                             [-1.0, MAGIC],
                             [-1.0, 0.0],

                             [-1.0, -MAGIC],
                             [-SQRTHALF-MAGIC45, -SQRTHALF+MAGIC45],
                             [-SQRTHALF, -SQRTHALF],

                             [-SQRTHALF+MAGIC45, -SQRTHALF-MAGIC45],
                             [-MAGIC, -1.0],
                             [0.0, -1.0],
                            ],
                            dtype=float)
        center = self.pos(center)
        vertices  = np.array(list(map(self.pos,vertices * radius))) + center
        segment = [["cubic"] for i in  range(8)]
        for i in range(8):
            segment[i].extend([vertices[3*i],vertices[3*i+3],vertices[3*i+1],vertices[3*i+2]])
        node =  self.path_by_xy(segment,name=name,**style) # 生成且注册
        self.moveto_xy(center)
        return node
        

register_projection(CanvasAxes)