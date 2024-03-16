'''
此模块提供Node类和Drawable类，Drawable可以视为maplotlib内的一个artist，node则是Drawable的集合并在其基础上添加了锚点功能。

关于自定义Drawable和Style的说明
====================================

自定义Drawable允许扩展各类artist至pytez。

自定义Drawable的方法是继承Drawable类，并设置drawtype、和style_types两个类属性，前者为Drawable的类型或者叫名字，用于支持get_drawable方法调用其，后者为drawable支持的style类型，需是个元组。
Drawable会根据style_types的值生成对style参数的check函数，确保style参数正确。此外还需要实现get_anchor_segement(提供node锚点计算所需的segment),_get_artist(生成matplotlib的类)
_style_to_mpl_kwargs(用于在设置Drawable样式时将样式参数转换为mpl参数，即生成的artist的set函数可以接收的参数)，最后将自定义的类通过register_drawable(your_drawable_cls)注册即可使用。

自定义style允许扩展自己定义的样式

自定义样式需要通过 register_style(name,default_style,style_check)函数来设置。name是样式的名称，default_style是默认样式，style_check是检查样式合法性的函数。

自定义样式的核心在于设置style_check函数。注册过得check函数会在两处地方被使用，第一处是指定了 style_types中含有样式名的Drawable类在初始化和设置样式的时候会使用，第二处是
在调用Canvas.set_style函数时会使用，用于检查样式设置的正确性。

注意事项
---------

1. 样式主要用于生成Drawable类，和设置Drawable类的样式过程中。因而check函数通用的定义形式为：

   ``` def check_your_style(**style) -> style_dict ```

2. 如果我的样式值为字典类型，可以只输入部分值嘛，check函数该如何设置？

   取决与check 函数的设置，如果你的check函数会自动补全缺失的键，那么在Drawable调用时不会出现问题。但是在设置样式时CTX样式对应的残缺的值会被默认值取代。
   而在load_style中支持字典样式值的自动补全。可以保证设置的样式值作用于生成的Drawable类。

   如果check 函数不会自动补全缺失的键，那么可以认为样式值是残缺的，不安全的，此时如果Drawable类没有自动补全机制，那么Drawable无法正常使用，而set_style也同理。
   因此，在check函数会自动补全的情况下，可以只输入部分值。check函数没有自动补全，则认为只支持完整的字典值。

3. check函数如何设置

    check函数接收预定的样式，且返回预定样式完整的值。
'''


import matplotlib.patches as mpatch
from matplotlib.path import Path
import re 
import numpy as np 
from matplotlib.colors import to_rgba
from abc import abstractmethod,ABC
from types import FunctionType

from utilities import segment_to_CV,to_xy,to_rad,codes_vects_to_segment,check_segment,getUnitCircle_CV
from bezier import segment_to_coefs,coefs_to_center,coefs_to_area,coefs_to_length_and_nodeweight,get_bezier_point,bezier_line_intersection
from matrix import get_transform_by_rad,get_transform_by_reverse,get_xy_by_transform

##############################################################################
###             Drawable: 与artist的接口类                                  ###
###          可以通过自定义Drawable类扩展绘图的类型                            ###
#############################################################################

## 设置对样式的支持和检查函数,支持扩展
## style检查函数会同时在drawable 以及 canvas使用

RE_float = r"-?(\d+(\.\d+)?|\.\d+)"
RE_node_name= RE_anchor_name = r"[a-z|_|\d][a-z|_|\d|-]*"

_tg_style = {
    "total" : {
        "hidden" : False,
        "alpha" : 1,
        "zorder" : None,
        "clipon" : True
    },
    "path" : {
        "fill" : None,
        "hatch" : None,
        "stroke" : None,
    },
}

def check_total(**style):
    for k,v in style.items():
        match k,k :
            case ("hidden" | "clipon",name) : 
                if not isinstance(v,bool) :  raise ValueError("%s not a value of bool, %s 's value must be bool" %(v,name))
            case "alpha",name : 
                try:
                    v = float(v) 
                    if not 0 <= v <= 1 : raise ValueError("%s must be a number between 0 - 1" % name)
                except Exception as e:
                    raise ValueError("%s is a bad value for %s : %s" % (v,name,e))
            case "zorder",name : 
                if v is None : pass 
                else:
                    try: 
                        v = int(v)
                    except :
                        raise ValueError("%s:%s must be a int" % (name,v))
            case _ :
                raise ValueError("%s is not a value that %s supportes" %(k,"total") )
        style[k] = v 
    return style

def _check_stroke(stroke):
    '''将stroke标准化为键完全的stroke字典'''
    _default_stoke = {"paint":(0,0,0),"thickness":1,"cap":"butt","dash":"solid","join":"miter"}
    _cap_str = ("butt","projecting","round",None,"square")
    _join_str = ("miter","round","bevel",None)
    _dash_str = ("-","--","-.",":","none","solid","dashed","dashdot","dotted","None",' ','',None,"dashed-dotted")
    if stroke is None : return _default_stoke
    if isinstance(stroke,str): # c:r,t:2,cap:round,dash:round,join:round
        args = stroke.split(",")
        args = [arg for arg in args if ":" in arg]
        stroke_dct = {}
        for  arg in args:
            arg = arg.split(":")
            if len(arg) != 2: raise ValueError(f"stroke格式错误{arg[0]:{arg[1:]}}")
            k,v = arg 
            if k == "p" : k = "paint"
            elif k in ("t","width","w") : k = "thickness"
            elif k == "d" : k = "dash"
            elif k == "j" : k = "join"
            elif k == "c" : k = "cap"
            elif k not in _default_stoke: raise ValueError(f"{k}并非stroke的键")
            stroke_dct[k] = v 
        return _check_stroke(stroke_dct)
    elif isinstance(stroke,dict):
        if not (set(stroke) <= set(_default_stoke)): raise ValueError(f"{stroke}存在不支持的stroke键，支持的键有{tuple(_default_stoke.keys())}")
        stroke = _default_stoke | stroke
        for k,v in stroke.items():
            match k : 
                case "paint":
                    if v is not None: v = to_rgba(v)  # 允许 paint的值为 None表示什么都不画
                case "thickness":
                    try:
                        v = float(v) 
                    except Exception:
                        raise ValueError(f"{v}不是能表示thickness的值")
                case "cap":
                    if v == None: v = "butt" # cap的值为None，取默认值 butt
                    if v == "square" : v = "projecting" # 允许square表示 projecting
                    if v not in _cap_str: raise ValueError(f"{v}不是合法的cap值,合法值：{_cap_str}")
                case "dash":
                    if v == None : v = "solid" # None取默认值solid
                    if v == "dashed-dotted": v = "dashdot" # dashed-dotted表示dashdot
                    if v not in _dash_str: raise ValueError(f"{v}不是合法的dash值,合法值有:{_dash_str}")
                case "join":
                    if v == None: v = "miter" # None取默认值 miter
                    if v not in _join_str: raise ValueError(f"{v}不是合法的join值,合法值:{_join_str}")
            stroke[k] = v
        return stroke
    else:
        raise TypeError(f"{stroke}类型错误,支持的stroke类型为stroke_str和字典类型")

def check_path(**style):
    _hatch_str = ('/', '\\', '|', '-', '+', 'x', 'o', 'O', '.', '*',None)
    for k,v in style.items():
        match k:
            case "fill":
                if v is None : pass 
                else: v = to_rgba(v)
            case "hatch":
                if v not in _hatch_str:
                    raise ValueError("%s not a suppoted hatch value : (%s)" %(v,_hatch_str))
            case "stroke":
                v = _check_stroke(v)
            case _ :
                raise ValueError("%s not a supported value" % k)
        style[k] = v
    return style

_tg_style_check = {
    "total" : check_total,
    "path" : check_path,
}

class Drawable(ABC):
    '''Base class for Drawables'''
    drawtype = None
    style_types = None
    def __init__(self,segment,**style) -> None:
        if self.drawtype is None or self.style_types is None : raise ValueError("class attribute: (drawtype,style_types) must be setted")
        # segment 
        self._segment = []
        try:
            for seg in segment:
                if seg[0] not in ("line","cubic"): raise TypeError(f"{seg[0]}不支持的格式")
                self._segment.append((seg[0],*[to_xy(xy) for xy in seg[1:]]))
        except Exception as e: 
            raise ValueError(f"segment不符合格式要求:{e}")
        # style
        self._style = self._check_style(**style)
        self._artist = self._get_artist()
        self._supported_style = set()
        for k in ("total",*(self.style_types)):
            self._supported_style |= set(_tg_style[k].keys())
        


    # 自我描述
    def get_description_dict(self):
        return {
            "type":self.drawtype,
            "segment" : self._segment,
            "style" : self._style
        }
    def __str__(self):
        return "Drawable:%s %s" % (self.drawtype,self.get_description_dict())
    @property
    def supported_style(self):
        return self._supported_style
    # check style
    def _check_style(self,**style):
        _style_types = ("total",*self.style_types)
        style_dct = {}
        for k in style:
            k_type = None
            for _type in _style_types:
                if k in _tg_style[_type]: k_type = _type
            if k_type is None : raise ValueError("%s is not supported style" % k)
            else:
                style_dct.update(_tg_style_check[k_type](**{k:style[k]}))
        return style_dct

        
    def get_artist(self):
        '''返回生成的artist'''
        return self._artist
    # style 
    def set(self,**style):
        style = self._check_style(**style)
        kwargs = self._style_to_mpl_kwargs(**style)
        self._artist.set(**kwargs)
        self._style.update(style)
    def _total_to_mpl_args(self,**style):
        mpl_kwargs = {}
        for k,v in style.items():
            match k:
                case "hidden" : mpl_kwargs.update({"visible" : not v})
                case "zorder" : mpl_kwargs.update({"zorder":v})
                case "alpha" : mpl_kwargs.update({"alpha":v})
                case "clipon" : mpl_kwargs.update({"clip_on":v})
                case _:
                    raise KeyError("%s not a key of total style" % k)
        return mpl_kwargs
    # bounding
    def get_datalim(self):
        '''返回segment中数据的范围:(xmin,ymin),(xmax,ymax)'''
        verts = []
        for seg in self._segment:
            verts.extend(seg[1:])
        #if not verts: verts = [(0,0)]
        xs,ys = zip(*verts)
        return (min(xs),min(ys)),(max(xs),max(ys))
    # segment to Path
    def _segment_to_path(self,segment):
        '''由segment生成path对象'''
        codes,vects = segment_to_CV(segment)
        return Path(vertices=vects,codes=codes)
    # must implement method 
    @abstractmethod
    def _get_artist(self):
        '''the method to build a artist that you need
        - return type : artist
        '''
        pass

    @abstractmethod
    def get_anchor_segment(self):
        '''
        return segment that you want to join anchor segment
        '''
        pass 

    @abstractmethod
    def _style_to_mpl_kwargs(self,**style):
        '''
        transform your kind of style to mpl kind

        return mpl_kwargs that can be used by artist.set() method
        '''
        pass
    
class PathDrawable(Drawable):

    # type , style_types
    drawtype = "path"
    style_types = ("path",)
    # 生成artist
    def _get_artist(self):
        '''通过标准的segment以及支持的style返回artist'''
        path = self._segment_to_path(self._segment)
        kwargs = self._style_to_mpl_kwargs(**self._style)
        return  mpatch.PathPatch(path,**kwargs)    
    # anchor segment
    def get_anchor_segment(self):
        '''返回使用计算的segment'''
        return self._segment
    # _style_to_mpl_kwargs
    def _stroke_to_mpl_args(self,paint,thickness,cap,dash,join):
        return {"edgecolor":paint,"linewidth":thickness,"capstyle":cap,"linestyle":dash,"joinstyle":join}
    def _fill_to_mpl_args(self,fill):
        if fill is None:
            return {"facecolor":None,"fill":False}
        else:
            return {"facecolor":fill,"fill":True}
    def _style_to_mpl_kwargs(self,**style):
        mpl_kwargs = {}
        for k,v in style.items():
            match k:
                case "stroke":
                    mpl_kwargs.update(self._stroke_to_mpl_args(**v))
                case "fill":
                    mpl_kwargs.update(self._fill_to_mpl_args(v))
                case "hatch":
                    mpl_kwargs.update({"hatch":v})
                case "hidden" | "zorder" | "clipon" | "alpha" :
                    mpl_kwargs.update(self._total_to_mpl_args(**{k:v}))
                case _:
                    raise KeyError("%s is not supported by Drawable: %s" %(k,self.drawtype))
        return mpl_kwargs

_tg_drawables = {
    "path":PathDrawable,
}

def register_style(name,default_style,style_check):
    if name in ("total","path") or not isinstance(name,str) : raise ValueError("%s 不是合法的name参数" % name)
    if not isinstance(default_style,dict):
        raise TypeError("default_style 必需为 dict 类型")
    if not isinstance(style_check,FunctionType):
        raise TypeError("style_check 必需为函数")
    _tg_style.update({name:default_style})
    _tg_style_check.update({name:style_check})

def register_drawable(drawable_cls):
    '''注册一个drawable实例'''

    if not issubclass(drawable_cls,Drawable):
        raise ValueError("%s Not a subclass from %s" % (drawable_cls,Drawable))
    try:
        type_ = drawable_cls.drawtype
    except :
        raise ValueError("%s not has the type attribute" % (drawable_cls))
    _tg_drawables.update({type_:drawable_cls})

def get_drawable(drawtype,segment,**style):
    if drawtype not in _tg_drawables : raise ValueError("drawable : %s does not exist" % drawtype)
    return _tg_drawables[drawtype](segment=segment,**style)

###############################################################
##                注册常用Style和Dawable                       ##
###############################################################

# circle style
def check_circle(**style):
    # 在path style的基础上增加了radius
    if "radius" in style:
        r = style.pop("radius")
        try:
            r = to_xy(r)
        except :
            try:
                r = to_xy((float(r),float(r)))
            except :
                raise ValueError("%s not a supported radius value: flaot or (2,1)float array" % r)
    else: r = None
    style = check_path(**style)
    if r is not None: style["radius"] = r
    return style
register_style(name="circle",default_style={"radius":(1,1)} | _tg_style["path"] ,style_check= check_circle )
# mark style and drawable
_tg_symbol = {
    ">":"arrow",
    "|>":"triangle",
    "<>":"diamond",
    "[]":"rect",
    "]":"bracket",
    "|":"bar",
    "o":"circle",
    "+":"plus",
    "x":"x",
    "*":"star"}
def check_mark(**style):
    _mark_style = ("symbol","poses","angle","scale","reverse")
    _symbol_dct = _tg_symbol
    mark_dct = {}
    for mk in _mark_style:
        if mk in style: mark_dct[mk] = style.pop(mk)
    for k,v in mark_dct.items():
        match k:
            case "symbol" : 
                if v is not None:
                    if isinstance(v,str):
                        if v in _symbol_dct: v = _symbol_dct[v] # 消除别名
                        if v not in _symbol_dct.values(): raise ValueError("%s is bad symbol,supported symbol str : %s" %(v,_symbol_dct))
                    else:
                        try:
                            v = check_segment(v)
                        except:
                            raise ValueError("bad symbol,symbol can be a segment or symbol str,yours:%s"%v)
            case "scale":
                try:
                    v = to_xy(v)
                except:
                    try:
                        v = to_xy((v,v))
                    except:
                        raise ValueError("%s is bad %s" % (v,k))
            case "angle":
                v = to_rad(v)
            case "reverse":
                if not isinstance(v,bool): raise TypeError("%s must be a bool value,yours : %s" %(k,v))
            case "poses":
                try:
                    v = [to_xy(xy) for xy in v]
                except:
                    raise ValueError("%s is bad %s , poses must be a (N,2) shape array of float" % (v,k))
        mark_dct[k] = v 
    style = check_path(**style)
    return mark_dct | style 
register_style(name="mark",default_style={"symbol":None,"poses":[(0,0)],"angle":0,"scale":(1,1),"reverse":False} | _tg_style["path"],style_check= check_mark)
class MarkDrawable(PathDrawable):
    '''MarkDrawable 是一类特殊的PathDrawable，其本身不参与锚点计算，但是可以显示图案在指定位置
    
    除了和PathDrawable一样的调用方式之外，还支持通过symbol,poses,angle,scale,reverse值来使用一些预定以的mark。
    '''
    drawtype = "mark"
    style_types = ("mark",)
    
    
    def _get_artist(self):
        '''支持symbol,poses,angle,scale,reverse生成预定以artist,前提为segment == []'''
        if self._segment : return super()._get_artist()
        symbol,poses,angle,scale,reverse = map(self._style.pop,("symbol","poses","angle","scale","reverse"))
        d = self.getMarkbyStyle(symbol=symbol,poses=poses,angle=angle,scale=scale,reverse=reverse,**self._style)
        self._segment = d._segment
        self._style = d._style
        return d._artist

    def get_anchor_segment(self):
        '''不参与anchor计算'''
        return []
    
    @classmethod
    def getUnitMark_CV(cls,symbol):
        '''支持通过symbol str 获得 codes和vects'''
        symbol = check_mark(symbol=symbol)["symbol"]
        match symbol:
            case "arrow" :
                x,y = np.cos(np.pi*5/6),np.sin(np.pi*5/6)
                vects = np.array([(x,y),(0,0),(x,-y)],dtype=float)
                codes = [ 1,2,2]
            case "triangle":
                x,y = np.cos(np.pi*5/6),np.sin(np.pi*5/6)
                vects = np.array([(x,y),(0,0),(x,-y),(x,y)],dtype=float)
                codes = [1,2,2,2]
            case "diamond":
                x,y = np.cos(np.pi*3/4),np.sin(np.pi*3/4)
                vects = np.array([(x,y),(0,0),(x,-y),(2*x,0),(x,y)],dtype=float)+(-x,0)
                codes = [1,2,2,2,2]
            case "rect":
                x,y = -1,1
                vects = np.array([(x,y),(0,y),(0,-y),(x,-y),(x,y)],dtype=float)+(0.5,0)
                codes = [1,2,2,2,2]
            case "bracket":
                x,y = -1,1
                vects = np.array([(x,y),(0,y),(0,-y),(x,-y)],dtype=float)
                codes = [1,2,2,2]
            case "bar":
                x,y = 0,1
                vects = np.array([(x,y),(x,-y)],dtype=float)
                codes = [1,2]
            case "circle":
                codes,vects = getUnitCircle_CV()
            case "plus":
                x,y = 1,1
                vects = np.array([(0,y),(0,-y),(-x,0),(x,0)],dtype=float)
                codes = [1,2,1,2]
            case "x":
                x = y = np.sqrt(2)/2
                vects = np.array([(x,y),(-x,-y),(-x,y),(x,-y)],dtype=float)
                codes = [1,2,1,2]
            case "star":
                x = y = np.sqrt(2)/2
                vects = np.array([(0,1),(0,-1),(x,y),(-x,-y),(-x,y),(x,-y)],dtype=float)
                codes = [1,2,1,2,1,2]
            case _:
                raise ValueError("%s is a bad symbol str,supported symbol str are : %s" %(symbol,_tg_symbol))
        vects = vects * 0.1
        assert len(codes) == len(vects)
        return codes,vects
    @classmethod
    def getMarkbyStyle(cls,symbol,poses,angle=0,scale=(1,1),reverse=False,**style):
        '''通过symbol,poses,angle,scale,reverse的值生成MarkDrawable'''
        mark_dct = check_mark(symbol=symbol,poses=poses,angle=angle,scale=scale,reverse=reverse)
        symbol,poses,angle,scale,reverse = map(mark_dct.get,("symbol","poses","angle","scale","reverse"))
        if symbol is None: raise ValueError("symbol is None, can't build a MarkDrawable")
        codes,vects = cls.getUnitMark_CV(symbol) if isinstance(symbol,str) else segment_to_CV(symbol)
        vects = vects * scale 
        mat = get_transform_by_rad(np.eye(3),angle)
        if reverse:
            mat = get_transform_by_reverse(mat,1,0,0)
        _get_xy = lambda xy : get_xy_by_transform(mat,xy)
        vects = np.array(list(map(_get_xy,vects)))
        _vects = []
        _codes = []
        for p in poses:
            _vects.extend(vects+p)
            _codes.extend(codes)
        segment = codes_vects_to_segment(_codes,_vects)
        return cls(segment,**style)        
register_drawable(MarkDrawable)
# line style
def check_line(**style):
    # 在path的基础上增加了mark
    _defautlt_mark_dct = _tg_style["mark"] | {"start":True,"end":False}
    def _check_line_mark(**mstyle):
        # 基于mark，添加start,end (bool),且每次返回都是一个完整的mark字典，因为mark这里作为了一整个值，必需具有这些
        mstyle = _defautlt_mark_dct | mstyle 
        start,end = mstyle.pop("start"),mstyle.pop("end")
        if not isinstance(start,bool): raise ValueError("%s must be a bool value , yours : %s" %("start",start) )
        if not isinstance(end,bool): raise ValueError("%s must be a bool value , yours : %s" %("start",end) )
        mstyle = check_mark(**mstyle)
        mstyle["start"],mstyle["end"] = start,end 
        return mstyle 
    mark_dct = style.pop("mark",None)
    path_style = check_path(**style)
    if mark_dct is not None: 
        mark_dct = _check_line_mark(**mark_dct)
        return path_style | {"mark":mark_dct}
    else:
        return path_style
register_style("line",default_style=_tg_style["path"] | {"mark":_tg_style["mark"] | {"start":True,"end":False}},style_check=check_line)
# arc style
_tg_arc_mode = ("open","close","pie")
def check_arc(**style):
    '''arc style: (mode,radius,mark,stroke,fill,hatch,)——在line的基础上添加了radius和mode'''
    mode = style.pop("mode",None)
    radius = style.pop("radius",None)
    style = check_line(**style)
    if mode is not None:
        if mode not in _tg_arc_mode: raise ValueError(f"{mode} is a bad value for arc mode : {_tg_arc_mode}")
        style["mode"] = mode 
    if radius is not None:
        try:
            radius = float(radius)
        except:
            raise ValueError(f"{radius} is a bad value for radius")
        style["radius"]  = radius 
    return style

register_style("arc",default_style=_tg_style["line"] | {"radius":1,"mode":"open"},style_check=check_arc)
# rect style
register_style("rect",default_style=_tg_style["circle"],style_check=check_circle) # as same as circle
# bezier style
register_style("bezier",default_style=_tg_style["line"],style_check=check_line) # as same as line



################################################################
##             end of register                                ##
################################################################

        
##########################################################################
###               end of Drawable interface                            ###
##########################################################################


class Node():
    '''
    生成artist，提供锚点计算和路径计算功能
    '''

    def __init__(self,drawables,name = None) -> None:                                                                           # drawable用字典可以表示，但是它的值与artist的状态是联动的，但是实际上在生成类之后其实就没有作用了
        if name is not None:                                                                                                    # drawable --|转换层|--> mpl参数
            if not isinstance(name,str) or not re.fullmatch(RE_node_name,name) : raise ValueError(f"{name}不是支持的Node名")      # 用户 -->drawable--> artist 
        self.name = name    
        self.drawables = []
        for d in drawables:
            if not isinstance(d,Drawable):
                self.drawables.append(get_drawable(**d))
            else:
                self.drawables.append(d)
        self._supported_style = set()
        for d in self.drawables:
            self._supported_style |= d.supported_style
        data_segment = []
        for d in self.drawables:
            data_segment.extend(d.get_anchor_segment())
        # 锚点预准备
        ## 如果是组(不连续)，则计算路径为边框，其他为路径本身
        ## 如果是连续不闭合路径，则允许路径计算
        ## 如果连续且闭合，则允许面积相关计算
        ## 组和闭合路径允许面积相关计算
        ## 不闭合路径只允许路径计算
        ## _iscontinued,_isgroup,_isclosed,_can_get_intersection,_coefs
        self._iscontinued,self._isclosed = self._is_segment_continued_and_closed(data_segment)
        if not self._iscontinued:
            if data_segment:
                self._isgroup = True
                self._can_get_intersection = True
                self._coefs = segment_to_coefs(self._get_bounding_segment()) # 路径为边框
            else:
                self._isgroup = False
                self._can_get_intersection = False
                self._coefs = []
        else:
            self._isgroup = False
            self._coefs = segment_to_coefs(data_segment)
            self._can_get_intersection = True if (self._isclosed and not np.isclose(coefs_to_area(self._coefs),0)) else False 
        ## 设置锚点字典
        self._anchor_dct = {}
        ## 如果可以获取交点，则具有 _center
        if self._can_get_intersection:
            self._center = coefs_to_center(self._coefs)
        ## 路径计算用的总长度，结点权重
        self._length,self._nodeweight,self._length_error = coefs_to_length_and_nodeweight(self._coefs)
        
    # 自我描述
    def get_description_dict(self):
        '''
        返回具有描述性的字典
        '''
        return {
            "name":self.name,
            "drawables":[d.get_description_dict() for d in self.drawables]
        }
    def __str__(self):
        return f"{self.__class__}({self.get_description_dict()})"
    @property
    def supported_style(self):
        return self._supported_style
    # artists
    @property
    def artists(self):
        return [d.get_artist() for d in self.drawables]
    def get_artists(self):
        return self.artists
    def iter_artists(self):
        for d in self.drawables:
            yield d.get_artist()
    def set(self,**style):
        '''
        为Aritists设置style值。
        '''
        for k,v in style:
            if k not in self.supported_style: raise ValueError("%s is a bad value for set style,support key : %s" %(k,self.supported_style))
            for d in self.drawables:
                if k in d.supported_style:
                    d.set(**{k:v})
    # 边框管理
    def _get_bounding_box(self):
        '''返回Node的边框((xmin,xmax),(ymin,ymax))，用于自动调整画布以及部分锚点计算'''
        verts = []
        for d in self.drawables:
            verts.extend(d.get_datalim())
        xs,ys = zip(*verts)
        return (min(xs),min(ys)),(max(xs),max(ys))
    def _get_bounding_segment(self):
        (xmin,xmax),(ymin,ymax) = self._get_bounding_box()
        return [("line",(xmin,ymin),(xmax,ymin),(xmax,ymax),(xmin,ymax),(xmin,ymin))]
    def get_datalim(self):
        return self._get_bounding_box()
    # 锚点
    def _update_anchor_dct(self,anchor,xy):
        if not re.fullmatch(RE_anchor_name,anchor): raise ValueError("锚点的命名不符合规范")
        xy = to_xy(xy)
        self._anchor_dct[anchor] = xy
    def add_anchor(self,anchor,xy):
        return self._update_anchor_dct(anchor,xy)
    def _is_segment_continued_and_closed(self,segment):
        if segment == []: return False,False
        start_points ,end_points = [],[]
        _continue = True
        _joint = True
        for code in segment:
            start_points.append(code[1])
            end_points.append(code[-1])
        if tuple(end_points[-1]) != tuple(start_points[0]) : _joint = False
        for i in range(1,len(start_points)):
            if tuple(start_points[i]) != tuple(end_points[i-1]) : _continue = False
        return _continue , (_joint and _continue)
    ## 返回锚点值
    def calculate_anchors(self,anchor=None):
        '''根据anchor的值返回坐标'''
        default_anchors = {'center':None,'north':'90deg','south':'-90deg','west':'180deg','east':'0deg','start':0,'mid':'50%','end':'100%'}
        if anchor in default_anchors: anchor = default_anchors[anchor]
        if anchor is None: 
            if self._can_get_intersection: return self._center
            else: return self.get_point('50%')
        anchor = str(anchor)
        if re.fullmatch(RE_float,anchor):
            return self.get_point(float(anchor)) #长度
        if re.fullmatch(RE_float+"%",anchor):
            return self.get_point(anchor) # 百分数
        if self._can_get_intersection:
            if re.fullmatch(RE_float+'rad',anchor):
                rad = float(anchor[:-3])
                rs = self.get_point_by_rad(rad)
                if len(rs) != 1: raise ValueError(f"由{anchor}锚点所确定的值不唯一，结果为{rs}")
                return rs[0]
            if re.fullmatch(RE_float+'deg',anchor):
                rad = np.radians(float(anchor[:-3]))
                rs = self.get_point_by_rad(rad)
                if len(rs) != 1: raise ValueError(f"由{anchor}锚点所确定的值不唯一，结果为{rs}")
                return rs[0]
        if anchor in self._anchor_dct:
            return self._anchor_dct[anchor]
        return TypeError(f"{anchor}不存在，或者未注册")
    # 路径计算
    def get_point(self,t):
        '''根据长度或者百分数计算路径上的点'''
        def _point_by_percent(t):
            assert 0<= t <= 1
            nodeweight = self._nodeweight.copy()
            nodeweight.insert(0,0)
            for i in range(1,len(nodeweight)):
                if t <= nodeweight[i] : break
            t = (t - nodeweight[i-1])/(nodeweight[i] - nodeweight[i-1])
            return get_bezier_point(self._coefs[i-1],t)
        if re.fullmatch(RE_float+"%",str(t)):
            t = float(t[:-1])/100
            return _point_by_percent(t)
        if re.fullmatch(RE_float,str(t)):
            t = float(t)
            if t < 0 : raise ValueError("长度必须大于0")
            if t > self._length : raise ValueError("长度超过曲线的长度")
            t = t/self._length
            return _point_by_percent(t)
        raise TypeError(f"{t}不是支持的参数，支持长度和百分数")
    def get_point_by_rad(self,rad):
        if not self._can_get_intersection: raise NotImplemented("由于node的曲线并不连续且封闭，因而不提供根据角度取值")
        _deg1 = (rad/np.pi)*180 % 360 
        _deg2 = (_deg1 - 90) % 180
        flag = 'x' if 45 <= _deg2 <= 125 else 'y'
        match flag:
            case 'x': 
                _sign = True if  np.cos(rad) > 0 else False
            case 'y':
                _sign = True if np.sin(rad) > 0 else False
        points = []
        line_vect = np.cos(rad) , np.sin(rad)
        line_point = self._center
        for coef in self._coefs:
            result_p = bezier_line_intersection(coef,line_point=line_point,line_vect=line_vect)
            for p in result_p:
                if len(points) == 0 or ( not np.array([ p.all() for p in np.isclose(points,p) ]).any()):
                    # 符号判断
                    match flag:
                        case "x": 
                            if not (((p[0] - line_point[0]) > 0 ) ^ _sign):
                                points.append(p)
                        case "y":
                            if not (((p[1] - line_point[1]) > 0 ) ^ _sign):
                                points.append(p)
                    
        return np.array(points,dtype=float)

assert "total" in _tg_style