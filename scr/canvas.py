from matplotlib.axes import Axes
from matplotlib.projections import register_projection
import numpy as np 
import re 

from node import Node,_tg_style,_tg_style_check,get_drawable
from matrix import *
from utilities import to_xy,to_rad,codes_vects_to_segment

RE_find_anchor = r"[a-z|_][a-z|_|\d]*(\.[a-z|_|\d]+)?" # 命名与python变量命名一致

####################################################################################
###         Axes interface                                                       ###
####################################################################################

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
    def get_canvas(self):
        return self.canvas
    
register_projection(CanvasAxes)

####################################################################################
###   end of Axes interface                                                      ###
####################################################################################

class CTX():
    ''' a helper class for Canvas
    
    储存Canvas状态的类''' 
    def __init__(self,*,prev,style:dict,datalim,padding,transform,nodes,unnamed_nodes) -> None:
        self._prev = prev
        self._style = style
        self._datalim = datalim
        self._padding = padding
        self._transform = transform
        self._nodes = nodes
        self._unnammed_nodes = unnamed_nodes
        self._supported_style = set()
        for style_type in _tg_style:
            self._supported_style |= set(_tg_style[style_type])

    @property
    def prev(self):
        return self._prev
    @prev.setter
    def prev(self,xy):
        self._prev = to_xy(xy)
    @property
    def style(self):
        return self._style
    @property
    def datalim(self):
        return self._datalim 
    @property
    def padding(self):
        return self._padding
    @padding.setter
    def padding(self):
        pass 
    @property
    def transform(self):
        return self._transform
    @transform.setter
    def transform(self,mat):
        return self.set_transform(mat)
    @property
    def nodes(self):
        return self._nodes
    @property
    def unnamed_nodes(self):
        return self._unnammed_nodes
    @property
    def supported_style(self):
        return self._supported_style

    def check_style(self,**style):
        _style_checks = _tg_style_check.keys()
        style_dct = {}
        for k,v in style.items(): # k = "total","line",etc.
            if k not in _style_checks: raise TypeError("%s 不是合法的style值")
            v = _tg_style_check[k](**v)
            style_dct.update({k:v})
        return style_dct

    def set_style(self,style_type=None,**style):
        _style_types = _tg_style.keys()
        if style_type is None:
            style_dct = { k:{} for k in _style_types}
            for k in style:
                k_types = []
                for st in _style_types:
                    if k in _tg_style[st]: 
                        k_types.append(st)
                for k_type in k_types:
                    style_dct[k_type].update({k:style[k]})
            style_dct =  self.check_style(**style_dct)
        else:
            style_dct = self.check_style(**{
                style_type:style
            })
        for st in _style_types:
            if st in style_dct:
                self.style[st].update(style_dct[st])

    def set_transform(self,mat):
        mat = check_transform(mat)
        self._transform = mat
    def remove_node(self,nodename):
        if isinstance(nodename,int):
            nd = self.unnamed_nodes[nodename]
            self.unnamed_nodes.remove(nd)
        if isinstance(nodename,slice):
            nd = self.unnamed_nodes[nodename]
            self.unnamed_nodes[nodename] = []
        if isinstance(nodename,str):
            nd = self.nodes.pop(nodename,None)
        if isinstance(nodename,Node):
            nd = nodename
            if nodename in self.nodes.values(): self.nodes.pop(nodename.name)
            if nodename in self.unnamed_nodes: self.unnamed_nodes.remove(nodename)
        if nd is None : return 
        else :
            nd.remove_artists()

    def update_datalim(self,x,y):
        x,y = to_xy((x,y))
        if x is not None:
            if x < self.datalim[0][0] : self.datalim[0][0] = x 
            if x > self.datalim[0][1] : self.datalim[0][1] = x 
        if y is not None: 
            if y < self.datalim[1][0] : self.datalim[1][0] = y 
            if y > self.datalim[1][1] : self.datalim[1][1] = y

    def load_style(self,style_dct,name="total"):
        if name not in self.style.keys(): raise ValueError("%s 不是合法的style type" %name)
        support_keys = (self.style[name] | self.style["total"]).keys() if name != "total" else self.style[name].keys()
        for k in support_keys:
            if k in style_dct: continue
            else: # 使用特定的样式字典填充
                if k in self.style[name] :
                    style_dct[k] = self.style[name][k]
                elif k in self.style["total"]:
                    style_dct[k] = self.style["total"][k]
                else:
                    raise ValueError("没有合适的值用于load %s" % k)
        return style_dct

    def set_datalim(self,xmin=None,ymin=None,xmax=None,ymax=None):
        try:
            if xmin is not None: self.datalim[0][0] = float(xmin)
            if xmax is not None: self.datalim[0][1] = float(xmax) 
            if ymin is not None: self.datalim[1][0] = float(ymin)
            if ymax is not None: self.datalim[1][1] = float(ymax)
        except :
            raise ValueError(f"datalim参数错误")

class Canvas():
    '''绘图的主要接口'''

    def __init__(self,ax) -> None:
        self.ax = ax
        self._ctx = CTX(
            prev=(0,0),
            style = _tg_style,
            datalim = [[0,1],[0,1]],
            padding={"top":1,"bottom":1,"left":1,"right":1},
            transform= np.eye(3,dtype=float),
            nodes={},
            unnamed_nodes=[])
        self._autoscale()

    # POS
    def to_abs_pos(self,pos,_update=True):
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
            return self.to_abs_pos({
                "name":name,
                "anchor":anchor
            })
        if np.array(pos).shape == (0,):
            return self.ctx.prev
        if not isinstance(pos,dict) and np.array(pos).shape == (2,):
            if isinstance(pos[0],str):
                angle = to_rad(pos[0])
                try:
                    radius = float(pos[1])
                except : 
                    raise ValueError(f"{pos[1]}不是合法的radius值")
                return self.to_abs_pos({
                    "angle":angle,
                    "radius":radius
                }) # (angle,radius)
            xy =  to_xy(pos) # (x,y)
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
                to = self.to_abs_pos(pos["to"],_update=False)
            match conflict_num :
                case 1 : 
                    x = 0 if "x" not in pos else pos["x"]
                    y = 0 if "y" not in pos else pos["y"]
                    xy =  to_xy((x,y)) # xy
                case 2 : 
                    if isinstance(pos,dict) and "rel" in pos["rel"]: raise ValueError(f"{pos}rel键嵌套,不允许嵌套")
                    xy =  to + self.to_abs_pos(pos["rel"]) # rel
                case 3 : 
                    angle = 0 if "angle" not in pos else pos["angle"]
                    radius = 0 if "radius" not in pos else pos["radius"]
                    angle = to_rad(angle)
                    xy = to_xy((radius * np.cos(angle),radius * np.sin(angle))) # angle_radius
                case 4 :
                    if "name" not in pos.keys() : raise ValueError("在使用anchor表示法时，必需指定命名")
                    name = pos["name"]
                    if name not in self.ctx.nodes.keys() : raise ValueError(f"Anchor:{name}未找到：尚未注册")
                    anchor = None if "anchor" not in pos.keys() else pos["anchor"]
                    xy =  self.ctx.nodes[name].calculate_anchors(anchor)
                    _has_transform = False
        if _has_transform:
            xy = get_xy_by_transform(self.ctx.transform,xy)
        if update :
            self._update_prev(xy)
        self._update_datalim(*xy) # 更新数据集，每一个pos操作都会更新
        return xy 
    def to_abs_poses(self,*pos,_update=True):
        def _pos(pos):
            return self.to_abs_pos(pos,_update=_update)
        return np.array(list(map(_pos,pos)))
    def to_user_poses(self,*pos):
        def _xy_to_pos(xy):
            return get_xy_by_transform(np.linalg.inv(self.ctx.transform),xy)
        return np.array(list(map(_xy_to_pos,self.to_abs_poses(*pos))))

    # CTX
    @property 
    def ctx(self):
        return self._ctx
    def load_style(self,style_dct,name="total"):
        return self.ctx.load_style(style_dct,name)
    def set_style(self,style_type = None,**style):
        '''更新默认字典的内容,如果style_type被指定，则只会修改对应的样式'''
        return self.ctx.set_style(style_type,**style)
    def _update_prev(self,xy):
        self.ctx.prev = xy
    def moveto(self,pos):
        xy = self.to_abs_pos(pos)
        return self._update_prev(xy)
    ## transform
    def set_transform(self,mat):
        return self.ctx.set_transform(mat)
    def rotate(self,angle):
        rad = to_rad(angle)
        return self.set_transform(get_transform_by_rad(self.ctx.transform,rad))
    def translate(self,v):
        return self.set_transform(get_transform_by_translate(self.ctx.transform,v))
    def scale(self,*,x=1,y=1):
        return self.set_transform(
            get_transform_by_scale(self.ctx.transform,x,y)
        )
    def set_origin(self,x,y):
        return self.set_transform(get_transform_by_origin(self.ctx.transform,x,y))
    def set_viewport(self,a,b,bounds=(1,1)):
        return self.set_transform(get_transform_by_viewport(self.ctx.transform,a,b,bounds))
    
    def _register_node(self,name,node):
        '''注册node，在创建node时使用一次'''
        for a in node.iter_artists():
            self.ax.add_artist(a)
            self._autoscale()
        if name is not None: self.ctx.nodes[name] = node
        else: self.ctx.unnamed_nodes.append(node)
        return node
    def remove(self,name):
        '''可以使用name字符串来remove注册的node，也可以使用int和slice来remove未注册的node，也可以传入Node来删除其artist'''
        return self.ctx.remove_node(name)

    def _update_datalim(self,x=None,y=None):
        '''根据坐标更新ctx.datalim值'''
        return self.ctx.update_datalim(x,y)
    def _set_datalim(self,xmin=None,xmax=None,ymin=None,ymax=None):
        '''直接设置ctx.datalim的值'''
        return self.ctx.set_datalim(xmin,ymin,xmax,ymax)

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
        nodes = list(self.ctx.nodes.values())
        nodes.extend(self.ctx.unnamed_nodes)
        for n in nodes:
            _lim = n.get_lim() 
            self._update_datalim(*_lim[0])
            self._update_datalim(*_lim[1])
        self._autoscale(scalex=scalex,scaley=scaley)
    
    
    # draw
        
    ## 
    @classmethod
    def UnitCircle_CV(self):
        '''返回单位圆的codes和verts,用于计算'''
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
        codes = [1]
        codes.extend([4 for i in range(len(vertices) - 1)])
        return codes,vertices
    @classmethod
    def UnitRect_CV(self):
        codes = [1,2,2,2,2]
        vects = [(0,0),(1,0),(1,1),(0,1),(0,0)]
        return codes,vects
    @classmethod
    def getUnitMark_CV(self,mark_name):
        _replace_dct = {">":"arrow"}
        if mark_name in _replace_dct:
            mark_name = _replace_dct[mark_name]
        match mark_name:
            case "arrow":
                vects = [ (np.cos(np.pi*5/6),np.sin(np.pi*5/6)),(0,0),(np.cos(np.pi/3),np.sin(np.pi/3)) ]
                codes = [ 1,2,2]
                return codes,vects
              
    ## basic drawing api
    def get_path_node(self,*segments,name=None,**style):
        _segments = [[] for i in range(len(segments))]
        for i,seg in enumerate(segments):
            for cmd in seg:
                _cmd = [cmd[0]]
                _cmd.extend(map(self.to_abs_pos,cmd[1:]))
                _segments[i].append(_cmd)
        return self.get_path_node_in_abspos(*_segments,name=name,**style)
    def get_path_node_in_abspos(self,*segment,name=None,**style):
        style = self.load_style(style,name="line")
        node = Node(drawables=[get_drawable("path",segment=seg,**style) for seg in segment],name=name,)
        return node 
    
    ###############################################################
    ###                          绘图api                         ###
    ###############################################################

    def line(self,*pos,name=None,**style):
        node = self.get_path_node([("line",*pos)],name=name,**style)
        self._register_node(name,node)
        return node
    
    def bezier(self,start,end,ctr1,ctr2,name = None,**style):
        node =  self.get_path_node([("cubic",start,end,ctr1,ctr2)],name=name,**style)
        self._register_node(name,node)
        return node

    def rect(self,a,b,name=None,**style):
        a,b = self.to_user_poses(a,b)
        return self.get_path_node([
            ("line",a,(b[0],a[1]),b,(a[0],b[1]),a),
        ],name=name,**style)
    
    def circle(self,center,radius = 1,name=None,**style):
        codes,verts = self.UnitCircle_CV
        center = self.to_user_poses(center)[0]
        verts = verts * radius + center
        segment = codes_vects_to_segment(codes=codes,vects=verts)
        node =  self.get_path_node(segment,name=name,**style)
        self.moveto_xy(center)
        return self._register_node(name,node)
    
    def mark(self,start,to,name=None,**style):
        #style,segment -> drawable, + name -> node
        # 设置style
        style = self._load_default_style(style,name="mark")
        line_style = self._load_default_style(style_dct={"hidden":True},name="line")
        # 设置字段
        start,to = self.to_abs_pos(start),self.to_abs_pos(to)
        angle = (to - start)
        codes,vects = self.getUnitMark_CV(">")
        vects *= 0.1
        vects = self.to_abs_poses(*vects)
        segment = codes_vects_to_segment(codes,to+vects)
        drawables = [] 
        drawables.append(get_drawable(drawtype="path",segment=[("line",start,to)],**line_style))
        drawables.append(get_drawable(drawtype="mark",segment=segment,**style))
        node = Node(drawables=drawables,name=name)
        return self._register_node(name=name,node=node)
        
        



