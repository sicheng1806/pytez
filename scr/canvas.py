from matplotlib.axes import Axes
from matplotlib.projections import register_projection
from argparse import Namespace
import numpy as np 
import re 
import json

from error import AnchorNameNotFoundError
from scr.argument import standardize_style
from node import Node

RE_find_anchor = r"[a-z|_][a-z|_|\d]*(\.[a-z|_|\d]+)?" # 命名与python变量命名一致
RE_anchor = r"[a-z|_|\d]+" #anchor字符串允许的样式
RE_float = r"-?(\d+(\.\d+)?|\.\d+)"

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
        self.ctx = Namespace(
            nodes={},
            prev=np.array((0,0)),
            style = self._get_style_by_json(".pytez_style.json"),
            xlim=[0,1],ylim=[0,1],
            padding={"top":1,"bottom":1,"left":1,"right":1},
            _other_nodes=[])
        self._autoscale()

    

    def _load_default_style(self,style_dct,support_keys,name=None):
        '''用默认字典填充样式字典'''
        for k in support_keys:
            if k in style_dct: continue
            if name is not None and name in self.ctx.style and k in self.ctx.style[name] and self.ctx.style[name][k] is not None:
                style_dct[k] = self.ctx.style[name][k]
            elif k in self.ctx.style:
                style_dct[k] = self.ctx.style[k]
        return style_dct

    def _get_style_by_json(self,fname):
        _must_keys = ("stroke","fill","hatch","alpha","zorder","hidden","clipon")
        with open(fname,'r') as f:
            dct = json.loads(f.read())
        if not (set(dct)>=set(_must_keys)) : raise ValueError("缺少必要的style键")
        for k in _must_keys:
            dct[k] = standardize_style(k,dct[k])
        return dct

    def pos(self,pos,_update=True):
        '''根据状态返回坐标值,并更新prev状态,
        1. update,to 用于指定是否更新当前位置，坐标参照位置
        2. x,y | angle,radius | name,anchor | 分别代表直角坐标，极坐标，锚点表示法
        3. rel:pos 相对坐标
        '''
        update = _update
        to = self.ctx.prev
        if isinstance(pos,str):
            if not re.fullmatch(RE_find_anchor,pos): raise ValueError("锚点语法错误")
            if "." in pos :
                name,anchor = pos.split(".")
            else:
                name = pos
                anchor = None
            return self.pos({
                "name":name,
                "anchor":anchor,
            })
        if isinstance(pos,dict):
            # 保证键参数正确
            conflict_dct = {"x":1,"y":1,"rel":2,"angle":3,"radius":3,"update":0,"to":0,"name":4,"anchor":4} #通过数字映射完成冲突管理
            conflict_num = 0
            for k in pos.keys():
                if conflict_num != conflict_dct[k]:
                    if  conflict_num * conflict_dct[k] != 0 :
                        raise ValueError()
                    else : conflict_num = conflict_num + conflict_dct[k]
            #                 
            if "update" in pos:
                if not isinstance(pos["update"],bool):
                    raise ValueError("update键必需是bool值")
                update = pos["update"] 
            if "to" in pos:
                to = self.pos(pos["to"],_update=False)
            match conflict_num :
                case 1 : 
                    x = 0 if "x" not in pos else pos["x"]
                    y = 0 if "y" not in pos else pos["y"]
                    try:
                        xy =  np.array((x,y),dtype="float")
                    except:
                        raise TypeError("坐标参数类型错误")
                case 2 : 
                    if isinstance(pos,dict) and "rel" in pos["rel"]: raise ValueError("rel键中不可再嵌套rel")
                    xy =  to + self.pos(pos["rel"])
                case 3 : 
                    angle = 0 if "angle" not in pos else pos["angle"]
                    radius = 0 if "radius" not in pos else pos["radius"]
                    angle = self._parse_arg(angle,"angle") # 
                    xy = np.array((radius* np.cos(angle),radius * np.sin(angle)),dtype="float")
                case 4 :
                    if "name" not in pos.keys() : raise ValueError("在使用anchor表示法时，必需指定命名")
                    name = pos["name"]
                    if name not in self.ctx.nodes.keys() : raise AnchorNameNotFoundError(f"{name}未找到：尚未注册")
                    anchor = None if "anchor" not in pos.keys() else pos["anchor"]
                    xy = self.ctx.nodes[name].calculate_anchors(anchor)
            if update :
                self._update_prev(xy)
            self._update_lim(*xy) # 更新数据集，每一个pos操作都会更新
            return xy # 第一个出口
        try:
            pos = np.array(pos)
        except :
            raise 
        if pos.shape == (0,):     # 输入为 ()，取当前坐标
            return self.ctx.prev #第二个出口
        if pos.shape != (2,):
            raise ValueError("坐标类型必需为2维")
        if isinstance(pos[0],str):
            return self.pos({"angle":pos[0],"radius": float(pos[1])}) # 相当于处理了一下参数又传入字典类型
        return self.pos({"x":pos[0],"y":pos[1]}) 
    
    def _register_node(self,name,node):
        for a in node.iter_artists():
            self.ax.add_artist(a)
            self._autoscale()
        if name is not None: self.ctx.nodes[name] = node
        else: self.ctx._other_nodes.append(node)
        return node

    def _update_lim(self,x=None,y=None):
        if x is not None:
            if x < self.ctx.xlim[0] : self.ctx.xlim[0] = x 
            if x > self.ctx.xlim[1] : self.ctx.xlim[1] = x 
        if y is not None: 
            if y < self.ctx.ylim[0] : self.ctx.ylim[0] = y 
            if y > self.ctx.ylim[1] : self.ctx.ylim[1] = y

    def _set_lim(self,xmin=None,xmax=None,ymin=None,ymax=None):
        if xmin is not None: self.ctx.xlim[0] = xmin 
        if xmax is not None: self.ctx.xlim[1] = xmax 
        if ymin is not None: self.ctx.ylim[0] = ymin
        if ymax is not None: self.ctx.ylim[1] = ymax

    def _update_prev(self,xy):
        try:
            xy = np.array(xy)
        except Exception : 
            raise TypeError()
        if xy.shape == (2,):
            self.ctx.prev = xy
        else:
            raise ValueError()
    
    def _parse_arg(self,value,vtype):
        '''angle 转成弧度制, '''
        match vtype:
            case "angle" : 
                if isinstance(value,float):
                    return np.radians(value)
                elif isinstance(value,str):
                    if re.fullmatch(RE_float+r"deg",value):
                        return np.radians(float(value[:-3]))
                    elif re.fullmatch(RE_float+r"rad",value):
                        return float(value[:-3])
            case _ :
                raise ValueError()

    def _autoscale(self,scalex=True,scaley=True):
        '''使用ctx中的xlim和ylim自动放缩'''
        if scalex:
            self.ax.set_xlim([self.ctx.xlim[0] - self.ctx.padding["left"],self.ctx.xlim[1] + self.ctx.padding["right"]])
        if scaley:
            self.ax.set_ylim([self.ctx.ylim[0] - self.ctx.padding["bottom"],self.ctx.ylim[1] + self.ctx.padding["top"]])

    def autoscale(self,scalex=True,scaley=True):
        '''自动放缩，以适应画面'''
        self.ctx.xlim = [0,1]
        self.ctx.ylim = [0,1]
        nodes = self.ctx.nodes.values().extend(self.ctx._other_nodes)
        for n in nodes:
            _lim = n.get_lim()
            self._update_lim(*_lim[:2])
            self._update_lim(*_lim[2:])
        self._autoscale(scalex=scalex,scaley=scaley)
    
    def set_style(self,name=None,**style):
        '''更新默认字典的内容'''
        _must_standardize = ("fill","stroke","alpha","hidden","zorder")
        if name is None:
            for k,v in style.items():
                if k in _must_standardize: self.ctx.style[k] = standardize_style(k,v)
                else: self.ctx.style[k] = v
        else:
            if name not in self.ctx.style:
                _dct = {}
                for k,v in style.items():
                    if k in _must_standardize: _dct[k] = standardize_style(k,v)
                    else: _dct[k] = v 
                self.ctx.style[name] = _dct
            else:
                for k,v in style.items():
                    if k in _must_standardize: self.ctx.style[name][k] = standardize_style(k,v)
                    else: self.ctx.style[name][k] = v

    def path(self,*segments,name=None,**style):
        support_keys = ("fill","stroke","alpha","zorder","hidden")
        style = self._load_default_style(style,support_keys=support_keys,name="line")
        _segments = [[] for i in range(len(segments))]
        for i,seg in enumerate(segments):
            for cmd in seg:
                _cmd = [cmd[0]]
                _cmd.extend(map(self.pos,cmd[1:]))
                _segments[i].append(_cmd)
        node_dct = {
            "name":name,
            "drawables" : []
        }
        for segment in _segments:
            node_dct["drawables"].append({
                "type":"path",
                "segments": segment,
            } | style )
        node = Node(**node_dct)
        return self._register_node(name,node)

    def _path_by_xy(self,*segments,name=None,**style):
        support_keys = ("fill","stroke","alpha","zorder","hidden")
        style = self._load_default_style(style,support_keys=support_keys,name="line")
        node_dct = {
            "name":name,
            "drawables" : []
        }
        for segment in segments:
            node_dct["drawables"].append({
                "type":"path",
                "segments": segment,
            } | style )
        node = Node(**node_dct)
        return self._register_node(name,node)

    def line(self,*pos,name=None,**style):
        return self.path([("line",*pos)],name=name,**style)

    def bezier(self,start,end,ctr1,ctr2,name = None,**style):
        return self.path([("cubic",start,end,ctr1,ctr2)],name=name,**style)
    
    def rect(self,a,b,name=None,**style):
        a,b = map(self.pos,(a,b))
        return self.path([
            ("line",a,(b[0],a[1]),b,(a[0],b[1]),a),
        ],name=name,**style)

    def circle(self,center,name=None,**style):
        radius = float(style.pop("radius"))
        center = np.array(center)
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
        vertices  = vertices * radius + center
        segment = [["cubic"] for i in  range(8)]
        for i in range(8):
            segment[i].extend([vertices[3*i],vertices[3*i+3],vertices[3*i+1],vertices[3*i+2]])
        return self.path(segment,name=name,**style)

register_projection(CanvasAxes)
