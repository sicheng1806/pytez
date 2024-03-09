'''
'''
import numpy as np
import re
from matplotlib.colors import to_rgba


RE_float = r"-?(\d+(\.\d+)?|\.\d+)"
RE_node_name= RE_anchor_name = r"[a-z|_|\d]+"
DefaultStyleValue = {"hidden":False,"fill":None,"hatch":None,"stroke":None,"alpha":1,"zorder":None,"clipon":True}
RE_find_anchor = r"[a-z|_][a-z|_|\d]*(\.[a-z|_|\d]+)?" # 命名与python变量命名一致

def standardize_color(color):
    return to_rgba(color)

def standardize_stroke(stroke):
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
        return standardize_stroke(stroke_dct)
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

def standardize_style_arg(style_name,value):
    _style_str = DefaultStyleValue # patheffects 暂不支持
    _hatch_str = ('/', '\\', '|', '-', '+', 'x', 'o', 'O', '.', '*',None)
    if style_name not in _style_str: raise ValueError(f"{style_name}不是合法的style值,合法值有{_style_str.keys()}")
    if value == None: return  _style_str[style_name]
    match style_name:
        case "fill" : 
            value =  standardize_color(value)
        case "hatch" : 
            if value not in _hatch_str: raise ValueError(f"{value}不是支持的hatch值，支持的值有{_hatch_str.keys()}")
        case "stroke": value =  standardize_stroke(value)
        case "alpha" : 
            try:
                value = float(value)
                if not (0<=value<=1): raise
            except : 
                raise TypeError(f"{value}不是支持的alpha值,合法值为0-1的实数")
        case "zorder" : 
            try:
                value = int(value)
            except :
                raise ValueError(f"{value}不是支持的zorder值,zorder为None或者int")
        case "hidden" :
            try:
               value = bool(value)
            except:
                raise TypeError(f"{value}不是合法的hidden值,合法值为bool")
    return value

def standardize_style_dct(style_dct):
    _must_checked = DefaultStyleValue.keys()
    if not isinstance(style_dct,dict): raise TypeError(f"{style_dct}不是支持的style类型，style必需为dict类型")
    for k in style_dct:
        if k in _must_checked: style_dct[k] = standardize_style_arg(k,style_dct[k])
        if isinstance(style_dct[k],dict):
            for k_2 in style_dct[k] : 
                if k_2 in _must_checked: style_dct[k][k_2] = standardize_style_arg(k,style_dct[k][k_2])
    for k in _must_checked:
        if k not in style_dct:
            style_dct[k] = standardize_style_arg(k,None) # 如果必须的值未在字典类，使用默认值填充
    return style_dct

def standardize_transform(t):
    try:
        t = np.array(t,dtype=float)
        if t.shape != (3,3) or np.linalg.det(t) == 0: raise
    except:
        raise ValueError(f"{t}不是支持的transform值，支持(3,3)的数组类型且可逆的变换矩阵")
    return t

def standardize_xy(xy):
    try:
        xy = np.array(xy,dtype=float)
        if xy.shape != (2,): raise 
    except :
        raise TypeError(f"{xy}不是合法的xy参数值，合法值为二元实数组")
    return xy 

def standardiz_angle(angle):
    if isinstance(angle,str):
        _angle = angle
        if re.fullmatch(RE_float+r"deg",angle):
            angle =  np.radians(float(angle[:-3]))
        elif re.fullmatch(RE_float+r"rad",angle):
            angle = float(angle[:-3])
    try:
        angle = float(angle)
    except : 
        raise ValueError(f"{_angle}不是合法的angle值")
    return angle

def standardize_drawable(drawable):
    if not isinstance(drawable,dict): raise ValueError(f"{drawable}不是支持的drawable类型，支持dict类型")
    if "type" not in drawable : raise ValueError(f"{drawable}缺少必需的键：type")
    match drawable["type"]:
        case "path":
            drawable.pop("type")
            kwargs = drawable
            drawable = get_drawable(drawtype="path",**kwargs)
            drawable["type"] = "path"
        case _ :
            raise ValueError(f"{drawable["type"]}不是支持的type键，目前支持(path,)")
    return drawable

def standardize_bezier_coef(coef):
    try:
        coef = np.array(coef,dtype=float)
        if len(coef.shape) != 2 or coef.shape[0] != 2 or coef.shape[1] > 4 : raise 
    except:
        raise ValueError(f"{coef}不是合法的三次贝塞尔曲线的系数值")
    if coef.shape == (2,2): coef = np.stack([coef.T[0],coef.T[1],[0,0],[0,0]],axis=1)
    if coef.shape == (2,3): coef = np.stack([coef.T[0],coef.T[1],coef.T[2],[0,0]],axis=1)
    return coef

def get_drawable(drawtype="path",**kwargs):
    '''标准化drawables为字典形式'''
    _suppot_keys = {"path":("segments",*DefaultStyleValue.keys())}
    drawable = {}
    match drawtype:
        case "path": #!segments,stroke,fill,hidden,zorder,alpha,
            if set(kwargs) > set(_suppot_keys["path"]) : raise ValueError(f"{drawtype}类型drawable存在不支持的值")
            if "segments" not in kwargs : raise ValueError(f"{drawtype}类型drawable缺少必需的键：segments键")
            segments = kwargs.pop("segments")
            style = standardize_style_dct(kwargs)
            drawable["type"] = "path"
            drawable["segments"] = segments
            drawable |= style 
        case _ : 
            raise ValueError(f"{drawtype}不是支持的drawable类型")
    return drawable
#!
def get_node_dct(drawables:list[dict],name=None):
    if name is not None: 
        if not isinstance(name,str) or not re.fullmatch(RE_node_name,name) : raise ValueError(f"{name}不是支持的Node名")
    node_dct = {"name":name,"drawables":[]}
    for drawable in drawables:
        node_dct["drawables"].append(standardize_drawable(drawable))
    return node_dct



if __name__ == '__main__':
    print(get_drawable(segments = ["line",(0,0),(1,1)],stroke="p:r,t:2"))
