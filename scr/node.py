import matplotlib.patches as mpatch
from matplotlib.path import Path
import re 
import numpy as np 
from matplotlib.colors import to_rgba
from abc import abstractmethod,ABC
from types import FunctionType

from utilities import segment_to_CV,to_xy,to_rad,codes_vects_to_segment
from bezier import segment_to_coefs,coefs_to_center,coefs_to_length_and_nodeweight,get_bezier_point,bezier_line_intersection
from matrix import get_transform_by_rad,get_transform_by_reverse,get_xy_by_transform

##############################################################################
###             Drawable: 与artist的接口类                                  ###
###          可以通过自定义Drawable类扩展绘图的类型                            ###
#############################################################################

## 设置对样式的支持和检查函数,支持扩展
## style检查函数会同时在drawable 以及 canvas使用

RE_float = r"-?(\d+(\.\d+)?|\.\d+)"
RE_node_name= RE_anchor_name = r"[a-z|_|\d]+"

_tg_style = {
    "total" : {
        "hidden" : False,
        "alpha" : 1,
        "zorder" : None,
        "clipon" : True
    },
    "line" : {
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

def check_line(**style):
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
    "line" : check_line,
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
    style_types = ("line",)
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
    if name in ("total","line") or not isinstance(name,str) : raise ValueError("%s 不是合法的name参数" % name)
    if not isinstance(default_style,dict):
        raise TypeError("default_style 必需为 dict 类型")
    if not isinstance(style_check,FunctionType):
        raise TypeError("style_check 必需为函数")
    _tg_style.update({name:default_style})
    _tg_style_check.update({name:style_check})

def register_drawable(drawable_cls):
    '''注册一个drawable实例'''

    if not isinstance(drawable_cls,Drawable):
        raise ValueError("%s Not a subclass from %s" % (drawable_cls,PathDrawable))
    try:
        type_ = drawable_cls.drawtype
    except :
        raise ValueError("%s not has the type attribute" % (drawable_cls))
    _tg_drawables.update({type_:drawable_cls})

def get_drawable(drawtype,segment,**style):
    if drawtype not in _tg_drawables : raise ValueError("drawable : %s does not exist" % drawtype)
    return _tg_drawables[drawtype](segment=segment,**style)

##############################################################################################
################   add style and drawable by register  ####################################### 

# add circle style 
def check_circle(**style):
    if "radius" in style:
        r = style.pop("radius")
        try:
            r = to_xy(r)
        except :
            try:
                r = to_xy((float(r),float(r)))
            except :
                raise ValueError("%s not a supported radius value: flaot or (2,1)float array" % r)
    style = check_line(**style)
    style["radius"] = r
    return style
register_style(name="circle",default_style={"radius":(1,1)} | _tg_style["line"] ,style_check= check_circle )

# add mark Drawable and style
_tg_symbol = {">":"arrow"}
def check_mark(**style):
    _mark_style = ("symbol","pos","angle","scale","reverse")
    _symbol_dct = _tg_symbol
    mark_dct = {}
    for mk in _mark_style:
        if mk in style: mark_dct[mk] = style.pop(mk)
    for k,v in mark_dct.items():
        match k:
            case "symbol" : 
                if v in _symbol_dct: v = _symbol_dct[v] # 消除别名
                if v not in _symbol_dct.values(): raise ValueError("%s is bad symbol,supported symbol : %s" %(v,_symbol_dct))
            case "scale":
                try:
                    v = to_xy(v)
                except:
                    raise ValueError("%s is bad %s" % (v,k))
            case "angle":
                v = to_rad(v)
            case "reverse":
                if not isinstance(v,bool): raise TypeError("%s must be a bool value,yours : %s" %(k,v))
            case "pos":
                try:
                    v = [to_xy(xy) for xy in v]
                except:
                    raise ValueError("%s is bad %s , pos must be a (N,2) shape array of float" % (v,k))

        mark_dct[k] = v 
    style = check_line(**style)
    return mark_dct | style 
register_style(name="mark",default_style={"symbol":None,"pos":[(0,0)],"angle":0,"scale":(1,1),"reverse":False} | _tg_style["line"],style_check= check_mark)

class MarkDrawable(PathDrawable):
    '''MarkDrawable 是一类特殊的PathDrawable，其本身不参与锚点计算，但是可以显示图案在指定位置
    
    除了和PathDrawable一样的调用方式之外，还支持通过symbol,pos,angle,scale,reverse值来使用一些预定以的mark。
    '''
    drawtype = "mark"
    style_types = ("mark",)
    
    
    def _get_artist(self):
        '''支持symbol,pos,angle,scale,reverse生成预定以artist,前提为segment == []'''
        if self._segment : return super()._get_artist()
        symbol,pos,angle,scale,reverse = map(self._style.get,("symbol","pos","angle","scale","reverse"))
        return self.getMarkbyStyle(symbol=symbol,pos=pos,angle=angle,scale=scale,reverse=reverse)

    def get_anchor_segment(self):
        '''不参与anchor计算'''
        return []
    
    @classmethod
    def getUnitMark_CV(cls,symbol):
        symbol = check_mark(symbol=symbol)["symbol"]
        match symbol:
            case "arrow" :
                vects = np.array([ (np.cos(np.pi*5/6),np.sin(np.pi*5/6)),(0,0),(np.cos(-np.pi*5/6),np.sin(-np.pi*5/6)) ]) * 0.1
                codes = [ 1,2,2]
                return codes,vects
            case _:
                raise ValueError("%s is a bad symbol,supported symbols are : %s" %(symbol,_tg_symbol))
        
    @classmethod
    def getMarkbyStyle(cls,symbol,pos,angle=0,scale=(1,1),reverse=False,**style):
        mark_dct = check_mark(symbol=symbol,pos=pos,angle=angle,scale=scale,reverse=reverse)
        symbol,pos,angle,scale,reverse = map(mark_dct.get,("symbol","pos","angle","scale","reverse"))
        codes,vects = cls.getUnitMark_CV(symbol=symbol)
        vects = vects * scale 
        mat = get_transform_by_rad(np.eye(3),angle)
        if reverse:
            mat = get_transform_by_reverse(mat,1,0,0)
        _get_xy = lambda xy : get_xy_by_transform(mat,xy)
        vects = np.array(list(map(_get_xy,vects)))
        _vects = []
        _codes = []
        for p in pos:
            _vects.extend(vects+p)
            _codes.extend(codes)
        segment = codes_vects_to_segment(_codes,_vects)
        return cls(segment,**style)
        




#############            end of register                 ######################################
###############################################################################################

        
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
            self._isgroup = True
            self._can_get_intersection = True
            self._coefs = segment_to_coefs(self._get_bounding_segment()) # 路径为边框
        else:
            self._isgroup = False
            self._coefs = segment_to_coefs(data_segment)
            self._can_get_intersection = True if self._isclosed else False 
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
        self._update_anchor_dct[anchor] = xy
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
