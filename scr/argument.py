'''
'''
from matplotlib.colors import to_rgba

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

def standardize_style(style_name,value):
    _style_str = ("fill","hatch","stroke","color","alpha","zorder","hidden","clipon") # patheffects 暂不支持
    match style_name:
        case "fill" : 
            if value is None : return value 
            else : return standardize_color(value)
        case "hatch" : 
            pass
        case "stroke": return standardize_stroke(value)
        case "color" : return standardize_color(value)
        case "alpha" : 
            try:
                value = float(value)
                if not (0<=value<=1): raise
            except : 
                raise TypeError(f"{value}不是支持的alpha值,合法值为0-1的实数")
            return value
        case "zorder" : 
            if value is None : return value 
            else: 
                try:
                    value = int(value)
                except :
                    raise ValueError(f"{value}不是支持的zorder值,zorder为None或者int")
            return value
        case "hidden" :
            try:
               value = bool(value)
            except:
                raise TypeError(f"{value}不是合法的hidden值,合法值为bool")
        case _ : raise ValueError(f"{style_name}不是合法的style值,合法值有{_style_str}")

if __name__ == '__main__':
    print(to_rgba("r")) # rgba接收三元数组嘛
